# backend/app/api/routes.py
from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
import uuid
import re

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from app.storage import reports_store as store
from app.ingest.parser import parse_pdf_bytes, normalize_test_name
from app.normalize.unit_normalization import normalize_units_for_test
from app.kb.loader import load_kb, get_entry_with_rag
from app.summarize.llm import summarize_results_structured

router = APIRouter(prefix="/api")

# Load the static KB once (dict keyed by canonical lower-cased test names)
KB: Dict[str, Any] = load_kb()

# Toggle debug echo (remove/False for production)
DEBUG_PARSE_ECHO = True


# ─────────────────────────── helpers ───────────────────────────

def _build_disclaimer() -> str:
    return (
        "⚠️ NutriScope is an AI-powered tool designed to help you understand your lab reports. "
        "We use standard reference ranges for children, adults, and elderly patients, which may differ slightly from your testing "
        "laboratory’s ranges. Information and diet suggestions are educational only and should not replace consultation with a "
        "qualified healthcare professional."
    )


def _title_from_kb_key(k: str) -> str:
    """Pretty-case a KB key for display."""
    if not k:
        return k
    parts = []
    for token in k.split():
        if "(" in token or ")" in token:
            parts.append(token)
        else:
            parts.append(token.capitalize())
    pretty = " ".join(parts)
    # small cleanups
    pretty = (
        pretty.replace("Oh)", "OH)")
              .replace("Ldl", "LDL")
              .replace("Hdl", "HDL")
              .replace("Tg", "TG")
    )
    return pretty


def convert_to_kb_unit(test_key_lower: str, value, unit: str, kb_unit: Optional[str]) -> Tuple[Optional[float], str]:
    """
    Convert (value, unit) to the KB's expected unit (kb_unit).
    Handles common CBC count shorthands (K/µL, M/µL, x10^3/µL, etc.).
    """
    if value is None:
        return None, unit

    t = (test_key_lower or "").strip().lower()
    u = (unit or "").strip().lower().replace("µ", "u").replace("μ", "u").replace("mc", "u")
    kbu = (kb_unit or "/uL").strip().lower().replace("µ", "u").replace("μ", "u").replace("mc", "u")

    def to_per_ul(v, u_):
        if u_ in {"k/ul", "x10^3/ul", "10^3/ul", "x10³/ul", "x10^3ul"}:
            return float(v) * 1_000.0, "/uL"
        if u_ in {"m/ul", "x10^6/ul", "10^6/ul", "x10⁶/ul", "x10^6ul"}:
            return float(v) * 1_000_000.0, "/uL"
        if u_ in {"/ul", "per ul"}:
            return float(v), "/uL"
        return float(v), unit  # unknown; leave as-is

    CBC_KEYS = {
        "platelet count", "platelets", "plt",
        "white blood cell (wbc)", "wbc", "white blood cell",
        "red blood cell (rbc)", "rbc", "red blood cell",
        "absolute neutrophils", "neutrophil, absolute",
        "absolute lymphocytes", "lymphocyte, absolute",
        "absolute monocytes", "monocyte, absolute",
        "absolute eosinophils", "eosinophil, absolute",
        "absolute basophils", "basophil, absolute",
    }

    if t in CBC_KEYS:
        v_ul, u_ul = to_per_ul(value, u)
        if kbu in {"/ul", "per ul"}:
            return v_ul, "/uL"
        if kbu in {"k/ul"}:
            return float(v_ul) / 1_000.0, "K/uL"
        if kbu in {"m/ul"}:
            return float(v_ul) / 1_000_000.0, "M/uL"
        return v_ul, u_ul

    # Non-count labs: no conversion here (extend for mg/dL <-> mmol/L, etc. as needed)
    return float(value), unit


def _infer_units_for_counts(kb_key_in: str, value: Optional[float], unit: str) -> Tuple[Optional[float], str]:
    """
    If unit is missing/blank for common CBC counts, infer and convert to /uL.
    - WBC is often reported in K/µL (e.g., 6.9) -> 6900 /uL
    - RBC in M/µL (e.g., 4.5) -> 4_500_000 /uL
    - Absolute differentials often in K/µL (e.g., 3.5) -> 3500 /uL
    - Platelets in K/µL (e.g., 180) -> 180_000 /uL
    """
    if value is None:
        return value, unit

    name = (kb_key_in or "").lower().strip()
    if unit:  # nothing to infer
        return value, unit

    # WBC
    if "white blood cell" in name or name == "wbc":
        if 0.1 <= value <= 30:
            return float(value) * 1_000.0, "/uL"

    # RBC
    if "red blood cell" in name or name == "rbc":
        if 0.1 <= value <= 10:
            return float(value) * 1_000_000.0, "/uL"

    # Absolute diffs
    ABS_KEYS = (
        "absolute neutrophils", "absolute lymphocytes", "absolute monocytes",
        "absolute eosinophils", "absolute basophils"
    )
    if any(k in name for k in ABS_KEYS):
        if 0.05 <= value <= 30:
            return float(value) * 1_000.0, "/uL"

    # Platelets
    if "platelet" in name or name == "plt":
        if 10 <= value <= 1000:
            return float(value) * 1_000.0, "/uL"

    return value, unit


# --- Robust KB key resolver -------------------------------------------------

def _resolve_kb_key(name: str) -> Optional[str]:
    """
    Try to map a parsed/normalized test name to an existing KB key by:
      - exact match
      - strip % suffix
      - remove '(...)'
      - try abbreviation inside '(...)' and expansions
      - search canonical variant sets
      - whitespace normalization
    """
    if not name:
        return None
    n = (name or "").strip().lower()

    # exact
    if n in KB:
        return n

    # strip trailing " %"
    if n.endswith(" %"):
        s = n[:-2].strip()
        if s in KB:
            return s

    # remove parentheticals and try again
    no_parens = re.sub(r"\s*\([^)]*\)\s*", "", n).strip()
    if no_parens in KB:
        return no_parens

    # parse abbreviation from parentheses and try abbrev + expansions
    m = re.search(r"\(([^)]+)\)", n)
    if m:
        abbr_full = m.group(1).strip()
        for a in re.split(r"[\/\s,]+", abbr_full):
            a = a.strip().lower()
            if not a:
                continue
            if a in KB:
                return a
            if f"{a} %" in KB:
                return f"{a} %"
            EXPAND = {
                "hb": "hemoglobin",
                "hgb": "hemoglobin",
                "hct": "hematocrit",
                "wbc": "white blood cell",
                "rbc": "red blood cell",
                "mcv": "mean corpuscular volume (mcv)",
                "mch": "mean corpuscular hemoglobin (mch)",
                "mchc": "mean corpuscular hemoglobin concentration (mchc)",
                "rdw": "red cell distribution width (rdw)",
                "mpv": "mean platelet volume (mpv)",
                "plt": "platelet count",
                "vit d": "vitamin d (25-oh)",
                "vitamin d3": "vitamin d (25-oh)",
            }
            lf = EXPAND.get(a)
            if lf and lf in KB:
                return lf

    # canonical variant sets
    CANON = {
        "white blood cell (wbc)": ["wbc", "white blood cell"],
        "red blood cell (rbc)": ["rbc", "red blood cell"],
        "hemoglobin (hb/hgb)": ["hemoglobin", "hb", "hgb"],
        "hematocrit (hct)": ["hematocrit", "hct"],
        "mean cell volume (mcv)": ["mcv", "mean corpuscular volume (mcv)"],
        "mean cell hemoglobin (mch)": ["mch", "mean corpuscular hemoglobin (mch)"],
        "mean cell hb conc (mchc)": ["mchc", "mean corpuscular hemoglobin concentration (mchc)"],
        "red cell dist width (rdw)": ["rdw", "red cell distribution width (rdw)"],
        "mean platelet volume": ["mpv", "mean platelet volume (mpv)"],
        "neutrophil (neut)": ["neutrophils %", "neutrophils"],
        "lymphocyte (lymph)": ["lymphocytes %", "lymphocytes"],
        "monocyte (mono)": ["monocytes %", "monocytes"],
        "eosinophil (eos)": ["eosinophils %", "eosinophils"],
        "basophil (baso)": ["basophils %", "basophils"],
        "platelet count": ["platelet count", "platelets", "plt"],
        "vitamin d (25-oh)": ["vit d", "vitamin d", "vitamin d3"],
    }
    for _k, variants in CANON.items():
        if n == _k or n in variants:
            for v in [n, _k, *variants]:
                if v in KB:
                    return v

    simp = " ".join(n.split())
    if simp in KB:
        return simp

    return None


def _apply_range_and_status(
    kb_key_in: str,
    value: Optional[float],
    unit: str,
    age: int,
    sex: str,
) -> Dict[str, Any]:
    """
    Lookup reference from KB (with resolver) and compute status.
    Falls back to RAG if static KB misses the entry.
    """
    kb_key = _resolve_kb_key(kb_key_in)
    kb_entry = KB.get(kb_key) if kb_key else None

    # RAG fallback when static KB misses it
    if not kb_entry:
        rag_entry = get_entry_with_rag(kb_key_in) if kb_key_in else None
        if rag_entry and isinstance(rag_entry, dict) and rag_entry.get("ranges"):
            kb_entry = rag_entry
            kb_key = kb_key or kb_key_in  # keep something for unit resolution

    if not kb_entry:
        return {
            "applied_range": {"low": None, "high": None, "source": "NONE", "note": "not_in_kb"},
            "status": "needs_review",
        }

    kb_unit = (kb_entry.get("unit") or "").strip() or None
    conv_value, _conv_unit = convert_to_kb_unit(kb_key, value, unit, kb_unit)

    applied = {"low": None, "high": None, "source": "KB", "note": None}
    ranges = kb_entry.get("ranges") or []

    # (1) fixed low/high
    chosen = None
    for r in ranges:
        applies = (r.get("applies") or {})
        s_ok = applies.get("sex") in (None, "any", sex)
        a_min = applies.get("age_min")
        a_max = applies.get("age_max")
        a_ok = (a_min is None or age >= a_min) and (a_max is None or age <= a_max)
        if s_ok and a_ok and ("low" in r or "high" in r):
            chosen = r
            break

    if chosen is not None:
        low = chosen.get("low")
        high = chosen.get("high")
        applied["low"], applied["high"] = low, high
        if kb_key in {"plt", "platelets", "platelet count", "wbc", "rbc"}:
            applied["unit"] = kb_unit or "/uL"
        elif kb_unit:
            applied["unit"] = kb_unit

        if conv_value is None:
            return {"applied_range": applied, "status": "needs_review"}
        if low is not None and conv_value < low:
            return {"applied_range": applied, "status": "low"}
        if high is not None and conv_value > high:
            return {"applied_range": applied, "status": "high"}
        return {"applied_range": applied, "status": "normal"}

    # (2) banded categories (LDL, TG, eGFR, Vitamin D, etc.)
    band_holder = None
    for r in ranges:
        applies = (r.get("applies") or {})
        if applies.get("sex") in (None, "any", sex) and r.get("bands"):
            band_holder = r
            break

    if conv_value is not None and band_holder and band_holder.get("bands"):
        for b in band_holder["bands"]:
            b_min = b.get("min", float("-inf"))
            b_max = b.get("max", float("inf"))
            if b_min is None:
                b_min = float("-inf")
            if b_max is None:
                b_max = float("inf")
            if b_min <= conv_value <= b_max:
                label = (b.get("label") or "").lower()
                status = "normal" if label in ("normal", "optimal", "sufficient") else label or "needs_review"
                applied["low"], applied["high"] = b.get("min"), b.get("max")
                applied["note"] = "banded"
                if kb_unit:
                    applied["unit"] = kb_unit
                return {"applied_range": applied, "status": status}
        return {"applied_range": {"low": None, "high": None, "source": "KB", "note": "band_no_match"}, "status": "needs_review"}

    return {"applied_range": {"low": None, "high": None, "source": "KB", "note": "no_applicable_range"}, "status": "needs_review"}


def _fallback_summary(context: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
    """Deterministic summary used when flagged values exist or LLM is empty."""
    age = context.get("age")
    sex = context.get("sex")
    flagged = [r for r in results if r["status"] not in ("normal", "missing", "needs_review")]

    if not results:
        return "No summary yet."

    if not flagged:
        return (
            f"All your reviewed values are within the applied reference ranges for age {age} ({str(sex).capitalize()}). "
            f"Everything looks good—keep up your current habits and routine checkups."
        )

    parts = [f"For age {age} ({str(sex).capitalize()}), we reviewed {len(results)} test(s): {len(flagged)} flagged."]
    for r in flagged:
        t = r["test"]
        v = r.get("value")
        u = r.get("unit") or ""
        rng = r["applied_range"]
        lo, hi = rng.get("low"), rng.get("high")
        rng_unit = rng.get("unit")
        rng_str = f"{lo}–{hi} {rng_unit}" if rng_unit else f"{lo}–{hi}"
        parts.append(f"• {t}: {v} {u} — {r['status']}. Reference: {rng_str} (KB)")
    return " ".join(parts)


# ─────────────────────────── endpoints ───────────────────────────

@router.post("/analyze")
async def analyze_report(
    report_name: Optional[str] = Form(None),
    age: Optional[int] = Form(None),
    sex: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    raw_bytes = await file.read()

    # Parse
    try:
        parsed = parse_pdf_bytes(raw_bytes)
        if isinstance(parsed, tuple):
            rows, ocr_confidence = parsed
        else:
            rows, ocr_confidence = parsed, 0.95
    except Exception as e:
        response = {
            "context": {"age": age, "sex": sex, "report_name": report_name, "report_id": str(uuid.uuid4())},
            "results": [],
            "diet_plan": None,
            "summary_text": None,
            "disclaimer": _build_disclaimer(),
            "issues": [f"parse_error: {e}"],
            "status": "needs_review",
            "meta": {"ocr_confidence": 0.0, "analyzer_version": "v2.0.0", "groq_used": False},
        }
        rid = response["context"]["report_id"]
        response["id"] = rid
        response.setdefault("filename", file.filename or "report.pdf")
        try:
            store.add(response)
        except Exception:
            pass
        return JSONResponse(status_code=200, content=response)

    parsed_results: List[Dict[str, Any]] = []
    aliased_count = 0
    debug_rows: List[Dict[str, Any]] = []

    # normalize once (avoid None / casing issues)
    age_eff = int(age) if age is not None else 30
    sex_eff = (sex or "any").lower()

    for row in rows:
        raw_name = row.get("test") or ""
        value = row.get("value")
        unit = (row.get("unit") or "").strip()

        # first normalize with your aliaser, then fall back to raw lower
        kb_key_in = normalize_test_name(raw_name) or (raw_name or "").strip().lower()
        if not kb_key_in:
            continue
        if kb_key_in != (raw_name or "").strip().lower():
            aliased_count += 1

        # infer unit for common counts if missing, then normalize
        value, unit = _infer_units_for_counts(kb_key_in, value, unit)
        value, unit = normalize_units_for_test(kb_key_in, value, unit)

        # status (resolver + RAG fallback inside)
        rs = _apply_range_and_status(kb_key_in, value, unit, age_eff, sex_eff)

        # display label: use resolved key if available
        kb_key_resolved = _resolve_kb_key(kb_key_in) or kb_key_in
        parsed_results.append({
            "test": _title_from_kb_key(kb_key_resolved),
            "value": value,
            "unit": unit,
            "applied_range": rs["applied_range"],
            "status": rs["status"],
            "source": "parsed",
        })

        if DEBUG_PARSE_ECHO:
            debug_rows.append({
                "raw": raw_name,
                "kb_key_in": kb_key_in,
                "kb_key_resolved": kb_key_resolved,
                "value": value,
                "unit": unit,
                "status": rs["status"],
                "applied": rs["applied_range"],
            })
            print(f"[DEBUG_ROW] raw={raw_name!r} in={kb_key_in!r} resolved={kb_key_resolved!r} "
                  f"value={value} unit={unit} -> {rs['status']} {rs['applied_range']}")

    flagged_count = sum(1 for r in parsed_results if r["status"] not in ("normal", "missing", "needs_review"))
    print(f"[DEBUG] rows_in={len(rows)} parsed={len(parsed_results)} aliased={aliased_count} flagged={flagged_count}")

    # Diet suggestions from KB
    diet_add, diet_limit = [], []
    for r in parsed_results:
        # r["test"] is pretty label; map back to KB key for advice
        kb_key_adv = _resolve_kb_key(r["test"].lower())
        kb_entry = KB.get(kb_key_adv) or {}
        adv = kb_entry.get("advice") or {}
        if r["status"].startswith("low") and adv.get("low"):
            diet_add.append(adv["low"])
        if r["status"].startswith("high") and adv.get("high"):
            diet_limit.append(adv["high"])
    diet_add = sorted({x for x in diet_add if x})
    diet_limit = sorted({x for x in diet_limit if x})
    diet_plan = {"add": diet_add, "limit": diet_limit} if (diet_add or diet_limit) else None

    # LLM summary + deterministic fallback
    structured = summarize_results_structured({"age": age_eff, "sex": sex_eff}, parsed_results) or {}
    llm_summary = structured.get("summary") or ""
    llm_diet = structured.get("diet_plan") or {}

    if llm_diet and (llm_diet.get("add") or llm_diet.get("limit")):
        diet_plan = llm_diet

    if flagged_count > 0:
        summary_text = _fallback_summary({"age": age_eff, "sex": sex_eff}, parsed_results)
        groq_used = False
    else:
        summary_text = llm_summary or _fallback_summary({"age": age_eff, "sex": sex_eff}, parsed_results)
        groq_used = bool(structured.get("_debug", {}).get("groq_used"))

    overall_status = "analyzed" if parsed_results else "needs_review"

    response = {
        "context": {"age": age, "sex": sex, "report_name": report_name, "report_id": str(uuid.uuid4())},
        "results": parsed_results,
        "diet_plan": diet_plan,
        "summary_text": summary_text or None,
        "disclaimer": _build_disclaimer(),
        "issues": None if parsed_results else ["no_rows_parsed"],
        "status": overall_status,
        "meta": {"ocr_confidence": float(ocr_confidence or 0.95), "analyzer_version": "v2.0.0", "groq_used": groq_used},
    }

    if DEBUG_PARSE_ECHO:
        response["_debug_rows"] = debug_rows  # helpful while inspecting; remove for prod

    # persist for /report/{id} & listing
    rid = response["context"]["report_id"]
    response["id"] = rid
    response.setdefault("filename", file.filename or "report.pdf")
    try:
        store.add(response)
    except Exception:
        pass

    return JSONResponse(status_code=200, content=response)


@router.get("/report/{rid}")
def get_report(rid: str):
    rep = store.get(rid)
    if not rep:
        raise HTTPException(status_code=404, detail="report_not_found")
    return rep


@router.get("/reports")
def list_reports(page: int = 1, page_size: int = 20):
    items = store.list(page=page, page_size=page_size)
    return {"items": items, "page": page, "page_size": page_size, "total": store.count()}
