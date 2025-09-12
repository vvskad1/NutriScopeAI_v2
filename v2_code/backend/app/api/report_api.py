# app/api/report_api.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.storage import reports_store as store

router = APIRouter(prefix="/api", tags=["reports"])

@router.get("/report/{rid}")
def get_report(rid: str):
    rep = store.get(rid)
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found")
    return rep

@router.get("/reports")
def list_reports(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    total, items = store.list_paginated(page, page_size)
    # return a simple list or a dict with items; your NiceGUI can handle either
    return {"total": total, "items": [
        {
            "id": item.get("id") or item.get("context", {}).get("report_id"),
            "filename": item.get("filename") or item.get("context", {}).get("report_name") or "report.pdf",
            "status": item.get("status") or "done",
        } for item in items
    ]}

@router.delete("/report/{rid}")
def delete_report(rid: str):
    ok = store.delete(rid)
    if not ok:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"deleted": True, "id": rid}
