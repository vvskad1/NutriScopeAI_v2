from typing import Optional

def classify(value: float, low: Optional[float], high: Optional[float], tol: float = 0.02) -> str:
    """
    Simple threshold classifier with ±2% borderline buffer.
    Returns: normal | borderline_low | low | borderline_high | high
    """
    lo_b = low * (1 - tol) if low is not None else None
    hi_b = high * (1 + tol) if high is not None else None

    if low is not None and value < low:
        return "borderline_low" if (lo_b is not None and value >= lo_b) else "low"
    if high is not None and value > high:
        return "borderline_high" if (hi_b is not None and value <= hi_b) else "high"
    return "normal"

# Plausibility guards to catch OCR glitches; widen them a bit to avoid false rejects
PLAUSIBLE = {
    "sodium (serum)": (120, 170),
    "potassium (serum)": (2.0, 7.0),
    "bicarbonate (co2)": (18, 35),
    # add more as needed
}

def plausible(test_name: str, v: float) -> bool:
    t = (test_name or "").lower()
    if t in PLAUSIBLE:
        lo, hi = PLAUSIBLE[t]
        return lo <= v <= hi
    return True
