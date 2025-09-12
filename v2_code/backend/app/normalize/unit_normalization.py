# app/normalize/unit_normalization.py
from __future__ import annotations
from typing import Optional, Tuple
from .normalized_values import normalize_to_kb_unit

def normalize_units_for_test(
    kb_key_in: str,
    value: Optional[float],
    unit: str,
    kb_unit: Optional[str] = None,
) -> Tuple[Optional[float], str]:
    """
    Thin wrapper used by the API: normalize to the KB’s target unit.
    """
    return normalize_to_kb_unit(kb_key_in, value, unit, kb_unit)
