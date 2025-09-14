from typing import Optional

def normalize_unit(u: str) -> str:
    """Normalize trivial spelling/case differences (ng/ml vs ng/mL, µ -> u, etc.)."""
    if not u:
        return ""
    n = u.strip()
    # unify case for L and U commonly seen in labs
    n = n.replace("µ", "u")           # micro sign
    n = n.replace("Ml", "mL").replace("ml", "mL").replace("l", "L")
    n = n.replace("DL", "dL").replace("dl", "dL")
    n = n.replace("UL", "uL").replace("ul", "uL")
    return n

def convert_to_canonical(test_name: str, value: float, unit: str, canonical_unit: str) -> Optional[float]:
    """
    Convert a measured value to the KB's canonical unit for that test.
    Return None if unknown/unsafe conversion.
    """
    if value is None:
        return None

    u = normalize_unit(unit or "")
    cu = normalize_unit(canonical_unit or "")
    if not u or not cu:
        return None

    # Already canonical
    if u == cu:
        return value

    name = (test_name or "").lower()

    # Glucose: mg/dL <-> mmol/L  (1 mmol/L = 18 mg/dL)
    if "glucose" in name:
        if u == "mg/dL" and cu == "mmol/L":
            return value / 18.0
        if u == "mmol/L" and cu == "mg/dL":
            return value * 18.0

    # Bilirubin: mg/dL <-> µmol/L (1 mg/dL ≈ 17.104 µmol/L)
    if "bilirubin" in name:
        if u in ("umol/L", "µmol/L") and cu == "mg/dL":
            return value / 17.104
        if u == "mg/dL" and cu in ("umol/L", "µmol/L"):
            return value * 17.104

    # Urea: mg/dL <-> mmol/L (1 mmol/L urea ≈ 6.0 mg/dL)
    if "urea" in name:
        if u == "mg/dL" and cu == "mmol/L":
            return value / 6.0
        if u == "mmol/L" and cu == "mg/dL":
            return value * 6.0

    # Uric Acid: mg/dL <-> µmol/L (1 mg/dL ≈ 59.48 µmol/L)
    if "uric acid" in name:
        if u in ("umol/L", "µmol/L") and cu == "mg/dL":
            return value / 59.48
        if u == "mg/dL" and cu in ("umol/L", "µmol/L"):
            return value * 59.48

    # Otherwise: unknown conversion
    return None
