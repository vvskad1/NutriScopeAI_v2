
# Ensure .env is loaded for all LLM endpoints

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# FastAPI test endpoint for plain prompt LLM test
from fastapi import APIRouter
plain_prompt_router = APIRouter()

@plain_prompt_router.post('/api/llm_plain_mealplan')
def llm_plain_mealplan():
    key = _get_groq_key() if "_get_groq_key" in globals() else os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return {"error": "No GROQ_API_KEY set"}
    try:
        client = Groq(api_key=key)
    except Exception as e:
        return {"error": f"Groq client error: {e}"}
    prompt = (
        "Given these flagged lab results: "
        "Red Blood Cell (RBC): 1.8 million/μl (low), Hemoglobin: 6.5 g/dL (low), Hematocrit: 19.5% (low). "
        "What are 3 specific meal ideas (with ingredients and instructions) that would help improve these results? "
        "Please explain why each meal is helpful."
    )
    # Try all available models in order
    models = []
    try:
        if "_discover_models" in globals():
            models = _discover_models(client)
        if not models:
            models = [os.getenv("GROQ_MODEL", "").strip()] if os.getenv("GROQ_MODEL", "").strip() else []
        if not models:
            models = ["llama-3.3-70b-specdec", "llama-guard-3-8b"]
    except Exception as e:
        print(f"[GROQ] Model selection failed: {e}")
        models = ["llama-3.3-70b-specdec", "llama-guard-3-8b"]

    for model in models:
        if not model:
            continue
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=600,
            )
            content = completion.choices[0].message.content.strip()
            print(f"[GROQ][PLAIN PROMPT TEST][{model}]", content)
            return {"result": content, "model": model}
        except Exception as e:
            print(f"[GROQ][PLAIN PROMPT TEST][{model}] failed: {e}")
            continue
    return {"error": "All models failed"}
# app/summarize/llm.py

import os, json, time
from typing import List, Dict, Any, Tuple, Optional
from groq import Groq
from groq import GroqError, BadRequestError


# Candidate chat models to try (order = preference). You can override with GROQ_MODEL.
CANDIDATES: List[str] = [
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    # Add more as needed
]

DISCOVERY_TTL_SEC = 3600  # re-discover available models every hour
_discovered: Dict[str, Any] = {"ts": 0, "models": []}
def _try_completion(client: Groq, model: str) -> bool:
    """
    Probe the model with a tiny request; return True if it succeeds.
    Keeps it minimal to avoid usage cost.
    """
    try:
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            temperature=0.0,
        )
        return True
    except BadRequestError as e:
        if "model_decommissioned" in str(e) or "not_found" in str(e):
            return False
        return False
    except Exception:
        return False

def resolve_model(client: Groq) -> str:
    """
    Choose a working model:
    1) Use GROQ_MODEL if provided and probe it.
    2) Otherwise probe candidates until one works.
    Raises a helpful error if none are usable.
    """
    env_model = os.getenv("GROQ_MODEL")
    if env_model:
        if _try_completion(client, env_model):
            return env_model
    for m in CANDIDATES:
        if _try_completion(client, m):
            return m
    raise GroqError(
        "No working Groq chat model found. "
        "Set GROQ_MODEL to a supported model shown in your Groq console."
    )

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

# Print available Groq models at startup for user convenience
def _print_groq_models():
    try:
        from groq import Groq
        key = os.getenv("GROQ_API_KEY", "").strip()
        if not key:
            print("[GROQ] No API key set, cannot list models.")
            return
        client = Groq(api_key=key)
        resp = client.models.list()
        ids = [m.id for m in getattr(resp, "data", []) if getattr(m, "id", None)]
        print(f"[GROQ] Available models: {ids}")
    except Exception as e:
        print(f"[GROQ] Could not list models: {e}")

_print_groq_models()

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
    # Only flag truly abnormal (high/low), not borderline or needs_review
    normals = [r for r in results if r["status"] == "normal"]
    flagged = [r for r in results if r["status"] in ("high", "low")]

    if not results:
        return {
            "summary": "We could not read any test values from this report. Please try a clearer PDF or use manual entry.",
            "diet_plan": {},
            "per_test": [],
            "_debug": {"groq_used": False, "path": "fallback", "reason": "no_results"}
        }

    if not flagged:
        return {
            "summary": (
                f"All your reviewed values are within the applied reference ranges for age {context.get('age')} "
                f"({context.get('sex')}). Everything looks good—keep up your current habits and routine checkups."
            ),
            "diet_plan": {},
            "per_test": [],
            "_debug": {"groq_used": False, "path": "fallback", "reason": "no_flagged"}
        }

    per = []
    fallback_meals = []
    # Always call LLM for every test to generate all fields
    try:
        key = _get_groq_key() if "_get_groq_key" in globals() else os.getenv("GROQ_API_KEY", "").strip()
        client = Groq(api_key=key)
        model = resolve_model(client)
        for r in flagged:
            test = r["test"]
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
            prompt = (
                f"Lab test: {test} ({r.get('value','')} {r.get('unit','')}), status: {status_text}.\n"
                "Please provide the following as clear, readable English sentences: "
                f"1) Why Important: What is the importance of this test?\n"
                f"2) Reason for High/Low: What are the common reasons for abnormal results?\n"
                f"3) Risks: What are the risks if the result is abnormal?\n"
                "Return a JSON object with keys: importance, reason, risks."
            )
            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a medical AI assistant. Return ONLY valid JSON with keys: importance, reason, risks. No prose."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    max_tokens=300,
                    response_format={"type": "json_object"},
                )
                content = completion.choices[0].message.content.strip()
                ai_data = json.loads(content)
                per.append({
                    "test": test,
                    "value": r.get("value"),
                    "unit": r.get("unit"),
                    "status": status_text,
                    "range": rng_text,
                    "importance": ai_data.get("importance", ""),
                    "reason": ai_data.get("reason", ""),
                    "risks": ai_data.get("risks", ""),
                })
            except Exception as e:
                print(f"[GROQ][per_test fallback] Exception for {test}: {e}")
                per.append({
                    "test": test,
                    "value": r.get("value"),
                    "unit": r.get("unit"),
                    "status": status_text,
                    "range": rng_text,
                    "importance": f"No AI explanation available for {test}.",
                    "reason": f"No AI reason available for {test}.",
                    "risks": f"No AI risks available for {test}.",
                })
    except Exception as e:
        print(f"[GROQ][per_test fallback] LLM client error: {e}")

        # Fallback meal ideas per test
        test_lc = test.lower()
        if "vitamin d" in test_lc:
            fallback_meals.append({
                "name": "Grilled Salmon with Mushrooms",
                "ingredients": ["1 salmon fillet", "1 cup mushrooms", "1 tsp olive oil", "lemon wedge"],
                "instructions": "Grill salmon and mushrooms, drizzle with olive oil and lemon.",
                "why_this_meal": "Salmon and mushrooms are rich in vitamin D.",
                "for_tests": [test]
            })
        elif "b12" in test_lc:
            fallback_meals.append({
                "name": "Egg & Cheese Breakfast Wrap",
                "ingredients": ["2 eggs", "1 whole wheat tortilla", "1 slice cheese", "spinach"],
                "instructions": "Scramble eggs, add cheese and spinach, wrap in tortilla.",
                "why_this_meal": "Eggs and cheese are good sources of vitamin B12.",
                "for_tests": [test]
            })
        elif "iron" in test_lc or "hemoglobin" in test_lc or "hematocrit" in test_lc:
            fallback_meals.append({
                "name": "Spinach & Lentil Stew",
                "ingredients": ["1 cup cooked lentils", "2 cups spinach", "1 tomato", "onion", "spices"],
                "instructions": "Cook lentils, add spinach, tomato, onion, and spices. Simmer until tender.",
                "why_this_meal": "Lentils and spinach are high in iron.",
                "for_tests": [test]
            })
        elif "calcium" in test_lc:
            fallback_meals.append({
                "name": "Yogurt Parfait",
                "ingredients": ["1 cup yogurt", "1/2 cup berries", "granola"],
                "instructions": "Layer yogurt, berries, and granola in a glass.",
                "why_this_meal": "Yogurt is rich in calcium.",
                "for_tests": [test]
            })
        elif "urea" in test_lc or "creatinine" in test_lc:
            fallback_meals.append({
                "name": "Hydrating Fruit Salad",
                "ingredients": ["1 cup watermelon", "1 cup cucumber", "mint leaves"],
                "instructions": "Chop fruits, mix with mint, and serve chilled.",
                "why_this_meal": "Watermelon and cucumber help with hydration, supporting kidney health.",
                "for_tests": [test]
            })
        # Add more mappings as needed for other tests

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
        "diet_plan": {"meals": fallback_meals},
        "per_test": per,
        "_debug": {"groq_used": False, "path": "fallback", "reason": "groq_not_used_or_failed"}
    }

def _groq_structured_summary(context: Dict[str, Any], results: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
    key = _get_groq_key() if "_get_groq_key" in globals() else os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        print("[GROQ] Missing GROQ_API_KEY (call-time)")
        return False, {}

    # Partition results
    flagged = [r for r in results if r["status"] in ("high", "low")]
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
        "IMPORTANT: Return ONLY a JSON object with a 'diet_plan' key containing a 'meals' list (at least 3 meal ideas, never empty), and a 'per_test' list with an entry for every test in the input.\n"
        "For each test in 'per_test', generate all fields (importance, reason, risks, etc.) as clear, readable, normal English sentences, even if the knowledge base is empty. Do NOT leave any field blank.\n"
        "Example format: { 'diet_plan': { 'meals': [ { 'name': 'Meal 1', 'ingredients': [...], 'instructions': '...', 'why_this_meal': '...', 'for_tests': [...] }, ... ] }, 'per_test': [ { 'test': 'Vitamin D', 'importance': 'Vitamin D is important for...', 'reason': 'Low levels may be due to...', 'risks': 'Risks include...' }, ... ] }\n"
        "Each meal must have: 'name', 'ingredients', 'instructions', 'why_this_meal', and 'for_tests'.\n"
        "Each per_test entry must have: 'test', 'importance', 'reason', 'risks', and other relevant fields.\n"
        "Do NOT include any other keys, text, or explanation."
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

    try:
        model = resolve_model(client)
        print(f"[GROQ] Using model: {model} with {len(payload)} {mode} items")
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
        print("[GROQ][DEBUG] LLM JSON response:", json.dumps(data, indent=2, ensure_ascii=False))
        # Extra debug: print just the meal plan for quick inspection
        meal_plan = data.get("diet_plan") or {}
        print("[GROQ][DEBUG] LLM meal plan only:", json.dumps(meal_plan, indent=2, ensure_ascii=False))
        data.setdefault("diet_plan", {"add": [], "limit": []})
        data.setdefault("per_test", [])
        # Ensure every test in the input has a per_test entry with all required fields, and all are AI-generated
        input_tests = [r["test"] for r in results]
        per_test_dict = {p.get("test"): p for p in data["per_test"]}
        required_fields = ["test", "importance", "reason", "risks"]
        key = _get_groq_key() if "_get_groq_key" in globals() else os.getenv("GROQ_API_KEY", "").strip()
        client = Groq(api_key=key)
        model = resolve_model(client)
        for test in input_tests:
            missing = False
            if test not in per_test_dict:
                missing = True
            else:
                for field in required_fields:
                    if field not in per_test_dict[test] or not per_test_dict[test][field]:
                        missing = True
                        break
            if missing:
                # Re-call LLM for just this test to fill in missing data
                r = next((x for x in results if x["test"] == test), None)
                if r:
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
                    prompt = (
                        f"Lab test: {test} ({r.get('value','')} {r.get('unit','')}), status: {status_text}.\n"
                        "Please provide the following as clear, readable English sentences: "
                        f"1) Why Important: What is the importance of this test?\n"
                        f"2) Reason for High: What are the common reasons for high results?\n"
                        f"3) Reason for Low: What are the common reasons for low results?\n"
                        f"4) Risks: What are the risks if the result is abnormal?\n"
                        "Return a JSON object with keys: importance, reason_high, reason_low, risks."
                    )
                    try:
                        completion = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": "You are a medical AI assistant. Return ONLY valid JSON with keys: importance, reason_high, reason_low, risks, value, unit, status. No prose."},
                                {"role": "user", "content": prompt},
                            ],
                            temperature=0.2,
                            max_tokens=400,
                            response_format={"type": "json_object"},
                        )
                        content = completion.choices[0].message.content.strip()
                        ai_data = json.loads(content)
                        per_test_dict[test] = {
                            "test": test,
                            "value": r.get("value", ""),
                            "unit": r.get("unit", ""),
                            "status": status_text,
                            "importance": ai_data.get("importance", ""),
                            "reason_high": ai_data.get("reason_high", ""),
                            "reason_low": ai_data.get("reason_low", ""),
                            "risks": ai_data.get("risks", ""),
                        }
                    except Exception as e:
                        print(f"[GROQ][per_test single LLM call] Exception for {test}: {e}")
                        per_test_dict[test] = {
                            "test": test,
                            "value": r.get("value", ""),
                            "unit": r.get("unit", ""),
                            "status": status_text,
                            "importance": "",
                            "reason_high": "",
                            "reason_low": "",
                            "risks": "",
                        }
        # Overwrite per_test with the complete list in input order
        data["per_test"] = [per_test_dict[test] for test in input_tests]
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
        print(f"[GROQ] All models failed or exception: {e}")
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
    flagged = [r for r in results if r["status"] in ("high", "low")]
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
    # If LLM fails, do not return fallback/static meal plan. Return error message only.
    return {
        "summary": "Sorry, we could not generate a meal plan at this time. Please try again later.",
        "diet_plan": {},
        "per_test": [],
        "_debug": {"groq_used": False, "path": "no_llm", "reason": "llm_failed_no_fallback"}
    }
