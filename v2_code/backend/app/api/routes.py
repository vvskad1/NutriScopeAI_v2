# app/api/routes.py
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
import uuid, re, io

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from app.storage import reports_store as store
from app.ingest.parser import parse_pdf_bytes, normalize_test_name
from app.normalize.unit_normalization import normalize_units_for_test
from app.normalize.normalized_values import is_recognized_unit
from app.kb.loader import load_kb, get_entry_with_rag
from app.summarize.llm import summarize_results_structured, _get_groq_key
from app.rag.store import get_rag_store, RangeDoc
import os, json

from PyPDF2 import PdfReader

router = APIRouter(prefix="/api")
KB: Dict[str, Any] = load_kb()
DEBUG_PARSE_ECHO = True

def _build_disclaimer() -> str:
    return ("⚠️ NutriScope is an AI-powered tool designed to help you understand your lab reports. "
            "We use standard reference ranges for children, adults, and elderly patients, which may differ slightly from your testing "
            "laboratory’s ranges. Information and diet suggestions are educational only and should not replace consultation with a "
            "qualified healthcare professional.")

def _title_from_kb_key(k: str) -> str:
    if not k: return k
    parts = []
    for token in k.split():
        parts.append(token if "(" in token or ")" in token else token.capitalize())
    pretty = " ".join(parts)
    return (pretty.replace("Oh)", "OH)")
                  .replace("Ldl", "LDL")
                  .replace("Hdl", "HDL")
                  .replace("Tg", "TG"))

# ---------------- Fallback text parsing (when table parser returns 0) --------
CBC_FALLBACK_PATTERNS = [
    (r"White\s*Blood\s*Cell\s*\(WBC\)\s*[:\-]?\s*([\d.,]+)\s*([A-Za-z/%µμ^0-9]*)", "white blood cell (wbc)"),
    (r"Red\s*Blood\s*Cell\s*\(RBC\)\s*[:\-]?\s*([\d.,]+)\s*([A-Za-z/%µμ^0-9]*)", "red blood cell (rbc)"),
    (r"Hemoglobin.*?\(HB\/?Hgb\)?\)?\s*[:\-]?\s*([\d.,]+)\s*(g\/dL)?", "hemoglobin"),
    (r"Hematocrit.*?\(HCT\).*?[:\-]?\s*([\d.,]+)\s*(%)", "hematocrit"),
    (r"Mean\s*Cell\s*Volume\s*\(MCV\).*?[:\-]?\s*([\d.,]+)\s*(fL)?", "mean cell volume (mcv)"),
    (r"Mean\s*Cell\s*Hemoglobin\s*\(MCH\).*?[:\-]?\s*([\d.,]+)\s*(pg)?", "mean cell hemoglobin (mch)"),
    (r"Mean\s*Cell\s*Hb\s*Conc\s*\(MCHC\).*?[:\-]?\s*([\d.,]+)\s*(g\/dL)?", "mean cell hb conc (mchc)"),
    (r"Red\s*Cell\s*Dist\s*Width\s*\(RDW\).*?[:\-]?\s*([\d.,]+)\s*(%)", "red cell dist width (rdw)"),
    (r"Platelet\s*count\s*[:\-]?\s*([\d.,]+)\s*([A-Za-z/%µμ^0-9]*)", "platelet count"),
    (r"Mean\s*Platelet\s*Volume.*?[:\-]?\s*([\d.,]+)\s*(fL)?", "mean platelet volume (mpv)"),
    (r"Neutrophil.*?\(Neut\).*?[:\-]?\s*([\d.,]+)\s*(%)", "neutrophils %"),
    (r"Lymphocyte.*?\(Lymph\).*?[:\-]?\s*([\d.,]+)\s*(%)", "lymphocytes %"),
    (r"Monocyte.*?\(Mono\).*?[:\-]?\s*([\d.,]+)\s*(%)", "monocytes %"),
    (r"Eosinophil.*?\(Eos\).*?[:\-]?\s*([\d.,]+)\s*(%)", "eosinophils %"),
    (r"Basophil.*?\(Baso\).*?[:\-]?\s*([\d.,]+)\s*(%)", "basophils %"),
    (r"Neutrophil.*?Absolute.*?[:\-]?\s*([\d.,]+)\s*([A-Za-z/%µμ^0-9]*)", "absolute neutrophils"),
    (r"Lymphocyte.*?Absolute.*?[:\-]?\s*([\d.,]+)\s*([A-Za-z/%µμ^0-9]*)", "absolute lymphocytes"),
    (r"Monocyte.*?Absolute.*?[:\-]?\s*([\d.,]+)\s*([A-Za-z/%µμ^0-9]*)", "absolute monocytes"),
    (r"Eosinophil.*?Absolute.*?[:\-]?\s*([\d.,]+)\s*([A-Za-z/%µμ^0-9]*)", "absolute eosinophils"),
    (r"Basophil.*?Absolute.*?[:\-]?\s*([\d.,]+)\s*([A-Za-z/%µμ^0-9]*)", "absolute basophils"),
]

def _extract_rows_from_pdf_text_fallback(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join([page.extract_text() or "" for page in reader.pages])
    except Exception:
        return []
    rows: List[Dict[str, Any]] = []
    for pat, kb_like_name in CBC_FALLBACK_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE | re.DOTALL)
        if not m: continue
        raw_val = (m.group(1) or "").replace(",", "")
        try:
            val = float(raw_val)
        except Exception:
            continue
        unit = (m.group(2) or "").strip() if m.lastindex and m.lastindex >= 2 else ""
        # reasonable defaults when unit omitted
        if kb_like_name in {"white blood cell (wbc)", "platelet count"} and not unit:
            unit = "K/uL"
        if kb_like_name == "red blood cell (rbc)" and not unit:
            unit = "M/uL"
        if kb_like_name.startswith("absolute ") and not unit:
            unit = "K/uL"
        rows.append({"test": kb_like_name, "value": val, "unit": unit})
    return rows

# ---------------- Name resolution & status ----------------------------------
def _resolve_kb_key(name: str) -> Optional[str]:
    if not name: return None
    n = (name or "").strip().lower()
    if n in KB: return n
    if n.endswith(" %") and n[:-2].strip() in KB:
        return n[:-2].strip()
    no_parens = re.sub(r"\s*\([^)]*\)\s*", "", n).strip()
    if no_parens in KB: return no_parens

    m = re.search(r"\(([^)]+)\)", n)
    if m:
        for a in re.split(r"[\/\s,]+", m.group(1).strip().lower()):
            if not a: continue
            if a in KB: return a
            if f"{a} %" in KB: return f"{a} %"
        EXPAND = {
            "hb": "hemoglobin", "hgb": "hemoglobin", "hct": "hematocrit",
            "wbc": "white blood cell", "rbc": "red blood cell",
            "mcv": "mean corpuscular volume (mcv)",
            "mch": "mean corpuscular hemoglobin (mch)",
            "mchc": "mean corpuscular hemoglobin concentration (mchc)",
            "rdw": "red cell distribution width (rdw)",
            "mpv": "mean platelet volume (mpv)",
            "plt": "platelet count",
            "vit d": "vitamin d (25-oh)", "vitamin d3": "vitamin d (25-oh)",
        }
        lf = EXPAND.get(m.group(1).strip().lower())
        if lf and lf in KB:
            return lf

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
    for k, variants in CANON.items():
        if n == k or n in variants:
            for v in [n, k, *variants]:
                if v in KB: return v

    simp = " ".join(n.split())
    return simp if simp in KB else None

def _apply_range_and_status(
    kb_key_in: str, value: Optional[float], unit: str, age: int, sex: str
) -> Dict[str, Any]:
    kb_key = _resolve_kb_key(kb_key_in)
    kb_entry = KB.get(kb_key) if kb_key else None


    # RAG fallback if static KB misses it
    if not kb_entry:
        rag_entry = get_entry_with_rag(KB, kb_key_in) if kb_key_in else None
        if rag_entry and isinstance(rag_entry, dict) and rag_entry.get("ranges"):
            kb_entry = rag_entry
            kb_key = kb_key or kb_key_in

    # If still not found, or if ranges are missing/invalid, call Groq LLM for info
    needs_llm = False
    if not kb_entry or not kb_entry.get("ranges") or all((r.get("low") is None and r.get("high") is None) for r in kb_entry.get("ranges", [])):
        needs_llm = True
    if needs_llm:
        groq_key = _get_groq_key()
        if groq_key:
            from groq import Groq
            client = Groq(api_key=groq_key)
            try:
                models = []
                if "_discover_models" in globals():
                    from app.summarize.llm import _discover_models
                    models = _discover_models(client)
                if not models:
                    models = [os.getenv("GROQ_MODEL", "llama-2-70b-4096")]
                model_to_use = models[0] if models else "llama-2-70b-4096"
                prompt = f"For the lab test '{kb_key_in}', what is the standard unit and reference range for a {age}-year-old {sex}? Provide a JSON with keys: unit, ranges (list of dicts with low/high), and advice (dict with 'low' and 'high')."
                completion = client.chat.completions.create(
                    model=model_to_use,
                    messages=[
                        {"role": "system", "content": "You are a medical assistant AI."},
                        {"role": "user", "content": prompt},
                        {"role": "system", "content": "Return ONLY valid JSON. No prose."},
                    ],
                    temperature=0.1,
                    max_tokens=400,
                    response_format={"type": "json_object"},
                )
                content = completion.choices[0].message.content.strip()
                data = json.loads(content)
                kb_entry = {
                    "unit": data.get("unit"),
                    "ranges": data.get("ranges", []),
                    "advice": data.get("advice", {}),
                    "source": "groq_llm"
                }
                # Optionally, cache to RAG
                try:
                    doc = RangeDoc(
                        id=f"groq_{kb_key_in}",
                        test_name=kb_key_in,
                        unit=data.get("unit"),
                        ranges=data.get("ranges", []),
                        source="groq_llm",
                        notes="Auto-added from Groq LLM"
                    )
                    rag_store = get_rag_store()
                    rag_store.add_docs([doc])
                except Exception as e:
                    print(f"[RAG] Could not cache Groq doc: {e}")
            except Exception as e:
                print(f"[GROQ] Exception getting info for {kb_key_in}: {e}")
        if not kb_entry:
            return {"applied_range": {"low": None, "high": None, "source": "NONE", "note": "not_in_kb"}, "status": "needs_review"}

    # Convert value into the unit the KB expects (no hardcoding)
    kb_unit = (kb_entry.get("unit") or "").strip() or None
    norm_value, norm_unit = normalize_units_for_test(kb_key, value, unit, kb_unit)

    applied = {"low": None, "high": None, "source": "KB", "note": None}
    ranges = kb_entry.get("ranges") or []

    # fixed low/high
    chosen = None
    for r in ranges:
        applies = (r.get("applies") or {})
        s_ok = applies.get("sex") in (None, "any", sex)
        a_min = applies.get("age_min"); a_max = applies.get("age_max")
        a_ok = (a_min is None or age >= a_min) and (a_max is None or age <= a_max)
        if s_ok and a_ok and ("low" in r or "high" in r):
            chosen = r; break

    if chosen is not None:
        low, high = chosen.get("low"), chosen.get("high")
        applied["low"], applied["high"] = low, high
        if kb_unit: applied["unit"] = kb_unit
        if norm_value is None:
            return {"applied_range": applied, "status": "needs_review"}
        if low is not None and norm_value < low:
            return {"applied_range": applied, "status": "low"}
        if high is not None and norm_value > high:
            return {"applied_range": applied, "status": "high"}
        return {"applied_range": applied, "status": "normal"}

    # banded categories
    band_holder = next((r for r in ranges if (r.get("applies") or {}).get("sex") in (None, "any", sex) and r.get("bands")), None)
    if norm_value is not None and band_holder and band_holder.get("bands"):
        for b in band_holder["bands"]:
            b_min = float("-inf") if b.get("min") is None else b.get("min")
            b_max = float("inf") if b.get("max") is None else b.get("max")
            if b_min <= norm_value <= b_max:
                label = (b.get("label") or "").lower()
                status = "normal" if label in ("normal", "optimal", "sufficient") else label or "needs_review"
                applied["low"], applied["high"] = b.get("min"), b.get("max")
                applied["note"] = "banded"
                if kb_unit: applied["unit"] = kb_unit
                return {"applied_range": applied, "status": status}
        return {"applied_range": {"low": None, "high": None, "source": "KB", "note": "band_no_match"}, "status": "needs_review"}

    return {"applied_range": {"low": None, "high": None, "source": "KB", "note": "no_applicable_range"}, "status": "needs_review"}

# ---------------- Summary helpers ------------------------------------------
def _fallback_summary(context: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
    age = context.get("age"); sex = context.get("sex")
    if not results:
        return "We could not read any test values from this report. Please try a clearer PDF or use manual entry."
    flagged = [r for r in results if r["status"] not in ("normal", "missing", "needs_review")]
    if not flagged:
        return (f"All your reviewed values are within the applied reference ranges for age {age} ({str(sex).capitalize()}). "
                f"Everything looks good—keep up your current habits and routine checkups.")
    parts = [f"For age {age} ({str(sex).capitalize()}), we reviewed {len(results)} test(s): {len(flagged)} flagged."]
    for r in flagged:
        t, v, u = r["test"], r.get("value"), r.get("unit") or ""
        rng = r["applied_range"]; lo, hi = rng.get("low"), rng.get("high"); rng_u = rng.get("unit")
        rng_source = rng.get("source", "KB")
        rng_str = f"{lo}–{hi} {rng_u}" if rng_u else f"{lo}–{hi}"
        if rng_source == "groq_llm":
            parts.append(f"• {t}: {v} {u} — {r['status']}. Reference: {rng_str} (Groq LLM)")
        elif rng_source == "NONE":
            parts.append(f"• {t}: {v} {u} — {r['status']}. Reference: not available")
        else:
            parts.append(f"• {t}: {v} {u} — {r['status']}. Reference: {rng_str} (KB)")
    return " ".join(parts)

# ---------------- Endpoint: /api/analyze -----------------------------------
@router.post("/analyze")
async def analyze_report(
    report_name: Optional[str] = Form(None),
    age: Optional[int] = Form(None),
    sex: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    raw_bytes = await file.read()

    # 1) Primary parser
    try:
        parsed = parse_pdf_bytes(raw_bytes)
        rows, ocr_confidence = (parsed if isinstance(parsed, tuple) else (parsed, 0.95))
        if not rows:
            # 2) OCR/text fallback (very tolerant)
            rows = _extract_rows_from_pdf_text_fallback(raw_bytes)
    except Exception as e:
        response = {
            "context": {"age": age, "sex": sex, "report_name": report_name, "report_id": str(uuid.uuid4())},
            "results": [], "diet_plan": None, "summary_text": None, "disclaimer": _build_disclaimer(),
            "issues": [f"parse_error: {e}"], "status": "needs_review",
            "meta": {"ocr_confidence": 0.0, "analyzer_version": "v2.0.0", "groq_used": False},
        }
        response["id"] = response["context"]["report_id"]
        response.setdefault("filename", file.filename or "report.pdf")
        try: store.add(response)
        except Exception: pass
        return JSONResponse(status_code=200, content=response)

    age_eff = int(age) if age is not None else 30
    sex_eff = (sex or "any").lower()
    parsed_results: List[Dict[str, Any]] = []
    debug_rows: List[Dict[str, Any]] = []
    aliased_count = 0



    rag_store = get_rag_store()
    for row in rows:
        raw_name = row.get("test") or ""
        value = row.get("value")
        unit = (row.get("unit") or "").strip()
        if not is_recognized_unit(unit):
            if DEBUG_PARSE_ECHO:
                debug_rows.append({
                    "raw": raw_name, "value": value, "unit": unit, "status": "unrecognized_unit", "applied": None,
                })
            continue
        kb_key_in = normalize_test_name(raw_name) or (raw_name or "").strip().lower()
        if not kb_key_in:
            continue
        if kb_key_in != (raw_name or "").strip().lower():
            aliased_count += 1

        # Try KB, then RAG, then Groq LLM for test info
        kb_key_for_unit = _resolve_kb_key(kb_key_in) or kb_key_in
        kb_unit = None
        kb_entry_for_unit = KB.get(kb_key_for_unit)
        if not kb_entry_for_unit:
            rag_entry = get_entry_with_rag(KB, kb_key_for_unit)
            if rag_entry:
                kb_entry_for_unit = rag_entry
        # If still not found, call Groq LLM for info
        if not kb_entry_for_unit:
            # Compose a prompt for Groq to get unit, range, advice
            groq_key = _get_groq_key()
            if groq_key:
                from groq import Groq
                client = Groq(api_key=groq_key)
                # Try to auto-discover available models
                try:
                    models = []
                    if "_discover_models" in globals():
                        from app.summarize.llm import _discover_models
                        models = _discover_models(client)
                    if not models:
                        models = [os.getenv("GROQ_MODEL", "llama-2-70b-4096")]  # fallback to a likely available model
                    model_to_use = models[0] if models else "llama-2-70b-4096"
                    prompt = f"For the lab test '{raw_name}', what is the standard unit and reference range for a {age_eff}-year-old {sex_eff}? Provide a JSON with keys: unit, ranges (list of dicts with low/high), and advice (dict with 'low' and 'high')."
                    completion = client.chat.completions.create(
                        model=model_to_use,
                        messages=[
                            {"role": "system", "content": "You are a medical assistant AI."},
                            {"role": "user", "content": prompt},
                            {"role": "system", "content": "Return ONLY valid JSON. No prose."},
                        ],
                        temperature=0.1,
                        max_tokens=400,
                        response_format={"type": "json_object"},
                    )
                    content = completion.choices[0].message.content.strip()
                    data = json.loads(content)
                    # Compose a KB-like entry
                    kb_entry_for_unit = {
                        "unit": data.get("unit"),
                        "ranges": data.get("ranges", []),
                        "advice": data.get("advice", {}),
                        "source": "groq_llm"
                    }
                    # Optionally, cache to RAG
                    try:
                        doc = RangeDoc(
                            id=f"groq_{kb_key_for_unit}",
                            test_name=kb_key_for_unit,
                            unit=data.get("unit"),
                            ranges=data.get("ranges", []),
                            source="groq_llm",
                            notes="Auto-added from Groq LLM"
                        )
                        rag_store.add_docs([doc])
                    except Exception as e:
                        print(f"[RAG] Could not cache Groq doc: {e}")
                except Exception as e:
                    print(f"[GROQ] Exception getting info for {raw_name}: {e}")
        if kb_entry_for_unit:
            kb_unit = (kb_entry_for_unit.get("unit") or "").strip() or None

        norm_value, norm_unit = normalize_units_for_test(kb_key_for_unit, value, unit, kb_unit)
        rs = _apply_range_and_status(kb_key_in, norm_value, norm_unit, age_eff, sex_eff)

        kb_key_resolved = _resolve_kb_key(kb_key_in) or kb_key_in
        parsed_results.append({
            "test": _title_from_kb_key(kb_key_resolved),
            "value": norm_value,
            "unit": norm_unit,
            "applied_range": rs["applied_range"],
            "status": rs["status"],
            "source": "parsed",
        })

        if DEBUG_PARSE_ECHO:
            debug_rows.append({
                "raw": raw_name, "kb_key_in": kb_key_in, "kb_key_resolved": kb_key_resolved,
                "value": norm_value, "unit": norm_unit, "status": rs["status"], "applied": rs["applied_range"],
            })

    flagged_count = sum(1 for r in parsed_results if r["status"] not in ("normal", "missing", "needs_review"))
    if DEBUG_PARSE_ECHO:
        print(f"[DEBUG] rows_in={len(rows)} parsed={len(parsed_results)} aliased={aliased_count} flagged={flagged_count}")
        for dr in debug_rows[:30]:
            print("[DEBUG_ROW]", dr)

    # Diet suggestions (from KB only; RAG may not have advice)
    diet_add, diet_limit = [], []
    for r in parsed_results:
        kb_key_adv = _resolve_kb_key(r["test"].lower())
        adv = (KB.get(kb_key_adv) or {}).get("advice") or {}
        if r["status"].startswith("low") and adv.get("low"): diet_add.append(adv["low"])
        if r["status"].startswith("high") and adv.get("high"): diet_limit.append(adv["high"])
    diet_add = sorted({x for x in diet_add if x}); diet_limit = sorted({x for x in diet_limit if x})
    diet_plan = {"add": diet_add, "limit": diet_limit} if (diet_add or diet_limit) else None

    structured = summarize_results_structured({"age": age_eff, "sex": sex_eff}, parsed_results) or {}
    llm_summary = structured.get("summary") or ""
    llm_diet = structured.get("diet_plan") or {}
    llm_per_test = structured.get("per_test") or []
    if llm_diet and (llm_diet.get("add") or llm_diet.get("limit")):
        diet_plan = llm_diet

    if not parsed_results or flagged_count > 0:
        summary_text = _fallback_summary({"age": age_eff, "sex": sex_eff}, parsed_results); groq_used = False
    else:
        summary_text = llm_summary or _fallback_summary({"age": age_eff, "sex": sex_eff}, parsed_results)
        groq_used = bool(structured.get("_debug", {}).get("groq_used"))

    overall_status = "analyzed" if parsed_results else "needs_review"
    response = {
        "context": {"age": age, "sex": sex, "report_name": report_name, "report_id": str(uuid.uuid4())},
        "results": parsed_results, "diet_plan": diet_plan, "summary_text": summary_text or None,
        "per_test": llm_per_test,
        "disclaimer": _build_disclaimer(), "issues": None if parsed_results else ["no_rows_parsed"],
        "status": overall_status,
        "meta": {"ocr_confidence": float(locals().get("ocr_confidence", 0.95)), "analyzer_version": "v2.0.0", "groq_used": groq_used},
    }
    if DEBUG_PARSE_ECHO: response["_debug_rows"] = debug_rows

    rid = response["context"]["report_id"]; response["id"] = rid
    response.setdefault("filename", file.filename or "report.pdf")
    try: store.add(response)
    except Exception: pass
    return JSONResponse(status_code=200, content=response)

# ---------------- Listing & detail -----------------------------------------
@router.get("/report/{rid}")
def get_report(rid: str):
    rep = store.get(rid)
    if not rep: raise HTTPException(status_code=404, detail="report_not_found")
    return rep


