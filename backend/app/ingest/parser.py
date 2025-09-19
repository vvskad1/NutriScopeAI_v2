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
    NON_RESULT_KEYWORDS = [
        "interpretation", "homeostasis", "the formation of", "used in diagnosis", "please correlate clinically",
        "test performed by", "method", "reference", "consultant", "specimen", "investigation", "reporting date", "sample collection", "patient name", "patient id", "op id", "lab id", "age/gender", "clinical biochemistry", "haematology", "lipid profile", "renal function test", "thyroid profile", "liver function test", "differential leukocyte count", "notes --", "end of report", "address:"
    ]
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i].strip()
        if not line or len(line) < 3:
            i += 1
            continue
        line_lc = line.lower()
        if any(kw in line_lc for kw in NON_RESULT_KEYWORDS):
            i += 1
            continue
        # Special handling for Vitamin D3 result lines
        if re.search(r"vitamin[\s\-]*d3?", line, re.I):
            vd_match = re.search(r'(vitamin[\s\-]*d3?)[^\d]*(\d+\.?\d*)\s*(ng/ml|ng/mL|nmol/L)', line, re.I)
            if vd_match:
                value = float(vd_match.group(2))
                unit = vd_match.group(3)
                rows.append({"test": "Vitamin D3", "value": value, "unit": unit})
                i += 1
                continue
        if re.match(r"^(Sufficient|Deficient|Insufficient|Normal|Low|High)[\s\d\-]+$", line, re.I):
            i += 1
            continue
        flag_match = re.search(r"\b(Low|High|Normal)\b", line, re.I)
        explicit_flag = flag_match.group(1).capitalize() if flag_match else None
        # Try to match low-high range
        range_match = re.search(r"([\d.]+)\s*[-–]\s*([\d.]+)\s*([a-zA-Z/%]+)?", line)
        # Try to match single-sided range (e.g., <0.2 mg/dL, >60 mg/dL)
        single_sided_match = re.search(r"([<>≤≥])\s*([\d.]+)\s*([a-zA-Z/%]+)?", line)
        # Try to match banded/label ranges (e.g., Desirable Level : <200 mg/dL)
        banded_match = re.search(r"(Desirable|Borderline|Undesirable|High|Low|Optimal|Sufficient|Insufficient|Deficient)\s*Level\s*:?\s*([<>≤≥]?)\s*([\d.]+)\s*-?\s*([\d.]*)\s*([a-zA-Z/%]+)?", line, re.I)
        low, high, ref_unit = None, None, None
        bands = []
        if range_match:
            try:
                low = float(range_match.group(1))
                high = float(range_match.group(2))
                ref_unit = _clean_unit(range_match.group(3) or "")
            except Exception:
                pass
        m = RE_ROW.match(line)
        if m:
            d = m.groupdict()
            nm = d.get("name") or ""
            val = d.get("value")
            u = _clean_unit(d.get("unit") or "")
            nm_stripped = nm.strip()
            if (
                not nm_stripped
                or re.match(r"^[\d\s\-:.]+$", nm_stripped)
                or re.match(r"^[\d.]+\s*[-:]+", nm_stripped)
                or not re.match(r"^[A-Za-z]", nm_stripped)
            ):
                i += 1
                continue
            try:
                value = float(val) if val is not None else None
            except Exception:
                value = None
            test_lc = nm_stripped.lower()
            if not u and ("vitamin d" in test_lc or "25-oh" in test_lc) and value is not None:
                if 5 <= value <= 150:
                    u = "ng/mL"
                elif 12 <= value <= 375:
                    u = "nmol/L"
            row = {"test": nm_stripped, "value": value, "unit": u}
            # If there is extra text after the value/unit, check for a band/label on the same line
            after_val = line[m.end():].strip() if m.end() < len(line) else ""
            bands = []
            if after_val:
                banded_inline = re.search(r"(Desirable|Borderline|Undesirable|High|Low|Optimal|Sufficient|Insufficient|Deficient)\s*Level\s*:?\s*([<>≤≥]?)\s*([\d.]+)\s*-?\s*([\d.]*)\s*([a-zA-Z/%]+)?", after_val, re.I)
                if banded_inline:
                    try:
                        label = banded_inline.group(1).capitalize()
                        op = banded_inline.group(2)
                        minv = banded_inline.group(3)
                        maxv = banded_inline.group(4)
                        bunit = _clean_unit(banded_inline.group(5) or "")
                        band = {"label": label}
                        if minv:
                            band["min"] = float(minv)
                        if maxv:
                            band["max"] = float(maxv)
                        if bunit:
                            band["unit"] = bunit
                        bands.append(band)
                    except Exception:
                        pass
            # Look ahead for a range on the next line if not present on this line
            next_line = raw_lines[i+1].strip() if i+1 < len(raw_lines) else ""
            next_range = re.search(r"([\d.]+)\s*[-–]\s*([\d.]+)\s*([a-zA-Z/%]+)?", next_line)
            next_single = re.search(r"([<>≤≥])\s*([\d.]+)\s*([a-zA-Z/%]+)?", next_line)
            next_banded = re.search(r"(Desirable|Borderline|Undesirable|High|Low|Optimal|Sufficient|Insufficient|Deficient)\s*Level\s*:?\s*([<>≤≥]?)\s*([\d.]+)\s*-?\s*([\d.]*)\s*([a-zA-Z/%]+)?", next_line, re.I)
            if low is not None and high is not None:
                row["low"] = low
                row["high"] = high
                if not u and ref_unit:
                    row["unit"] = ref_unit
            elif single_sided_match:
                try:
                    op = single_sided_match.group(1)
                    val = float(single_sided_match.group(2))
                    sunit = _clean_unit(single_sided_match.group(3) or "")
                    if op in ('<', '≤'):
                        row["low"] = None
                        row["high"] = val
                    elif op in ('>', '≥'):
                        row["low"] = val
                        row["high"] = None
                    if not u and sunit:
                        row["unit"] = sunit
                except Exception:
                    pass
            elif next_range:
                try:
                    row["low"] = float(next_range.group(1))
                    row["high"] = float(next_range.group(2))
                    nunit = _clean_unit(next_range.group(3) or "")
                    if not u and nunit:
                        row["unit"] = nunit
                except Exception:
                    pass
                i += 1
            elif next_single:
                try:
                    op = next_single.group(1)
                    val = float(next_single.group(2))
                    sunit = _clean_unit(next_single.group(3) or "")
                    if op in ('<', '≤'):
                        row["low"] = None
                        row["high"] = val
                    elif op in ('>', '≥'):
                        row["low"] = val
                        row["high"] = None
                    if not u and sunit:
                        row["unit"] = sunit
                except Exception:
                    pass
                i += 1
            # Parse banded/label ranges for S.HDL and similar
            # Collect all consecutive banded/label range lines after the test value line
            j = i+1
            while j < len(raw_lines):
                l2 = raw_lines[j].strip()
                b2 = re.search(r"(Desirable|Borderline|Undesirable|High|Low|Optimal|Sufficient|Insufficient|Deficient)\s*Level\s*:?\s*([<>≤≥]?)\s*([\d.]+)\s*-?\s*([\d.]*)\s*([a-zA-Z/%]+)?", l2, re.I)
                if b2:
                    try:
                        label = b2.group(1).capitalize()
                        op = b2.group(2)
                        minv = b2.group(3)
                        maxv = b2.group(4)
                        bunit = _clean_unit(b2.group(5) or "")
                        band = {"label": label}
                        if minv:
                            band["min"] = float(minv)
                        if maxv:
                            band["max"] = float(maxv)
                        if bunit:
                            band["unit"] = bunit
                        bands.append(band)
                    except Exception:
                        pass
                    j += 1
                else:
                    break
            if bands:
                row["bands"] = bands
                i = j-1
            if explicit_flag:
                row["explicit_flag"] = explicit_flag
            rows.append(row)
            i += 1
            continue
        if re.search(r"vitamin d|25-oh", line, re.I):
            num_match = re.search(r"(\d+\.?\d*)", line)
            if num_match:
                value = float(num_match.group(1))
                u = ""
                if 5 <= value <= 150:
                    u = "ng/mL"
                elif 12 <= value <= 375:
                    u = "nmol/L"
                rows.append({"test": line, "value": value, "unit": u})
        i += 1
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
