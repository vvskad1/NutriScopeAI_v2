from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

_DB: Dict[str, Dict[str, Any]] = {}  # id -> {meta, results, file_bytes}

def create_report_meta(report_name: str, age: int, sex: str, status: str = "pending") -> str:
    rid = str(uuid.uuid4())
    _DB[rid] = {
        "meta": {
            "id": rid,
            "report_name": report_name,
            "age": age,
            "sex": sex,
            "uploaded_at": datetime.utcnow().isoformat() + "Z",
            "status": status,
            "summary_snippet": None
        },
        "results": [],
        "file": None
    }
    return rid

def save_file(rid: str, file_bytes: bytes) -> None:
    _DB[rid]["file"] = file_bytes

def save_results(rid: str, results: List[Dict[str, Any]], status: str, summary_snippet: Optional[str] = None):
    _DB[rid]["results"] = results
    _DB[rid]["meta"]["status"] = status
    _DB[rid]["meta"]["summary_snippet"] = summary_snippet

def get_reports() -> List[Dict[str, Any]]:
    return [rec["meta"] for rec in _DB.values()]

def get_report(rid: str) -> Optional[Dict[str, Any]]:
    return _DB.get(rid)

def delete_report(rid: str) -> bool:
    return _DB.pop(rid, None) is not None
