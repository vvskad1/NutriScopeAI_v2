# app/normalize/normalized_values.py
from __future__ import annotations
from typing import Dict, Tuple, Optional

# ---- Synonyms --------------------------------------------------------------
UNIT_SYNONYMS: Dict[str, str] = {
    # Volume
    "µl": "/uL", "μl": "/uL", "ul": "/uL", "/ul": "/uL", "per ul": "/uL", "microliter": "/uL", "microlitre": "/uL",
    # Count
    "k/µl": "K/uL", "k/μl": "K/uL", "k/ul": "K/uL", "x10^3/µl": "K/uL", "10^3/µl": "K/uL", "x10^3/ul": "K/uL", "10^3/ul": "K/uL",
    "m/µl": "M/uL", "m/μl": "M/uL", "m/ul": "M/uL", "x10^6/µl": "M/uL", "10^6/µl": "M/uL", "x10^6/ul": "M/uL", "10^6/ul": "M/uL",
    # Mass/volume
    "fl": "fL", "femtoliter": "fL", "pg": "pg", "picogram": "pg", "g/dl": "g/dL", "mg/dl": "mg/dL", "g/l": "g/L", "mg/l": "mg/L",
    # Concentration
    "mmol/l": "mmol/L", "mmol/litre": "mmol/L", "µiu/ml": "uIU/mL", "μiu/ml": "uIU/mL", "iu/l": "IU/L", "iu": "IU", "u/l": "U/L",
    "ng/ml": "ng/mL", "nmol/l": "nmol/L", "µg/l": "ug/L", "μg/l": "ug/L", "ug/l": "ug/L", "mcg/l": "ug/L", "mcg/ml": "ug/mL",
    "ng/dl": "ng/dL", "pg/ml": "pg/mL", "pg/dl": "pg/dL", "ng/ul": "ng/uL",
    # Percent
    "%": "%",
    # Misc
    "iu/l": "IU/L", "u/l": "U/L", "u": "U", "iu": "IU",
}

def is_recognized_unit(u: str | None) -> bool:
    if not u:
        return False
    u = u.strip().lower()
    # Accept million/µl and variants
    if u in {"million/µl", "million/ul", "10^6/ul", "10^6/µl", "x10^6/ul", "x10^6/µl"}:
        return True
    return u in UNIT_SYNONYMS or u in set(UNIT_SYNONYMS.values())

def canonical_unit(u: str | None) -> str:
    if not u:
        return ""
    u = u.strip().lower()
    return UNIT_SYNONYMS.get(u, u)

# ---- Common per-test families ---------------------------------------------
CBC_COUNT_KEYS = {
    "platelet count", "platelets", "plt",
    "white blood cell (wbc)", "wbc", "white blood cell",
    "red blood cell (rbc)", "rbc", "red blood cell",
    "absolute neutrophils", "neutrophil, absolute",
    "absolute lymphocytes", "lymphocyte, absolute",
    "absolute monocytes", "monocyte, absolute",
    "absolute eosinophils", "eosinophil, absolute",
    "absolute basophils", "basophil, absolute",
}

# ---- Generic conversion factors (from_unit -> to_unit) ---------------------
# Factors are “value_in_to_unit = value_in_from_unit * factor”
GENERIC_FACTORS: Dict[Tuple[str, str], float] = {
    # Vitamin D: ng/mL -> nmol/L
    ("ng/mL", "nmol/L"): 2.5,
    ("nmol/L", "ng/mL"): 1/2.5,

    # Glucose: mg/dL <-> mmol/L
    ("mg/dL", "mmol/L"): 1/18.0,
    ("mmol/L", "mg/dL"): 18.0,

    # Cholesterol (total/LDL/HDL): mg/dL <-> mmol/L
    ("mg/dL", "mmol/L_chol"): 1/38.67,
    ("mmol/L_chol", "mg/dL"): 38.67,

    # Triglycerides: mg/dL <-> mmol/L
    ("mg/dL", "mmol/L_tg"): 1/88.57,
    ("mmol/L_tg", "mg/dL"): 88.57,

    # Creatinine: mg/dL -> umol/L
    ("mg/dL", "umol/L_creat"): 88.4,
    ("umol/L_creat", "mg/dL"): 1/88.4,

    # Hemoglobin: g/dL <-> g/L
    ("g/dL", "g/L"): 10.0,
    ("g/L", "g/dL"): 0.1,

    # Ferritin: ng/mL <-> ug/L (1:1)
    ("ng/mL", "ug/L"): 1.0,
    ("ug/L", "ng/mL"): 1.0,
}

def _convert_by_factor(val: float, from_u: str, to_u: str, test_key: str) -> Optional[float]:
    # Special cases where mmol/L meaning depends on analyte family
    if to_u == "mmol/L":
        if "triglycer" in test_key:
            key = (from_u, "mmol/L_tg")
        elif any(k in test_key for k in ["cholesterol", "hdl", "ldl", "vldl"]):
            key = (from_u, "mmol/L_chol")
        else:
            key = (from_u, "mmol/L")  # e.g., glucose
    elif from_u == "mmol/L":
        if "triglycer" in test_key:
            key = ("mmol/L_tg", to_u)
        elif any(k in test_key for k in ["cholesterol", "hdl", "ldl", "vldl"]):
            key = ("mmol/L_chol", to_u)
        else:
            key = ("mmol/L", to_u)
    elif to_u in {"umol/L", "µmol/L"} or from_u in {"umol/L", "µmol/L"}:
        # Creatinine common case
        u_to = "umol/L_creat" if (to_u in {"umol/L", "µmol/L"}) else to_u
        u_from = "umol/L_creat" if (from_u in {"umol/L", "µmol/L"}) else from_u
        key = (u_from, u_to)
    else:
        key = (from_u, to_u)

    factor = GENERIC_FACTORS.get(key)
    return (val * factor) if factor is not None else None

# ---- Public: normalize value+unit into KB’s target unit --------------------
def normalize_to_kb_unit(
    test_key_lower: str,
    value: Optional[float],
    incoming_unit: str,
    kb_unit: Optional[str],
) -> tuple[Optional[float], str]:
    """
    Returns (value_converted, unit_converted).
    - Uses KB’s target unit when provided.
    - Handles CBC shorthand (K/uL, M/uL) and blank units by inference.
    - Falls back to identity if conversion not known.
    """
    if value is None:
        return None, incoming_unit or ""

    name = (test_key_lower or "").strip().lower()
    u_in = canonical_unit(incoming_unit)
    u_target = canonical_unit(kb_unit) if kb_unit else ""

    # 1) CBC counts: normalize to /uL by default (or to KB unit if defined)
    if name in CBC_COUNT_KEYS:
        # if unit missing but value looks like K/uL or M/uL-ish, infer
        if not u_in:
            if ("white blood cell" in name or name == "wbc") and 0.1 <= value <= 30:
                u_in = "K/uL"
            elif ("red blood cell" in name or name == "rbc") and 0.1 <= value <= 10:
                u_in = "M/uL"
            elif any(k in name for k in ["absolute neut", "absolute lymph", "absolute mono", "absolute eos", "absolute baso"]) and 0.05 <= value <= 30:
                u_in = "K/uL"
            elif "platelet" in name or name == "plt":
                if 10 <= value <= 1000:  # common K/uL style
                    u_in = "K/uL"

        # convert shorthands to /uL, then to target if needed
        # first to /uL
        if u_in == "K/uL":
            value = float(value) * 1_000.0; base_unit = "/uL"
        elif u_in == "M/uL":
            value = float(value) * 1_000_000.0; base_unit = "/uL"
        elif u_in in {"", "/uL"}:
            value = float(value); base_unit = "/uL"
        else:
            # unknown count unit; keep
            base_unit = u_in

        # then if KB declares something else (rare), convert
        if u_target in {"", "/uL"}:
            return value, "/uL"
        if u_target == "K/uL" and base_unit == "/uL":
            return value / 1_000.0, "K/uL"
        if u_target == "M/uL" and base_unit == "/uL":
            return value / 1_000_000.0, "M/uL"
        # fallback
        return value, base_unit

    # 2) If KB has a target unit and it differs, try generic factors
    if u_target and u_in and (u_in != u_target):
        maybe = _convert_by_factor(float(value), u_in, u_target, name)
        if maybe is not None:
            return maybe, u_target

    # 3) Otherwise pass-through (already in desired unit or unknown)
    return float(value), u_in or u_target or ""
