# backend/app/ingest/parser.py
from __future__ import annotations
from typing import List, Dict, Any, Tuple, Optional
import io, re
import pdfplumber
from app.ocr.extract import extract_text_from_pdf

# You already had normalize_test_name somewhere; keep it or import from aliases
from app.normalize.aliases import normalize_test_name  # re-point to your alias file

Value = Optional[float]

# regexes for generic "name value unit" (expanded for Vitamin D and more)
RE_ROW = re.compile(
    r"""
    ^\s*
    (?P<name>[A-Za-z0-9 \-/()%.,]+?)       # test name
    [\s:]*                                  # delimiter
    (?P<value>-?\d+(?:\.\d+)?)              # numeric value
    \s*
    (?P<unit>%|mg/dl|g/dl|mmol/l|iu/l|iu/ml|µ?iu/ml|ng/ml|nmol/l|pg/ml|u/l|k/µl|m/µl|/µl|fL|fl|pg|g/l)?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE
)

def _clean_unit(u: str) -> str:
    u = (u or "").strip()
    u = u.replace("µ", "u").replace("μ", "u")
    u = u.replace("FL", "fL").replace("fl", "fL")
    u = u.replace("IU/L", "IU/L")
    return u

def _try_table_rows(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    """Try structured extraction with pdfplumber tables first."""
    out: List[Dict[str, Any]] = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []
                for tb in tables:
                    # heuristic: search rows that look like [name, value, unit, ...]
                    for row in tb:
                        cells = [c.strip() if isinstance(c, str) else "" for c in row if c]
                        if len(cells) < 2: 
                            continue
                        # find first number cell
                        val_idx = None
                        for i, c in enumerate(cells):
                            if re.search(r"-?\d+(\.\d+)?", c or ""):
                                val_idx = i; break
                        if val_idx is None: 
                            continue
                        name = " ".join(cells[:val_idx]).strip()
                        val_cell = cells[val_idx]
                        m = re.search(r"-?\d+(\.\d+)?", val_cell)
                        if not name or not m:
                            continue
                        value = float(m.group(0))
                        # unit might be same cell or next cell
                        unit = ""
                        rest = " ".join(cells[val_idx:]).replace(m.group(0), "").strip()
                        # quick unit probe
                        m2 = re.search(r"(%|mg/dl|g/dl|mmol/l|iu/l|iu/ml|µ?iu/ml|ng/ml|nmol/l|pg/ml|u/l|k/µl|m/µl|/µl|fL|fl|pg|g/l)", rest, re.I)
                        if m2:
                            unit = _clean_unit(m2.group(0))
                        # If unit is missing, try to infer for common tests
                        test_lc = name.strip().lower()
                        if not unit:
                            if test_lc in ("hemoglobin", "haemoglobin", "hb", "hgb", "hemoglobin (hgb)"):
                                unit = "g/dL"
                            elif test_lc in ("red blood cell", "rbc", "red blood cell (rbc)", "red blood cell count"):
                                unit = "million/µL"
                            elif "vitamin d" in test_lc or "25-oh" in test_lc:
                                # Infer Vitamin D units by value range
                                if 5 <= value <= 150:
                                    unit = "ng/mL"
                                elif 12 <= value <= 375:
                                    unit = "nmol/L"
                        out.append({"test": name, "value": value, "unit": unit})
    except Exception:
        pass
    return out

def _try_line_rows(text: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    raw_lines = text.splitlines()
    # DEBUG: print all lines for troubleshooting
    print("[DEBUG] Raw lines from PDF:")
    for l in raw_lines:
        print(f"[DEBUG_LINE] {l}")
    for raw in raw_lines:
        line = raw.strip()
        if not line or len(line) < 3:
            continue
        # Special handling for Vitamin D3 result lines
        if re.search(r"vitamin[\s\-]*d3?", line, re.I):
            vd_match = re.search(r'(vitamin[\s\-]*d3?)[^\d]*(\d+\.?\d*)\s*(ng/ml|ng/mL|nmol/L)', line, re.I)
            if vd_match:
                value = float(vd_match.group(2))
                unit = vd_match.group(3)
                rows.append({"test": "Vitamin D3", "value": value, "unit": unit})
                continue
        # Skip lines that are likely reference/interpretation (e.g., 'Sufficient 30 -')
        if re.match(r"^(Sufficient|Deficient|Insufficient|Normal|Low|High)[\s\d\-]+$", line, re.I):
            continue
        m = RE_ROW.match(line)
        if m:
            d = m.groupdict()
            nm = d.get("name") or ""
            val = d.get("value")
            u = _clean_unit(d.get("unit") or "")
            try:
                value = float(val) if val is not None else None
            except Exception:
                value = None
            # If Vitamin D and unit missing, infer ng/mL if value plausible
            test_lc = nm.strip().lower()
            if not u and ("vitamin d" in test_lc or "25-oh" in test_lc) and value is not None:
                if 5 <= value <= 150:
                    u = "ng/mL"
                elif 12 <= value <= 375:
                    u = "nmol/L"
            rows.append({"test": nm, "value": value, "unit": u})
            continue
        # FLEXIBLE: If line contains 'vitamin d' and a number, extract it even if format is nonstandard
        if re.search(r"vitamin d|25-oh", line, re.I):
            num_match = re.search(r"(\d+\.?\d*)", line)
            if num_match:
                value = float(num_match.group(1))
                u = ""
                # Try to infer unit
                if 5 <= value <= 150:
                    u = "ng/mL"
                elif 12 <= value <= 375:
                    u = "nmol/L"
                rows.append({"test": line, "value": value, "unit": u})
    return rows

def parse_pdf_bytes(pdf_bytes: bytes) -> Tuple[List[Dict[str, Any]], float]:
    """
    Returns (rows, ocr_confidence)
    rows: [{"test": name, "value": float, "unit": str}]
    """
    # 1) structured tables
    rows = _try_table_rows(pdf_bytes)
    if rows:
        return rows, 0.97

    # 2) text + regex lines
    text = extract_text_from_pdf(pdf_bytes)
    rows = _try_line_rows(text)
    if rows:
        return rows, 0.92

    # 3) nothing found
    return [], 0.0
