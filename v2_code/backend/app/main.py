from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import upload




# NEW: load .env at startup (explicit path)
try:
    from dotenv import load_dotenv  # python-dotenv is already in requirements
    import os
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    print(f"[ENV DEBUG] Attempting to load .env from: {env_path}")
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            print("[ENV DEBUG] .env contents:\n" + f.read())
    else:
        print("[ENV DEBUG] .env file not found at:", env_path)
    load_dotenv(env_path)
    print("[ENV DEBUG] GROQ_API_KEY =", os.getenv("GROQ_API_KEY"))
except Exception as e:
    print(f"[ENV] Could not load .env: {e}")

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
