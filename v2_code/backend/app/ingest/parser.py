# backend/app/ingest/parser.py
from __future__ import annotations
from typing import List, Dict, Any, Tuple, Optional
import io, re
import pdfplumber
from app.ocr.extract import extract_text_from_pdf

# You already had normalize_test_name somewhere; keep it or import from aliases
from app.normalize.aliases import normalize_test_name  # re-point to your alias file

Value = Optional[float]

# regexes for generic "name value unit"
RE_ROW = re.compile(
    r"""
    ^\s*
    (?P<name>[A-Za-z0-9 \-/()%.,]+?)       # test name
    [\s:]*                                  # delimiter
    (?P<value>-?\d+(?:\.\d+)?)              # numeric value
    \s*
    (?P<unit>%|mg/dl|g/dl|mmol/l|iu/l|µ?iu/ml|ng/ml|pg/ml|u/l|k/µl|m/µl|/µl|fL|fl|pg|g/l)?
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
                        m2 = re.search(r"(%|mg/dl|g/dl|mmol/l|iu/l|µ?iu/ml|ng/ml|pg/ml|u/l|k/µl|m/µl|/µl|fL|fl|pg|g/l)", rest, re.I)
                        if m2:
                            unit = _clean_unit(m2.group(0))
                        out.append({"test": name, "value": value, "unit": unit})
    except Exception:
        pass
    return out

def _try_line_rows(text: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or len(line) < 3: 
            continue
        m = RE_ROW.match(line)
        if not m:
            continue
        d = m.groupdict()
        nm = d.get("name") or ""
        val = d.get("value")
        u = _clean_unit(d.get("unit") or "")
        try:
            value = float(val) if val is not None else None
        except Exception:
            value = None
        rows.append({"test": nm, "value": value, "unit": u})
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
