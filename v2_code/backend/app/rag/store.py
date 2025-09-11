# backend/app/rag/store.py
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
import os, json
from dataclasses import dataclass, asdict

# Optional: Chroma or FAISS; we’ll gracefully degrade to a simple keyword search
try:
    import chromadb  # type: ignore
    from chromadb.config import Settings  # type: ignore
    CHROMA_OK = True
except Exception:
    CHROMA_OK = False

@dataclass
class RangeDoc:
    id: str
    test_name: str           # canonical or common name e.g. "hematocrit"
    unit: Optional[str]      # e.g. "%", "mg/dL"
    ranges: List[Dict[str, Any]]  # either [{"low":..,"high":..,"applies":{...}}] or [{"bands":[...]}]
    source: str              # citation or file name
    notes: Optional[str] = None
    synonyms: Optional[List[str]] = None

class RagStore:
    """
    A tiny vector-backed (if available) or keyword-backed store of reference ranges.
    Each doc carries a normalized test_name, unit, ranges schema compatible with your KB.
    """

    def __init__(self, persist_dir: str = ".rag_data"):
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)
        self._docs: Dict[str, RangeDoc] = {}  # id -> doc

        # lightweight persistence for docs
        self._json_path = os.path.join(self.persist_dir, "docs.json")
        if os.path.exists(self._json_path):
            try:
                data = json.load(open(self._json_path, "r", encoding="utf-8"))
                for d in data:
                    self._docs[d["id"]] = RangeDoc(**d)
            except Exception:
                pass

        # Optional vector DB
        self._client = None
        self._col = None
        if CHROMA_OK:
            try:
                self._client = chromadb.Client(Settings(
                    is_persistent=True,
                    persist_directory=self.persist_dir,
                ))
                self._col = self._client.get_or_create_collection("lab_ranges")
                # sync vector store from json if empty
                if not self._col.count():
                    self._bulk_index()
            except Exception:
                self._client = None
                self._col = None

    def _bulk_index(self):
        if not self._col: return
        if not self._docs: return
        ids = []
        texts = []
        metas = []
        for d in self._docs.values():
            ids.append(d.id)
            txt = d.test_name
            if d.synonyms:
                txt += " | " + " | ".join(d.synonyms)
            texts.append(txt)
            metas.append({"test_name": d.test_name})
        self._col.add(ids=ids, documents=texts, metadatas=metas)

    def _save_json(self):
        try:
            json.dump([asdict(x) for x in self._docs.values()], open(self._json_path, "w", encoding="utf-8"), indent=2)
        except Exception:
            pass

    def add_docs(self, docs: List[RangeDoc]):
        for d in docs:
            self._docs[d.id] = d
        self._save_json()
        if self._col:
            self._bulk_index()

    def query(self, test_name: str, top_k: int = 3) -> List[RangeDoc]:
        """Return likely matching docs for test_name."""
        name = (test_name or "").strip().lower()
        out: List[RangeDoc] = []

        if self._col:
            try:
                res = self._col.query(query_texts=[name], n_results=top_k)
                ids = res.get("ids", [[]])[0]
                for _id in ids:
                    if _id in self._docs:
                        out.append(self._docs[_id])
                if out:
                    return out
            except Exception:
                pass

        # fallback: keyword contains on synonyms/test_name
        for d in self._docs.values():
            if name == d.test_name.lower():
                out.append(d); continue
            if any(name == s.lower() for s in (d.synonyms or [])):
                out.append(d); continue
            if name in d.test_name.lower():
                out.append(d); continue
        return out[:top_k]


# convenient singleton
_rag_store: Optional[RagStore] = None

def get_rag_store() -> RagStore:
    global _rag_store
    if _rag_store is None:
        _rag_store = RagStore(persist_dir=os.getenv("RAG_DIR", ".rag_data"))
    return _rag_store
