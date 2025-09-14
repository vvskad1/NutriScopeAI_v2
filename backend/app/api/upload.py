# app/api/upload.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

router = APIRouter(tags=["upload"])

@router.post("/upload-report")
async def upload_report(
    file: UploadFile = File(...),
    report_name: str | None = Form(None),
    age: int | None = Form(None),
    sex: str | None = Form(None),
):
    try:
        content = await file.read()
        # TODO: call your PDF parser / analyzer here with `content`
        # For now just return metadata so frontend can test:
        return {
            "report_id": "1234",
            "status": "done",
            "filename": file.filename,
            "size": len(content),
            "report_name": report_name,
            "age": age,
            "sex": sex,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
