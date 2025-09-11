# backend/app/normalize/unit_normalization.py
from __future__ import annotations
from typing import Tuple, Optional

def normalize_units_for_test(test_key: str, value, unit: str) -> Tuple[Optional[float], str]:
    """
    Normalize (value, unit) to what your KB expects (often % for HCT,
    g/dL for Hgb, /uL for counts, mg/dL for many chems).
    We only convert when it’s unambiguous.
    """
    if value is None:
        return None, unit
    t = (test_key or "").strip().lower()
    u = (unit or "").strip().lower().replace("µ", "u").replace("μ", "u")

    # ---- CBC counts → /uL ---------------------------------
    if t in {"platelet count","platelets","plt","white blood cell (wbc)","wbc","white blood cell",
             "red blood cell (rbc)","rbc","red blood cell",
             "absolute neutrophils","neutrophil, absolute",
             "absolute lymphocytes","lymphocyte, absolute",
             "absolute monocytes","monocyte, absolute",
             "absolute eosinophils","eosinophil, absolute",
             "absolute basophils","basophil, absolute"}:
        if u in {"k/ul","x10^3/ul","10^3/ul"}:
            return float(value) * 1_000.0, "/uL"
        if u in {"m/ul","x10^6/ul","10^6/ul"}:
            return float(value) * 1_000_000.0, "/uL"
        if u in {"/ul","per ul"}:
            return float(value), "/uL"
        # sometimes no unit but number like 180 or 6.9 -> assume K/uL for WBC/PLT; keep as-is to let range decide
        return float(value), u or ""

    # ---- CBC indices: keep native units -------------------
    if t in {"hematocrit","hematocrit (hct)","hct","red cell dist width (rdw)","rdw"}:
        return float(value), "%"
    if t in {"mean cell volume (mcv)","mcv"}:
        return float(value), "fL"
    if t in {"mean cell hemoglobin (mch)","mch"}:
        return float(value), "pg"
    if t in {"mean cell hb conc (mchc)","mchc"}:
        return float(value), "g/dL"
    if t in {"hemoglobin","hemoglobin (hb/hgb)","hb","hgb"}:
        return float(value), "g/dL"

    # ---- Common chem conversions (extend as needed) -------
    # Glucose: mg/dL <-> mmol/L (divide by 18)
    if t in {"glucose","fasting glucose","plasma glucose"}:
        if u == "mmol/l":
            return float(value) * 18.0, "mg/dL"
        return float(value), "mg/dL"

    # Cholesterol & triglycerides: mg/dL <-> mmol/L
    if t in {"total cholesterol","hdl","ldl","triglycerides","non-hdl cholesterol"}:
        if u == "mmol/l":
            factor = 38.67 if t != "triglycerides" else 88.57
            return float(value) * factor, "mg/dL"
        return float(value), "mg/dL"

    # Creatinine: mg/dL <-> µmol/L (×88.4)
    if t in {"creatinine","serum creatinine"}:
        if u in {"umol/l","µmol/l"}:
            return float(value) / 88.4, "mg/dL"
        return float(value), "mg/dL"

    # Vitamin D (25-OH): ng/mL <-> nmol/L (×2.5)
    if t in {"vitamin d (25-oh)","vitamin d","25-oh vitamin d"}:
        if u == "nmol/l":
            return float(value) / 2.5, "ng/mL"
        return float(value), "ng/mL"

    # TSH: µIU/mL and mIU/L are numerically equal
    if t in {"tsh"}:
        if u in {"miu/l"}:
            return float(value), "µIU/mL"
        return float(value), "µIU/mL"

    # Default: do nothing
    return float(value), unit or ""
