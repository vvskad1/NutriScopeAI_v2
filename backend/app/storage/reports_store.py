
import os, json
from typing import Dict, Any, List
from threading import RLock

_REPORTS_PATH = os.path.join(os.path.dirname(__file__), "reports.json")

def _load_reports():
    if not os.path.exists(_REPORTS_PATH):
        return {}, []
    try:
        with open(_REPORTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("store", {}), data.get("order", [])
    except Exception:
        return {}, []

def _save_reports():
    try:
        with open(_REPORTS_PATH, "w", encoding="utf-8") as f:
            json.dump({"store": _store, "order": _order}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[reports_store] Failed to save reports: {e}")

_store, _order = _load_reports()
_lock = RLock()

def delete(rid: str) -> bool:
    """Delete a report by ID. Returns True if deleted, False if not found."""
    with _lock:
        if rid in _store:
            del _store[rid]
            if rid in _order:
                _order.remove(rid)
            _save_reports()
            return True
        return False

def list_paginated(page: int = 1, page_size: int = 20):
    """
    Returns (total_count, items) for the given page and page_size.
    Items are sorted newest first.
    """
    with _lock:
        total = len(_order)
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        ids_desc = list(reversed(_order))
        start = (page - 1) * page_size
        end = start + page_size
        page_ids = ids_desc[start:end]
        items = [_store[i] for i in page_ids]
        return total, items

def add(doc: Dict[str, Any]) -> None:
    rid = doc.get("id") or doc.get("report_id")
    if not rid:
        return
    with _lock:
        _store[rid] = doc
        if rid in _order:
            _order.remove(rid)
        _order.append(rid)
        _save_reports()

def get(rid: str) -> Dict[str, Any] | None:
    with _lock:
        return _store.get(rid)

def count() -> int:
    with _lock:
        return len(_order)

def list_reports(page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
    with _lock:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        ids_desc = list(reversed(_order))     # newest first using the BUILT-IN list()
        start = (page - 1) * page_size
        end = start + page_size
        page_ids = ids_desc[start:end]
        return [ _store[i] for i in page_ids ]
