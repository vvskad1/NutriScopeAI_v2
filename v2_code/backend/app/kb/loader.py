# backend/app/kb/loader.py
from __future__ import annotations
from typing import Dict, Any, Optional
import json, os
from app.rag.store import get_rag_store

# Load your static KB (existing file path)
DEFAULT_KB_PATH = os.getenv("KB_PATH", "app/kb/lab_kb.json")

def load_kb() -> Dict[str, Any]:
    if os.path.exists(DEFAULT_KB_PATH):
        try:
            return json.load(open(DEFAULT_KB_PATH, "r", encoding="utf-8"))
        except Exception:
            pass
    return {}

def get_entry_with_rag(kb: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    k = (key or "").strip().lower()
    if k in kb:
        return kb[k]

    # RAG fallback
    store = get_rag_store()
    hits = store.query(k, top_k=2)
    for h in hits:
        # shape into KB-compatible entry
        entry = {
            "unit": h.unit,
            "ranges": h.ranges,   # already in KB format (either low/high or bands)
            "advice": {
                # optional placeholders; you can enrich your docs to include advice too
                "low": None,
                "high": None,
            },
            "_source": h.source,
            "_notes": h.notes,
        }
        # DO NOT auto-mutate saved KB on disk; return ephemeral entry.
        return entry
    return None
