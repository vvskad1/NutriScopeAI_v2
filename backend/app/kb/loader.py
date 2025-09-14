# app/kb/loader.py
from __future__ import annotations
from typing import Dict, Any, Optional, List
import json, os
from app.rag.store import get_rag_store  # <-- uses our tiny RAG store

def load_kb() -> Dict[str, Any]:
    path = os.getenv("KB_PATH", os.path.join(os.path.dirname(__file__), "tests_kb_v2.json"))
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Support both dict and list KB formats
    if isinstance(data, list):
        kb_dict = {}
        import re
        for entry in data:
            name = entry.get("test_name", "").strip()
            name_lc = name.lower()
            # Add canonical
            if name_lc:
                kb_dict[name_lc] = entry
            # Add parenthetical-stripped alias (e.g., "hemoglobin (hgb)" -> "hemoglobin")
            name_noparen = re.sub(r"\s*\([^)]*\)", "", name).strip().lower()
            if name_noparen and name_noparen != name_lc:
                kb_dict[name_noparen] = entry
            # Add all aliases if present
            for alias in entry.get("aliases", []):
                alias_lc = alias.strip().lower()
                if alias_lc:
                    kb_dict[alias_lc] = entry
        # Add placeholder KB entries for MCV, MCH, MCHC, RDW if missing
        for missing in [
            ("mcv", "Mean Corpuscular Volume (MCV)", "fL", "Indicates average size of red blood cells.", ["Iron deficiency", "B12/folate deficiency", "Thalassemia"], {"low": "Check iron/B12/folate; treat cause.", "high": "Assess for macrocytosis causes (B12/folate, liver, alcohol)."}),
            ("mch", "Mean Corpuscular Hemoglobin (MCH)", "pg", "Average amount of hemoglobin per red blood cell.", ["Iron deficiency", "B12/folate deficiency"], {"low": "Check iron/B12/folate; treat cause.", "high": "Assess for macrocytosis causes."}),
            ("mchc", "Mean Corpuscular Hemoglobin Concentration (MCHC)", "g/dL", "Average concentration of hemoglobin in red blood cells.", ["Iron deficiency", "Hereditary spherocytosis"], {"low": "Check iron; treat cause.", "high": "Assess for spherocytosis or lab artifact."}),
            ("rdw", "Red Cell Distribution Width (RDW)", "%", "Variation in size of red blood cells; high values suggest mixed causes of anemia.", ["Iron deficiency", "B12/folate deficiency", "Recent bleeding"], {"high": "Check for mixed anemia causes; iron/B12/folate status."})
        ]:
            key, pretty, unit, importance, causes, advice = missing
            if key not in kb_dict:
                kb_dict[key] = {
                    "test_name": pretty,
                    "canonical_unit": unit,
                    "importance": importance,
                    "causes": causes,
                    "advice": advice
                }
        return kb_dict
    out: Dict[str, Any] = {}
    for k, v in data.items():
        out[str((k or "")).strip().lower()] = v
    return out

def get_entry_with_rag(KB: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    """
    If a key is missing in the static KB, ask the small RAG store for a compatible entry.
    Returns a dict shaped like KB[test_name]: {"unit": "...", "ranges":[...], "advice": {...}} or None.
    """
    name = (key or "").strip().lower()
    if not name:
        return None

    # already present?
    if name in KB:
        return KB[name]

    # query rag store
    store = get_rag_store()
    docs = store.query(name, top_k=1)
    if not docs:
        return None

    d = docs[0]
    # adapt to KB schema
    entry: Dict[str, Any] = {
        "unit": d.unit,
        "ranges": d.ranges,
    }
    # optional: pass through advice if you’ve stored it in notes (not required)
    return entry
