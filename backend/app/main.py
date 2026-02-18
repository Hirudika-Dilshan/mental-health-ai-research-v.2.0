# backend/app/main.py

import os
import httpx
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

load_dotenv()

# ── Config ──────────────────────────────────────────────────
SUPABASE_URL      = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")   # service_role key
FRONTEND_URL      = os.getenv("FRONTEND_URL", "http://localhost:5173")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env")

# ── App ──────────────────────────────────────────────────────
app = FastAPI(title="Auth API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Schemas ──────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None   # optional

class RegisterResponse(BaseModel):
    user_id: str
    email: str
    message: str

# ── Routes ──────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(body: RegisterRequest):
    """
    Creates a new user in Supabase Auth.
    The Supabase trigger will automatically create a row in public.profiles.
    """
    supabase_auth_url = f"{SUPABASE_URL}/auth/v1/admin/users"

    headers = {
        "apikey":        SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type":  "application/json",
    }

    payload = {
        "email":    body.email,
        "password": body.password,
        "email_confirm": True,   # auto-confirm; set False to require email verification
        "user_metadata": {
            "name": body.name or "",
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            supabase_auth_url,
            headers=headers,
            json=payload,
            timeout=10.0,
        )

    def _is_duplicate_email(payload: dict) -> bool:
        joined = " ".join(
            str(payload.get(k, ""))
            for k in ("code", "msg", "message", "error", "error_description")
        ).lower()
        return (
            "email_exists" in joined
            or ("already" in joined and "register" in joined)
            or ("already" in joined and "exist" in joined)
            or ("already" in joined and "use" in joined)
        )

    # ── Error handling ───────────────────────────────────────
    if response.status_code == 422:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid email or weak password (min 6 characters).",
        )

    if response.status_code == 400:
        data = response.json()
        if _is_duplicate_email(data):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is already registered. Try logging in instead.",
            )
        msg  = data.get("msg") or data.get("message") or "Bad request."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase error: {response.text}",
        )

    user = response.json()

    return RegisterResponse(
        user_id=user["id"],
        email=user["email"],
        message="Registration successful. You can now log in.",
    )
