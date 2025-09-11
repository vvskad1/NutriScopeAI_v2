from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import upload



# NEW: load .env at startup
try:
    from dotenv import load_dotenv  # python-dotenv is already in requirements
    load_dotenv()
except Exception:
    pass

from app.api.routes import router
from app.summarize.llm import summarize_results_structured

import os
print(f"[BOOT] GROQ loaded: {bool(os.getenv('GROQ_API_KEY'))}")


app = FastAPI(title="NutriScope v2 API", version="2.0.0")
app.include_router(upload.router)
app.include_router(router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)
from app.api import report_api
app.include_router(report_api.router)

from app.api.auth import router as auth_router
app.include_router(auth_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
