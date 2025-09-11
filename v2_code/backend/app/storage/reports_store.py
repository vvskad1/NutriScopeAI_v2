# app/storage/reports_store.py
from __future__ import annotations
from typing import Dict, Any, List, Optional
from threading import RLock

_store: Dict[str, Dict[str, Any]] = {}
_order: List[str] = []  # append report ids in the order they are added (oldest -> newest)
_lock = RLock()

def add(report: Dict[str, Any]) -> None:
    rid = report.get("id")
    if not rid:
        return
    with _lock:
        _store[rid] = report
        _order.append(rid)

def get(rid: str) -> Optional[Dict[str, Any]]:
    with _lock:
        return _store.get(rid)

def count() -> int:
    with _lock:
        return len(_order)

def list(page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
    """
    Return newest-first page of saved reports.
    """
    with _lock:
        # sanitize inputs
        if not isinstance(page, int) or page < 1:
            page = 1
        if not isinstance(page_size, int) or page_size < 1:
            page_size = 20

        # newest first
        ids_desc: List[str] = list(reversed(_order))
        start = (page - 1) * page_size
        end = start + page_size
        page_ids = ids_desc[start:end]
        return [_store[i] for i in page_ids if i in _store]
