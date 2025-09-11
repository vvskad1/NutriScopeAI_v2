# backend/app/ocr/extract.py
from __future__ import annotations
from typing import List
import io, os
from PIL import Image
import pdfplumber

# Optional OCR engines
USE_EASYOCR = os.getenv("OCR_ENGINE", "eas y ocr").lower().startswith("easy")
USE_TESS = os.getenv("OCR_ENGINE", "easyocr").lower().startswith("tess")

_easyocr_reader = None
if USE_EASYOCR:
    try:
        import easyocr  # type: ignore
        _easyocr_reader = easyocr.Reader(["en"], gpu=False)
    except Exception:
        _easyocr_reader = None

if USE_TESS:
    try:
        import pytesseract  # type: ignore
    except Exception:
        pytesseract = None  # type: ignore

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """1) try pdf text  2) fallback OCR per page (Fast + Good)."""
    # (1) pdf text
    text_chunks: List[str] = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for p in pdf.pages:
                t = p.extract_text() or ""
                if t.strip():
                    text_chunks.append(t)
    except Exception:
        pass

    base_text = "\n".join(text_chunks).strip()
    if len(base_text) > 50:
        return base_text

    # (2) OCR images per page
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            ocr_chunks: List[str] = []
            for p in pdf.pages:
                im = p.to_image(resolution=300).original
                if USE_EASYOCR and _easyocr_reader:
                    res = _easyocr_reader.readtext(im, detail=0, paragraph=True)
                    ocr_chunks.append("\n".join(res))
                elif USE_TESS and pytesseract:
                    txt = pytesseract.image_to_string(Image.fromarray(im))
                    ocr_chunks.append(txt)
                else:
                    # as last resort, try pdf text again at high res (already tried)
                    pass
        return "\n".join(ocr_chunks).strip()
    except Exception:
        return base_text or ""
