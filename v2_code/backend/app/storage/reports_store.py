from __future__ import annotations
# app/storage/reports_store.py

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
from typing import Dict, Any, List
from threading import RLock

_store: Dict[str, Dict[str, Any]] = {}
_order: List[str] = []
_lock = RLock()

def add(doc: Dict[str, Any]) -> None:
    rid = doc.get("id") or doc.get("report_id")
    if not rid:
        return
    with _lock:
        _store[rid] = doc
        if rid in _order:
            _order.remove(rid)
        _order.append(rid)

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
