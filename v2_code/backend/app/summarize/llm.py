# app/summarize/llm.py
import os, json, time
from typing import List, Dict, Any, Tuple
from groq import Groq

DISCOVERY_TTL_SEC = 3600  # re-discover available models every hour
_discovered: Dict[str, Any] = {"ts": 0, "models": []}

def _get_groq_key() -> str:
    return os.getenv("GROQ_API_KEY", "").strip()

def _discover_models(client: Groq) -> List[str]:
    """Ask Groq for current models and return a ranked list of viable chat-completions models."""
    now = time.time()
    if _discovered["models"] and (now - _discovered["ts"] < DISCOVERY_TTL_SEC):
        return _discovered["models"]

    try:
        resp = client.models.list()
        ids: List[str] = [m.id for m in getattr(resp, "data", []) if getattr(m, "id", None)]
    except Exception as e:
        print(f"[GROQ] Model discovery failed: {e}")
        return _discovered["models"] or []

    # Heuristics: prefer models that look like chat-capable LLMs (exclude audio/vision/embeddings/tools)
    def is_chat_candidate(mid: str) -> bool:
        s = mid.lower()
        # Keep llama/gemma/mixtral style text/chat models. Exclude embeddings/audio/whisper/tokenizers.
        bad = ("embed", "whisper", "audio", "tts", "stt", "vision", "token", "tool", "rerank")
        return any(x in s for x in ("llama", "gemma", "mixtral")) and not any(b in s for b in bad)

    candidates = [m for m in ids if is_chat_candidate(m)]

    # Rank: bigger and newer-looking first
    def score(mid: str) -> Tuple[int, int, int, int]:
        s = mid.lower()
        # crude size hints
        size = 0
        if "405b" in s or "400b" in s or "340b" in s: size = 405
        elif "200b" in s: size = 200
        elif "90b" in s: size = 90
        elif "70b" in s: size = 70
        elif "40b" in s: size = 40
        elif "30b" in s: size = 30
        elif "11b" in s: size = 11
        elif "8b" in s: size = 8
        elif "3b" in s or "1b" in s: size = 3

        # favor text/chat over instruct if both exist, but both are fine
        is_text = 1 if "text" in s or "chat" in s else 0
        is_llama = 1 if "llama" in s else 0
        is_preview = 1 if "preview" in s else 0  # sometimes previews are newer/better
        return (is_llama, size, is_text, is_preview)

    ranked = sorted(candidates, key=score, reverse=True)

    # Allow explicit override/priority via env GROQ_MODELS (comma-separated)
    env_val = os.getenv("GROQ_MODELS", "").strip()
    if env_val:
        preferred = [m.strip() for m in env_val.split(",") if m.strip()]
        # keep only those that exist; then append the rest
        preferred_existing = [m for m in preferred if m in ranked]
        ranked = preferred_existing + [m for m in ranked if m not in preferred_existing]

    # Cache
    _discovered["ts"] = now
    _discovered["models"] = ranked
    if os.getenv("GROQ_VERBOSE", "0") == "1":
        print(f"[GROQ] Discovered models (top 10): {ranked[:10]}")
    return ranked

# --- Load KB so we can enrich prompts with importance/causes/advice
try:
    from app.kb.loader import load_kb
    KB = load_kb()  # dict keyed by test_name.lower()
except Exception:
    KB = {}

def _kb_snippet(test_name: str) -> Dict[str, Any]:
    entry = KB.get(test_name.lower(), {}) if test_name else {}
    if not entry:
        return {}
    return {
        "importance": entry.get("importance", ""),
        "causes": entry.get("causes", []) or [],
        "advice": entry.get("advice", {}) or {},
    }

def _fallback_summary(context: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Local deterministic summary + diet plan (guarantees non-empty response)."""
    normals = [r for r in results if r["status"] == "normal"]
    flagged = [r for r in results if r["status"] not in ("normal", "missing", "needs_review")]

    if not results:
        return {
            "summary": "We could not read any test values from this report. Please try a clearer PDF or use manual entry.",
            "diet_plan": {"add": [], "limit": []},
            "per_test": [],
            "_debug": {"groq_used": False, "path": "fallback", "reason": "no_results"}
        }

    if not flagged:
        return {
            "summary": (
                f"All your reviewed values are within the applied reference ranges for age {context.get('age')} "
                f"({context.get('sex')}). Everything looks good—keep up your current habits and routine checkups."
            ),
            "diet_plan": {"add": [], "limit": []},
            "per_test": [],
            "_debug": {"groq_used": False, "path": "fallback", "reason": "no_flagged"}
        }

    add, limit, per = [], [], []

    for r in flagged:
        test = r["test"]
        kbs = _kb_snippet(test)
        status_text = r["status"].replace("_", " ")

        rng = r.get("applied_range", {})
        if rng.get("low") is not None and rng.get("high") is not None:
            rng_text = f"{rng['low']}–{rng['high']} ({rng.get('source', 'KB')})"
        elif rng.get("low") is not None:
            rng_text = f"≥{rng['low']} ({rng.get('source', 'KB')})"
        elif rng.get("high") is not None:
            rng_text = f"≤{rng['high']} ({rng.get('source', 'KB')})"
        else:
            rng_text = "not available"

        per.append({
            "test": test,
            "value": r.get("value"),
            "unit": r.get("unit"),
            "status": status_text,
            "range": rng_text,
            "importance": kbs.get("importance", ""),
            "reasons": kbs.get("causes", [])[:4],
            "next_steps": (
                [kbs.get("advice", {}).get("low")] if "low" in r["status"] and kbs.get("advice", {}).get("low") else []
            ) or (
                [kbs.get("advice", {}).get("high")] if "high" in r["status"] and kbs.get("advice", {}).get("high") else []
            )
        })

        adv = kbs.get("advice", {})
        if "low" in r["status"] and adv.get("low"):
            add.append(adv["low"])
        if "high" in r["status"] and adv.get("high"):
            limit.append(adv["high"])

    # dedupe
    add = sorted({x for x in add if x})
    limit = sorted({x for x in limit if x})

    tests_word = "tests" if len(results) != 1 else "test"
    header = (
        f"For age {context.get('age')} ({context.get('sex')}), we reviewed {len(results)} {tests_word}: "
        f"{len(flagged)} flagged, {len(normals)} normal."
    )
    bullets = [
        f"{p['test']}: {p['value']} {p['unit'] or ''} — {p['status']}; reference {p['range']}."
        for p in per
    ]

    return {
        "summary": " ".join([header] + bullets + [
            "Consider following the diet tips and consult a clinician if symptoms persist."
        ]),
        "diet_plan": {"add": add, "limit": limit},
        "per_test": per,
        "_debug": {"groq_used": False, "path": "fallback", "reason": "groq_not_used_or_failed"}
    }

def _groq_structured_summary(context: Dict[str, Any], results: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
    key = _get_groq_key() if "_get_groq_key" in globals() else os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        print("[GROQ] Missing GROQ_API_KEY (call-time)")
        return False, {}

    # Partition results
    flagged = [r for r in results if r["status"] not in ("normal", "missing", "needs_review")]
    normals = [r for r in results if r["status"] == "normal"]

    if not results:
        print("[GROQ] No results -> skip Groq")
        return False, {}

    # Build payload
    payload_flagged = []
    for r in flagged:
        payload_flagged.append({
            "test": r["test"],
            "value": r.get("value"),
            "unit": r.get("unit"),
            "status": r["status"],
            "range": r.get("applied_range", {}),
            "kb": _kb_snippet(r["test"]),
        })

    payload = payload_flagged
    mode = "flagged"
    if not payload_flagged:
        # No flagged items — include a few normals so Groq can craft a “you’re good” message
        payload_normals = []
        # cap to a few to keep prompt short
        for r in normals[:6]:
            payload_normals.append({
                "test": r["test"],
                "value": r.get("value"),
                "unit": r.get("unit"),
                "status": r["status"],
                "range": r.get("applied_range", {}),
                "kb": _kb_snippet(r["test"]),
            })
        payload = payload_normals
        mode = "normals"

    if not payload:
        print("[GROQ] Results exist but empty payload after filtering -> skip Groq")
        return False, {}

    sys_text = (
        "You are a medical assistant. Create a short, patient-friendly summary of lab results. "
        "If any flagged results are provided, explain: why the test matters, why it may be low/high, potential risks, and next steps. "
        "If only normal results are provided, return a brief positive reassurance. "
        "Use the provided KB info (importance, common reasons, advice). "
        "No diagnoses. Keep it concise and actionable. Return ONLY valid JSON."
    )

    usr_obj = {
        "context": {"age": context.get("age"), "sex": context.get("sex")},
        "mode": mode,  # "flagged" or "normals" (for the model to adapt tone)
        "results": payload,  # unified key now
        "output_schema": {
            "per_test": [
                {
                    "test": "string",
                    "value": "string",
                    "unit": "string",
                    "status": "string (low/high/normal/etc.)",
                    "importance": "1–2 lines",
                    "why_low": ["reasons if low"],
                    "why_high": ["reasons if high"],
                    "risks_if_low": ["problems if persistently low"],
                    "risks_if_high": ["problems if persistently high"],
                    "next_steps": ["practical actions"]
                }
            ],
            "diet_plan": {"add": ["…"], "limit": ["…"]},
            "overall_message": "1–2 lines wrap-up for the user"
        }
    }

    try:
        client = Groq(api_key=key)
    except Exception as e:
        print(f"[GROQ] Client init failed: {e}")
        return False, {}

    models = []
    try:
        # Use discovery if present; else fall back to a safe set
        if "_discover_models" in globals():
            models = _discover_models(client)
        if not models:
            models = [os.getenv("GROQ_MODEL", "").strip()] if os.getenv("GROQ_MODEL", "").strip() else []
        if not models:
            # last-resort defaults; will skip any decommissioned via exception
            models = ["llama-3.3-70b-specdec", "llama-guard-3-8b"]  # replace with any known-good in your account
    except Exception as e:
        print(f"[GROQ] Model selection failed: {e}")
        models = []

    if not models:
        print("[GROQ] No models to try -> skip Groq")
        return False, {}

    for model in models:
        if not model:
            continue
        try:
            print(f"[GROQ] Trying model: {model} with {len(payload)} {mode} items")
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": sys_text},
                    {"role": "user", "content": json.dumps(usr_obj, ensure_ascii=False)},
                    {"role": "system", "content": "Return ONLY valid JSON. No prose."},
                ],
                temperature=0.1,
                max_tokens=400,
                response_format={"type": "json_object"},
            )
            content = completion.choices[0].message.content.strip()
            data = json.loads(content)
            data.setdefault("diet_plan", {"add": [], "limit": []})
            data.setdefault("per_test", [])
            # compose summary on top of per_test (keeps your consistent format)
            try:
                summary_text = _compose_summary(context, results, data.get("per_test", []))
                data["summary"] = summary_text or data.get("overall_message", "")
            except Exception:
                data.setdefault("summary", data.get("overall_message", ""))

            data["_debug"] = {"groq_used": True, "path": "groq", "model": model, "mode": mode}
            print(f"[GROQ] Success with {model} (mode={mode})")
            return True, data

        except Exception as e:
            print(f"[GROQ] Exception with {model}: {e}")
            continue

    print("[GROQ] All models failed, falling back")
    return False, {}

def _compose_summary(context: Dict[str, Any],
                     results: List[Dict[str, Any]],
                     per_test_struct: List[Dict[str, Any]]) -> str:
    """
    Build a clean, consistent summary:
      - For each test: What it is (importance), result vs range, why low/high, potential problems, next steps.
      - For normals in `results`: one-liner “looks good”.
    """
    by_test = {p.get("test",""): p for p in per_test_struct or []}

    lines: List[str] = []
    age, sex = context.get("age"), context.get("sex")

    # Header
    flagged = [r for r in results if r["status"] not in ("normal","missing","needs_review")]
    normals = [r for r in results if r["status"] == "normal"]
    lines.append(f"For age {age} ({sex}), we reviewed {len(results)} test(s): {len(flagged)} flagged, {len(normals)} normal.")

    # Flagged details
    for r in flagged:
        t = r["test"]
        p = by_test.get(t, {})
        val = r.get("value")
        unit = r.get("unit") or ""
        rng = r.get("applied_range", {})
        rng_text = None
        if rng.get("low") is not None and rng.get("high") is not None:
            rng_text = f"{rng['low']}–{rng['high']} ({rng.get('source','KB')})"
        elif rng.get("low") is not None:
            rng_text = f"≥{rng['low']} ({rng.get('source','KB')})"
        elif rng.get("high") is not None:
            rng_text = f"≤{rng['high']} ({rng.get('source','KB')})"

        status = r["status"].replace("_"," ")

        # Importance
        if p.get("importance"):
            lines.append(f"\n• {t}: {val} {unit} — {status}. Reference: {rng_text or 'n/a'}")
            lines.append(f"  Why it matters: {p['importance']}")
        else:
            lines.append(f"\n• {t}: {val} {unit} — {status}. Reference: {rng_text or 'n/a'}")

        # Why low/high
        if "low" in r["status"] and p.get("why_low"):
            lines.append("  Why it may be low: " + "; ".join(p["why_low"][:5]) + ".")
        if "high" in r["status"] and p.get("why_high"):
            lines.append("  Why it may be high: " + "; ".join(p["why_high"][:5]) + ".")

        # Potential problems
        if "low" in r["status"] and p.get("risks_if_low"):
            lines.append("  Potential problems if low persists: " + "; ".join(p["risks_if_low"][:5]) + ".")
        if "high" in r["status"] and p.get("risks_if_high"):
            lines.append("  Potential problems if high persists: " + "; ".join(p["risks_if_high"][:5]) + ".")

        # Next steps
        if p.get("next_steps"):
            lines.append("  Next steps: " + "; ".join(p["next_steps"][:6]) + ".")

    # Normals (short positive)
    if normals:
        norms = []
        for r in normals:
            t = r["test"]
            val = r.get("value")
            unit = r.get("unit") or ""
            norms.append(f"{t} ({val} {unit})")
        lines.append("\n✅ Within normal range: " + ", ".join(norms) + ". Keep up the good habits!")

    return "\n".join(lines).strip()


def summarize_results_structured(context: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
    ok, data = _groq_structured_summary(context, results)
    if ok and (data.get("summary") or data.get("diet_plan") or data.get("per_test")):
        return data
    fb = _fallback_summary(context, results)
    if "_debug" not in fb:
        fb["_debug"] = {"groq_used": False, "path": "fallback", "reason": "unknown"}
    return fb
