import os
from functools import lru_cache
from typing import Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from app.services.llm_service import LLMService

load_dotenv()

# Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Never expose
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY or not SUPABASE_ANON_KEY:
    raise RuntimeError("Missing Supabase env vars. Check your .env file.")

app = FastAPI(title="Auth API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class RegisterResponse(BaseModel):
    user_id: str
    email: str
    message: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    email: str
    name: str | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    system_prompt: str = (
        "You are a supportive mental health research assistant. "
        "You are not a doctor, and you avoid diagnosis."
    )
    conversation_history: list[ChatMessage] = Field(default_factory=list)
    user_message: str


class ChatResponse(BaseModel):
    reply: str


class ChatPersistRequest(BaseModel):
    user_id: str
    mode: Literal["general", "anxiety", "depression"]
    role: Literal["user", "assistant"]
    content: str
    conversation_id: str | None = None


class ChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: str | None = None


class ChatHistoryResponse(BaseModel):
    messages: list[ChatHistoryItem]


class ChatConversationItem(BaseModel):
    conversation_id: str
    title: str
    updated_at: str


class ChatConversationsResponse(BaseModel):
    conversations: list[ChatConversationItem]


def _safe_json(response: httpx.Response) -> dict:
    try:
        data = response.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


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


@lru_cache(maxsize=1)
def _get_llm_service() -> LLMService:
    return LLMService()


def _supabase_service_headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }


def _raise_supabase_http_error(action: str, response: httpx.Response):
    body = response.text[:500]
    # Keep a server-side trace for fast terminal debugging.
    print(f"[Supabase:{action}] status={response.status_code} body={body}")
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Supabase {action} failed ({response.status_code}): {body}",
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    url = f"{SUPABASE_URL}/auth/v1/admin/users"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "email": body.email,
        "password": body.password,
        "email_confirm": True,
        "user_metadata": {"name": body.name or ""},
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, headers=headers, json=payload, timeout=10.0)
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Cannot reach Supabase. Check SUPABASE_URL in backend/.env "
                "(expected format: https://<project-ref>.supabase.co)."
            ),
        )

    if res.status_code == 422:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid email or weak password (min 6 characters).",
        )

    if res.status_code == 400:
        data = _safe_json(res)
        if _is_duplicate_email(data):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is already registered. Try logging in instead.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=data.get("msg") or data.get("message") or "Bad request.",
        )

    if res.status_code not in (200, 201):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase error: {res.text}",
        )

    user = _safe_json(res)
    return RegisterResponse(
        user_id=user["id"],
        email=user["email"],
        message="Registration successful. You can now log in.",
    )


@app.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    token_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    token_headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }
    token_payload = {
        "email": body.email,
        "password": body.password,
    }

    try:
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                token_url, headers=token_headers, json=token_payload, timeout=10.0
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Cannot reach Supabase. Check SUPABASE_URL in backend/.env "
                "(expected format: https://<project-ref>.supabase.co)."
            ),
        )

    if token_res.status_code == 400:
        data = _safe_json(token_res)
        msg = data.get("error_description") or data.get("msg") or "Invalid email or password."
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)

    if token_res.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase error: {token_res.text}",
        )

    token_data = token_res.json()
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    user = token_data["user"]
    user_id = user["id"]

    profile_url = f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}&select=name"
    profile_headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {access_token}",
    }

    try:
        async with httpx.AsyncClient() as client:
            profile_res = await client.get(profile_url, headers=profile_headers, timeout=10.0)
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Logged in, but failed to fetch profile from Supabase REST API. "
                "Verify SUPABASE_URL and network access."
            ),
        )

    name = None
    if profile_res.status_code == 200:
        rows = profile_res.json()
        if rows:
            name = rows[0].get("name")

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user_id,
        email=user["email"],
        name=name,
    )


@app.post("/chat/respond", response_model=ChatResponse)
async def chat_respond(body: ChatRequest):
    try:
        llm = _get_llm_service()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    history = [{"role": msg.role, "content": msg.content} for msg in body.conversation_history]
    reply = llm.generate_response(
        system_prompt=body.system_prompt,
        conversation_history=history,
        user_message=body.user_message,
    )
    return ChatResponse(reply=reply)


@app.get("/chat/history", response_model=ChatHistoryResponse)
async def chat_history(
    user_id: str,
    mode: Literal["general", "anxiety", "depression"],
    conversation_id: str | None = None,
):
    url = f"{SUPABASE_URL}/rest/v1/chat_messages"
    params = {
        "user_id": f"eq.{user_id}",
        "mode": f"eq.{mode}",
        "select": "role,content,created_at",
        "order": "created_at.asc",
    }
    if conversation_id:
        params["conversation_id"] = f"eq.{conversation_id}"

    headers = _supabase_service_headers()

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=headers, params=params, timeout=10.0)
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to reach Supabase while fetching chat history.",
        )

    if res.status_code != 200:
        _raise_supabase_http_error("fetch_chat_history", res)

    rows = res.json()
    messages: list[ChatHistoryItem] = []
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                messages.append(
                    ChatHistoryItem(
                        role=row.get("role", "assistant"),
                        content=row.get("content", ""),
                        created_at=row.get("created_at"),
                    )
                )
    return ChatHistoryResponse(messages=messages)


@app.post("/chat/messages", status_code=status.HTTP_201_CREATED)
async def chat_messages(body: ChatPersistRequest):
    url = f"{SUPABASE_URL}/rest/v1/chat_messages"
    headers = _supabase_service_headers()
    headers["Prefer"] = "return=minimal"
    payload = {
        "user_id": body.user_id,
        "mode": body.mode,
        "role": body.role,
        "content": body.content,
        "conversation_id": body.conversation_id or "default",
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, headers=headers, json=payload, timeout=10.0)
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to reach Supabase while saving chat message.",
        )

    if res.status_code not in (200, 201):
        _raise_supabase_http_error("save_chat_message", res)

    return {"message": "saved"}


@app.delete("/chat/history")
async def delete_chat_history(
    user_id: str,
    mode: Literal["general", "anxiety", "depression"],
    conversation_id: str | None = None,
):
    url = f"{SUPABASE_URL}/rest/v1/chat_messages"
    params = {
        "user_id": f"eq.{user_id}",
        "mode": f"eq.{mode}",
    }
    if conversation_id:
        params["conversation_id"] = f"eq.{conversation_id}"

    headers = _supabase_service_headers()
    headers["Prefer"] = "return=minimal"

    try:
        async with httpx.AsyncClient() as client:
            res = await client.delete(url, headers=headers, params=params, timeout=10.0)
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to reach Supabase while deleting chat history.",
        )

    if res.status_code not in (200, 204):
        _raise_supabase_http_error("delete_chat_history", res)

    return {"message": "deleted"}


@app.get("/chat/conversations", response_model=ChatConversationsResponse)
async def chat_conversations(user_id: str, mode: Literal["general", "anxiety", "depression"]):
    url = f"{SUPABASE_URL}/rest/v1/chat_messages"
    params = {
        "user_id": f"eq.{user_id}",
        "mode": f"eq.{mode}",
        "select": "conversation_id,role,content,created_at",
        "order": "created_at.desc",
        "limit": "1000",
    }
    headers = _supabase_service_headers()

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=headers, params=params, timeout=10.0)
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to reach Supabase while loading conversation list.",
        )

    if res.status_code != 200:
        _raise_supabase_http_error("load_conversations", res)

    rows = res.json()
    if not isinstance(rows, list):
        return ChatConversationsResponse(conversations=[])

    by_conversation: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        convo_id = row.get("conversation_id") or "default"
        content = str(row.get("content") or "").strip()
        row_role = row.get("role") or ""
        row_created = row.get("created_at") or ""
        existing = by_conversation.get(convo_id)
        if not existing:
            by_conversation[convo_id] = {
                "updated_at": row_created,
                "latest_content": content,
                "latest_user_content": content if row_role == "user" else "",
            }
            continue

        if not existing.get("latest_user_content") and row_role == "user" and content:
            existing["latest_user_content"] = content

    items: list[ChatConversationItem] = []
    for convo_id, agg in by_conversation.items():
        title_source = agg.get("latest_user_content") or agg.get("latest_content") or "New chat"
        title = title_source[:48] + "..." if len(title_source) > 48 else title_source
        items.append(
            ChatConversationItem(
                conversation_id=convo_id,
                title=title,
                updated_at=agg.get("updated_at") or "",
            )
        )

    items.sort(key=lambda item: item.updated_at, reverse=True)
    return ChatConversationsResponse(conversations=items)
