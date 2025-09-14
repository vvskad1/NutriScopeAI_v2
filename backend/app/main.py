from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router
from app.api.upload import router as upload_router
# from app.api.report_api import router as report_router  # REMOVE: endpoints moved to routes.py
from app.api.auth import router as auth_router
try:
    from dotenv import load_dotenv
    import os
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(env_path)
except Exception:
    pass

app = FastAPI(title="NutriScope v2 API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)
app.include_router(api_router)
app.include_router(upload_router)
# app.include_router(report_router)  # REMOVE: endpoints moved to routes.py
app.include_router(auth_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
