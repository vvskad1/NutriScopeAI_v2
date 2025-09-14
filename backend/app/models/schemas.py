# app/models/schemas.py
from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel

Sex = Literal["male", "female"]

class AnalyzeRequest(BaseModel):
    report_name: str
    age: int
    sex: Sex

class AppliedRange(BaseModel):
    low: Optional[float] = None
    high: Optional[float] = None
    source: Literal["LAB", "KB", "NONE"]
    note: Optional[str] = None

class ResultRow(BaseModel):
    test: str
    value: Optional[float] = None
    unit: Optional[str] = None
    applied_range: AppliedRange
    status: Literal["normal","borderline_low","low","borderline_high","high","missing","needs_review"]
    source: Literal["parsed","manual"] = "parsed"

class AnalyzeMeta(BaseModel):
    ocr_confidence: float
    analyzer_version: str
    groq_used: Optional[bool] = None  # ✅ carries the Groq usage flag

class AnalyzeResponse(BaseModel):
    context: Dict[str, Any]
    results: List[ResultRow]
    diet_plan: Optional[Dict[str, List[str]]] = None
    summary_text: Optional[str] = None
    disclaimer: str
    issues: Optional[List[str]] = None
    status: Literal["analyzed","needs_review"]
    meta: AnalyzeMeta   # ✅ ensures `groq_used` is preserved

class ReportMeta(BaseModel):
    id: str
    report_name: str
    age: int
    sex: Sex
    uploaded_at: str
    status: Literal["pending","analyzed","needs_review"]
    summary_snippet: Optional[str] = None

class ManualValue(BaseModel):
    test: str
    value: float
    unit: str

class ManualValuesPayload(BaseModel):
    rows: List[ManualValue]
