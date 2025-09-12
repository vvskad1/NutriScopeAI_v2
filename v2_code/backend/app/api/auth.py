# app/api/auth.py
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from datetime import datetime, timedelta
import os, json
import jwt  # PyJWT; ensure: pip uninstall jwt && pip install PyJWT

router = APIRouter(prefix="/api/auth", tags=["auth"])

DATA_FILE = os.path.join(os.path.dirname(__file__), "users.json")
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = os.getenv("JWT_SECRET", "devsecret")
JWT_ALG = "HS256"

def _load_users():
    if not os.path.exists(DATA_FILE):
        return {"seq": 1, "users": {}}  # email -> user
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_users(db):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)

def _get_user(email: str):
    db = _load_users()
    return db["users"].get(email.lower())

def _create_user(name: str, email: str, password: str):
    email = email.lower().strip()
    db = _load_users()
    if email in db["users"]:
        raise HTTPException(status_code=409, detail="Email already registered")
    uid = db["seq"]
    db["seq"] += 1
    user = {
        "id": uid,
        "name": name.strip(),
        "email": email,
        "password_hash": pwd.hash(password),
        "created_at": datetime.utcnow().isoformat(),
    }
    db["users"][email] = user
    _save_users(db)
    return user

def _verify_user(email: str, password: str):
    user = _get_user(email)
    if not user:
        return None
    if not pwd.verify(password, user["password_hash"]):
        return None
    return user

def _make_token(user):
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "name": user["name"],
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=12),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

class SignUpBody(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginBody(BaseModel):
    email: EmailStr
    password: str

@router.post("/signup")
def signup(body: SignUpBody):
    user = _create_user(body.name, body.email, body.password)
    # No token on signup (matches your Node frontend)
    return {"id": user["id"], "name": user["name"], "email": user["email"]}

@router.post("/login")
def login(body: LoginBody):
    email = body.email.lower().strip()
    user = _verify_user(email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = _make_token(user)
    return {"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"]}}
