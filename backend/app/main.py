import json
import os
from datetime import datetime
from functools import lru_cache
from typing import Dict, Literal, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from app.services.gad7_protocol import GAD7Protocol
from app.services.llm_service import LLMService
from app.services.phq9_protocol import PHQ9Protocol

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY or not SUPABASE_ANON_KEY:
    raise RuntimeError("Missing Supabase env vars. Check your .env file.")

app = FastAPI(title="Mental Health Screening API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


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
    name: Optional[str] = None


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
    conversation_id: Optional[str] = None


class ChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    messages: list[ChatHistoryItem]


class ChatConversationItem(BaseModel):
    conversation_id: str
    title: str
    updated_at: str


class ChatConversationsResponse(BaseModel):
    conversations: list[ChatConversationItem]


class GAD7Request(BaseModel):
    user_id: str
    conversation_id: str = "default"
    user_message: str


class GAD7ResetRequest(BaseModel):
    user_id: str
    conversation_id: str = "default"


class GAD7Response(BaseModel):
    reply: str
    completed: bool = False
    score: Optional[int] = None
    severity: Optional[str] = None
    crisis: bool = False
    withdrawn: bool = False
    delete_partial: bool = False
    no_result: bool = False
    terminal_reason: Optional[str] = None
    state: dict


# ── Internal helpers ───────────────────────────────────────────────────────

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
    print(f"[Supabase:{action}] status={response.status_code} body={body}")
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Supabase {action} failed ({response.status_code}): {body}",
    )


def _shorten(text: str, max_len: int = 60) -> str:
    value = text.strip()
    return value if len(value) <= max_len else f"{value[:max_len].rstrip()}..."


def _build_conversation_title(user_messages: list[str], fallback: str) -> str:
    first_user = next((msg for msg in user_messages if msg.strip()), "")
    return _shorten(first_user or fallback or "New chat")


# ── GAD-7 Session Management (Supabase-backed) ─────────────────────────────
#
# State is persisted to `gad7_sessions` table so it survives server restarts.
# Falls back gracefully to in-memory if the table doesn't exist yet.
#
# Required Supabase table (run once):
#   CREATE TABLE gad7_sessions (
#     id TEXT PRIMARY KEY,           -- "{user_id}:{conversation_id}"
#     user_id TEXT NOT NULL,
#     conversation_id TEXT NOT NULL,
#     protocol_state JSONB,
#     total_score INTEGER,
#     severity_level TEXT,
#     protocol_completed BOOLEAN DEFAULT FALSE,
#     created_at TIMESTAMPTZ DEFAULT NOW(),
#     updated_at TIMESTAMPTZ DEFAULT NOW()
#   );
#
# NOTE: If you prefer pure in-memory (no DB table), keep _memory_sessions only.

_memory_sessions: Dict[str, GAD7Protocol] = {}
_last_gad7_prefix: Dict[str, str] = {}
_memory_phq9_sessions: Dict[str, PHQ9Protocol] = {}
_last_phq9_prefix: Dict[str, str] = {}


async def _load_gad7_session(user_id: str, conversation_id: str) -> GAD7Protocol:
    """Load protocol state from Supabase; fall back to in-memory."""
    key = f"{user_id}:{conversation_id}"

    # Check in-memory cache first (avoids DB round-trip on same request burst)
    if key in _memory_sessions:
        return _memory_sessions[key]

    protocol = GAD7Protocol()

    try:
        url = f"{SUPABASE_URL}/rest/v1/gad7_sessions"
        params = {"id": f"eq.{key}", "select": "protocol_state"}
        async with httpx.AsyncClient() as client:
            res = await client.get(
                url, headers=_supabase_service_headers(), params=params, timeout=5.0
            )
        if res.status_code == 200:
            rows = res.json()
            if rows and isinstance(rows, list) and rows[0].get("protocol_state"):
                protocol.load_state(rows[0]["protocol_state"])
    except Exception as exc:
        # Non-fatal: continue with fresh protocol if DB unavailable
        print(f"[GAD7] state load warning: {exc}")

    _memory_sessions[key] = protocol
    return protocol


async def _save_gad7_session(
    user_id: str,
    conversation_id: str,
    protocol: GAD7Protocol,
    completed: bool = False,
):
    """Persist protocol state to Supabase and update in-memory cache."""
    key = f"{user_id}:{conversation_id}"
    _memory_sessions[key] = protocol

    update_data = {
        "id": key,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "protocol_state": protocol.get_state(),
        "total_score": protocol.total_score,
        "severity_level": protocol.calculate_severity() if protocol.total_score else None,
        "protocol_completed": completed,
        "updated_at": datetime.utcnow().isoformat(),
    }

    try:
        url = f"{SUPABASE_URL}/rest/v1/gad7_sessions"
        headers = _supabase_service_headers()
        headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
        async with httpx.AsyncClient() as client:
            await client.post(url, headers=headers, json=update_data, timeout=5.0)
    except Exception as exc:
        print(f"[GAD7] state save warning: {exc}")


def _reset_gad7_session(user_id: str, conversation_id: str):
    key = f"{user_id}:{conversation_id}"
    _memory_sessions.pop(key, None)
    _last_gad7_prefix.pop(key, None)


async def _delete_gad7_session_row(user_id: str, conversation_id: str):
    key = f"{user_id}:{conversation_id}"
    try:
        url = f"{SUPABASE_URL}/rest/v1/gad7_sessions"
        params = {"id": f"eq.{key}"}
        headers = {**_supabase_service_headers(), "Prefer": "return=minimal"}
        async with httpx.AsyncClient() as client:
            await client.delete(url, headers=headers, params=params, timeout=5.0)
    except Exception as exc:
        print(f"[GAD7] reset DB row warning: {exc}")


async def _load_phq9_session(user_id: str, conversation_id: str) -> PHQ9Protocol:
    key = f"{user_id}:{conversation_id}"
    if key in _memory_phq9_sessions:
        return _memory_phq9_sessions[key]

    protocol = PHQ9Protocol()
    try:
        url = f"{SUPABASE_URL}/rest/v1/phq9_sessions"
        params = {"id": f"eq.{key}", "select": "protocol_state"}
        async with httpx.AsyncClient() as client:
            res = await client.get(
                url, headers=_supabase_service_headers(), params=params, timeout=5.0
            )
        if res.status_code == 200:
            rows = res.json()
            if rows and isinstance(rows, list) and rows[0].get("protocol_state"):
                protocol.load_state(rows[0]["protocol_state"])
    except Exception as exc:
        print(f"[PHQ9] state load warning: {exc}")

    _memory_phq9_sessions[key] = protocol
    return protocol


async def _save_phq9_session(
    user_id: str,
    conversation_id: str,
    protocol: PHQ9Protocol,
    completed: bool = False,
):
    key = f"{user_id}:{conversation_id}"
    _memory_phq9_sessions[key] = protocol

    update_data = {
        "id": key,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "protocol_state": protocol.get_state(),
        "total_score": protocol.total_score,
        "severity_level": protocol.calculate_severity() if protocol.total_score is not None else None,
        "protocol_completed": completed,
        "updated_at": datetime.utcnow().isoformat(),
    }

    try:
        url = f"{SUPABASE_URL}/rest/v1/phq9_sessions"
        headers = _supabase_service_headers()
        headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
        async with httpx.AsyncClient() as client:
            await client.post(url, headers=headers, json=update_data, timeout=5.0)
    except Exception as exc:
        print(f"[PHQ9] state save warning: {exc}")


def _reset_phq9_session(user_id: str, conversation_id: str):
    key = f"{user_id}:{conversation_id}"
    _memory_phq9_sessions.pop(key, None)
    _last_phq9_prefix.pop(key, None)


async def _delete_phq9_session_row(user_id: str, conversation_id: str):
    key = f"{user_id}:{conversation_id}"
    try:
        url = f"{SUPABASE_URL}/rest/v1/phq9_sessions"
        params = {"id": f"eq.{key}"}
        headers = {**_supabase_service_headers(), "Prefer": "return=minimal"}
        async with httpx.AsyncClient() as client:
            await client.delete(url, headers=headers, params=params, timeout=5.0)
    except Exception as exc:
        print(f"[PHQ9] reset DB row warning: {exc}")


def _extract_gad7_question_scores(responses: dict) -> dict:
    scores: Dict[int, Optional[int]] = {}
    for q_num in range(1, 8):
        raw_value = responses.get(q_num)
        if raw_value is None:
            raw_value = responses.get(str(q_num))
        scores[q_num] = raw_value if isinstance(raw_value, int) else None
    return scores


def _build_gad7_assessment_payload(
    user_id: str,
    conversation_id: str,
    protocol: GAD7Protocol,
    terminal_reason: Optional[str],
    completed: bool,
    crisis: bool,
) -> Optional[dict]:
    reason = (terminal_reason or "").strip().lower()

    # Store only finalized outcomes needed for research table.
    if reason == "completed" and completed and not crisis:
        state = protocol.get_state()
        scores = _extract_gad7_question_scores(state.get("responses", {}))
        return {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "status": "completed",
            "q1_score": scores[1],
            "q2_score": scores[2],
            "q3_score": scores[3],
            "q4_score": scores[4],
            "q5_score": scores[5],
            "q6_score": scores[6],
            "q7_score": scores[7],
            "total_score": protocol.total_score,
            "anxiety_level": protocol.calculate_severity(),
            "assessed_at": datetime.utcnow().isoformat(),
        }

    if reason == "crisis" or crisis:
        # Mid-session crisis: keep a record but with empty score fields.
        return {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "status": "crisis_terminated",
            "q1_score": None,
            "q2_score": None,
            "q3_score": None,
            "q4_score": None,
            "q5_score": None,
            "q6_score": None,
            "q7_score": None,
            "total_score": None,
            "anxiety_level": None,
            "assessed_at": datetime.utcnow().isoformat(),
        }

    # Consent fail / withdrawn / excluded => no record.
    return None


async def _insert_gad7_assessment(payload: dict) -> bool:
    try:
        url = f"{SUPABASE_URL}/rest/v1/gad7_assessments"
        headers = {**_supabase_service_headers(), "Prefer": "return=minimal"}
        async with httpx.AsyncClient() as client:
            res = await client.post(url, headers=headers, json=payload, timeout=10.0)
        if res.status_code not in (200, 201):
            print(f"[GAD7] assessment insert warning: status={res.status_code} body={res.text[:400]}")
            return False
        return True
    except Exception as exc:
        print(f"[GAD7] assessment insert warning: {exc}")
        return False


def _extract_phq9_question_scores(responses: dict) -> dict:
    scores: Dict[int, Optional[int]] = {}
    for q_num in range(1, 10):
        raw_value = responses.get(q_num)
        if raw_value is None:
            raw_value = responses.get(str(q_num))
        scores[q_num] = raw_value if isinstance(raw_value, int) else None
    return scores


def _build_phq9_assessment_payload(
    user_id: str,
    conversation_id: str,
    protocol: PHQ9Protocol,
    terminal_reason: Optional[str],
    completed: bool,
    crisis: bool,
) -> Optional[dict]:
    reason = (terminal_reason or "").strip().lower()

    if reason == "completed" and completed and not crisis:
        state = protocol.get_state()
        scores = _extract_phq9_question_scores(state.get("responses", {}))
        return {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "status": "completed",
            "q1_score": scores[1],
            "q2_score": scores[2],
            "q3_score": scores[3],
            "q4_score": scores[4],
            "q5_score": scores[5],
            "q6_score": scores[6],
            "q7_score": scores[7],
            "q8_score": scores[8],
            "q9_score": scores[9],
            "total_score": protocol.total_score,
            "depression_level": protocol.calculate_severity(),
            "assessed_at": datetime.utcnow().isoformat(),
        }

    if reason == "crisis" or crisis:
        return {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "status": "crisis_terminated",
            "q1_score": None,
            "q2_score": None,
            "q3_score": None,
            "q4_score": None,
            "q5_score": None,
            "q6_score": None,
            "q7_score": None,
            "q8_score": None,
            "q9_score": None,
            "total_score": None,
            "depression_level": None,
            "assessed_at": datetime.utcnow().isoformat(),
        }

    return None


async def _insert_phq9_assessment(payload: dict) -> bool:
    try:
        url = f"{SUPABASE_URL}/rest/v1/phq9_assessments"
        headers = {**_supabase_service_headers(), "Prefer": "return=minimal"}
        async with httpx.AsyncClient() as client:
            res = await client.post(url, headers=headers, json=payload, timeout=10.0)
        if res.status_code not in (200, 201):
            print(f"[PHQ9] assessment insert warning: status={res.status_code} body={res.text[:400]}")
            return False
        return True
    except Exception as exc:
        print(f"[PHQ9] assessment insert warning: {exc}")
        return False


def _heuristic_gad7_intent(text: str) -> str:
    value = (text or "").strip().lower()
    if any(k in value for k in ["suicide", "kill myself", "want to die", "self harm", "hurt myself"]):
        return "crisis"
    if any(k in value for k in ["stop", "exit", "quit", "end session"]):
        return "withdraw"
    if value in {"1", "2", "3", "4"}:
        return f"freq_{value}"
    if value in {"yes", "y", "yeah", "yep", "ok", "okay"}:
        return "yes"
    if value in {"no", "n", "nope"}:
        return "no"
    if "skip" in value:
        return "skip"
    if "back" in value:
        return "back"
    if "how many" in value and "question" in value:
        return "meta_count"
    if "why" in value and "ask" in value:
        return "meta_why"
    if "gad" in value:
        return "meta_what"
    if "example" in value:
        return "example"
    if "don't understand" in value or "dont understand" in value or "confused" in value:
        return "confused"
    if "because" in value or "reason" in value:
        return "justification"
    if "can you tell me if" in value or "am i anxious" in value or "how do i know" in value:
        return "assessment"
    return "normal"


def _map_intent_to_protocol_text(intent: str, raw_text: str) -> str:
    mapping = {
        "yes": "yes",
        "no": "no",
        "freq_1": "1",
        "freq_2": "2",
        "freq_3": "3",
        "freq_4": "4",
        "skip": "skip",
        "back": "back",
        "meta_count": "how many questions are left?",
        "meta_why": "why are you asking this?",
        "meta_what": "what is gad-7?",
        "confused": "i don't understand",
        "example": "can you give me examples?",
        "assessment": "can you tell me if i am anxious?",
        "justification": "yes, but it's because of my situation",
        "withdraw": "stop",
        "crisis": "i want to die",
        "off_topic": "what is the weather?",
    }
    return mapping.get(intent, raw_text)


def _is_structured_intent(intent: str) -> bool:
    return intent in {
        "yes",
        "no",
        "freq_1",
        "freq_2",
        "freq_3",
        "freq_4",
        "skip",
        "back",
        "meta_count",
        "meta_why",
        "meta_what",
        "confused",
        "example",
        "assessment",
        "justification",
        "withdraw",
        "crisis",
        "off_topic",
    }


def _classify_gad7_intent_with_ai(user_message: str, protocol_state: dict) -> str:
    # AI-first classification for natural-language variants
    system_prompt = (
        "Classify the user's message into one intent label for a GAD-7 protocol.\n"
        "Allowed labels only:\n"
        "yes, no, freq_1, freq_2, freq_3, freq_4, skip, back, meta_count, meta_why, meta_what, "
        "confused, example, assessment, justification, withdraw, crisis, off_topic, normal.\n"
        "Return JSON only: {\"intent\":\"<label>\"}"
    )
    user_prompt = (
        f"User message: {user_message}\n"
        f"Protocol state: {json.dumps(protocol_state, ensure_ascii=False)}\n"
        "Choose the single best label."
    )
    try:
        llm = _get_llm_service()
        raw = llm.generate_response(
            system_prompt=system_prompt,
            conversation_history=[],
            user_message=user_prompt,
        )
        data = json.loads(raw)
        intent = str(data.get("intent", "")).strip().lower()
        if intent:
            return intent
    except Exception:
        pass

    # Fallback heuristic only if AI parse fails.
    return _heuristic_gad7_intent(user_message)


def _heuristic_phq9_intent(text: str) -> str:
    value = (text or "").strip().lower()
    if any(k in value for k in ["suicide", "kill myself", "want to die", "self harm", "hurt myself"]):
        return "crisis"
    if any(k in value for k in ["stop", "exit", "quit", "end session"]):
        return "withdraw"
    if value in {"1", "2", "3", "4"}:
        return f"freq_{value}"
    if value in {"yes", "y", "yeah", "yep", "ok", "okay"}:
        return "yes"
    if value in {"no", "n", "nope"}:
        return "no"
    if "skip" in value:
        return "skip"
    if "back" in value:
        return "back"
    if "how many" in value and "question" in value:
        return "meta_count"
    if "why" in value and "ask" in value:
        return "meta_why"
    if "phq" in value:
        return "meta_what"
    if "example" in value:
        return "example"
    if (
        "is that about" in value
        or "what do you mean" in value
        or "day or night" in value
        or "not clear" in value
    ):
        return "confused"
    if "don't understand" in value or "dont understand" in value or "confused" in value:
        return "confused"
    if "because" in value or "reason" in value:
        return "justification"
    if "can you tell me if" in value or "am i depressed" in value or "how do i know" in value:
        return "assessment"
    return "normal"


def _map_phq9_intent_to_protocol_text(intent: str, raw_text: str) -> str:
    mapping = {
        "yes": "yes",
        "no": "no",
        "freq_1": "1",
        "freq_2": "2",
        "freq_3": "3",
        "freq_4": "4",
        "skip": "skip",
        "back": "back",
        "meta_count": "how many questions are left?",
        "meta_why": "why are you asking this?",
        "meta_what": "what is phq-9?",
        "confused": "i don't understand",
        "example": "can you give me examples?",
        "assessment": "can you tell me if i am depressed?",
        "justification": "yes, but it's because of my situation",
        "withdraw": "stop",
        "crisis": "i want to die",
        "off_topic": "what is the weather?",
    }
    return mapping.get(intent, raw_text)


def _classify_phq9_intent_with_ai(user_message: str, protocol_state: dict) -> str:
    heuristic = _heuristic_phq9_intent(user_message)
    if heuristic != "normal":
        return heuristic

    system_prompt = (
        "Classify the user's message into one intent label for a PHQ-9 protocol.\n"
        "Allowed labels only:\n"
        "yes, no, freq_1, freq_2, freq_3, freq_4, skip, back, meta_count, meta_why, meta_what, "
        "confused, example, assessment, justification, withdraw, crisis, off_topic, normal.\n"
        "Return JSON only: {\"intent\":\"<label>\"}"
    )
    user_prompt = (
        f"User message: {user_message}\n"
        f"Protocol state: {json.dumps(protocol_state, ensure_ascii=False)}\n"
        "Choose the single best label."
    )
    try:
        llm = _get_llm_service()
        raw = llm.generate_response(
            system_prompt=system_prompt,
            conversation_history=[],
            user_message=user_prompt,
        )
        data = json.loads(raw)
        intent = str(data.get("intent", "")).strip().lower()
        if intent:
            return intent
    except Exception:
        pass
    return _heuristic_phq9_intent(user_message)


# ── LLM conversational wrapper ─────────────────────────────────────────────

def _build_gad7_conversational_reply(
    session_key: str,
    intent: str,
    user_message: str,
    protocol_reply: str,
    completed: bool,
    crisis: bool,
    withdrawn: bool,
) -> str:
    """Optionally prepend a short empathetic LLM prefix.
    Safety-critical protocol messages are never modified."""
    if crisis or withdrawn:
        return protocol_reply

    system_prompt = (
        "CRITICAL RULES:\n"
        "1. You are NOT a therapist or doctor. You are a screening tool.\n"
        "2. NEVER diagnose or give medical advice.\n"
        "3. Follow the exact GAD-7 protocol provided.\n"
        "4. Be conversational but professional.\n"
        "5. If user is confused, provide clarification gently.\n"
        "6. If user goes off-topic, gently guide them back.\n"
        "7. Watch for crisis keywords and respond appropriately.\n\n"
        "YOUR TONE: Warm, supportive, non-judgmental, like a caring healthcare worker.\n\n"
        "Task: Write a short conversational bridge (1-2 sentences) for this turn.\n"
        "Then append the protocol text EXACTLY as given, unchanged.\n"
        "Do not repeat generic phrases in multiple turns."
    )
    user_prompt = (
        f"Detected intent: {intent}\n"
        f"User said: {user_message}\n"
        f"Completed: {completed}\n"
        f"Protocol text to append EXACTLY:\n{protocol_reply}\n\n"
        "Return final assistant message now."
    )

    try:
        llm = _get_llm_service()
        prefix = (
            llm.generate_response(
                system_prompt=system_prompt,
                conversation_history=[],
                user_message=user_prompt,
            )
            or ""
        ).strip()
        if not prefix:
            return protocol_reply
        # Avoid identical full response repeats.
        if _last_gad7_prefix.get(session_key) == prefix:
            return protocol_reply
        _last_gad7_prefix[session_key] = prefix
        return prefix
    except Exception:
        return protocol_reply


def _build_phq9_conversational_reply(
    session_key: str,
    intent: str,
    user_message: str,
    protocol_reply: str,
    completed: bool,
    crisis: bool,
    withdrawn: bool,
) -> str:
    if crisis or withdrawn:
        return protocol_reply

    system_prompt = (
        "CRITICAL RULES:\n"
        "1. You are NOT a therapist or doctor. You are a screening tool.\n"
        "2. NEVER diagnose or give medical advice.\n"
        "3. Follow the exact PHQ-9 protocol provided.\n"
        "4. Be conversational but professional.\n"
        "5. If user is confused, provide clarification gently.\n"
        "6. If user goes off-topic, gently guide them back.\n"
        "7. Watch for crisis keywords and respond appropriately.\n\n"
        "YOUR TONE: Warm, supportive, non-judgmental, like a caring healthcare worker.\n\n"
        "Task: Write a short conversational bridge (1-2 sentences) for this turn.\n"
        "Then append the protocol text EXACTLY as given, unchanged.\n"
        "Do not repeat generic phrases in multiple turns."
    )
    user_prompt = (
        f"Detected intent: {intent}\n"
        f"User said: {user_message}\n"
        f"Completed: {completed}\n"
        f"Protocol text to append EXACTLY:\n{protocol_reply}\n\n"
        "Return final assistant message now."
    )
    try:
        llm = _get_llm_service()
        prefix = (
            llm.generate_response(
                system_prompt=system_prompt,
                conversation_history=[],
                user_message=user_prompt,
            )
            or ""
        ).strip()
        if not prefix:
            return protocol_reply
        if _last_phq9_prefix.get(session_key) == prefix:
            return protocol_reply
        _last_phq9_prefix[session_key] = prefix
        return prefix
    except Exception:
        return protocol_reply


# ── Delete chat rows helper ────────────────────────────────────────────────

async def _delete_chat_history_rows(
    user_id: str,
    mode: Literal["general", "anxiety", "depression"],
    conversation_id: Optional[str] = None,
):
    url = f"{SUPABASE_URL}/rest/v1/chat_messages"
    params = {"user_id": f"eq.{user_id}", "mode": f"eq.{mode}"}
    if conversation_id:
        params["conversation_id"] = f"eq.{conversation_id}"
    headers = {**_supabase_service_headers(), "Prefer": "return=minimal"}
    async with httpx.AsyncClient() as client:
        res = await client.delete(url, headers=headers, params=params, timeout=10.0)
    if res.status_code not in (200, 204):
        _raise_supabase_http_error("delete_chat_history", res)


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Auth ───────────────────────────────────────────────────────────────────

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
            detail="Cannot reach Supabase. Check SUPABASE_URL in .env.",
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
    token_headers = {"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                token_url,
                headers=token_headers,
                json={"email": body.email, "password": body.password},
                timeout=10.0,
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cannot reach Supabase. Check SUPABASE_URL in .env.",
        )

    if token_res.status_code == 400:
        data = _safe_json(token_res)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=data.get("error_description") or "Invalid email or password.",
        )
    if token_res.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase error: {token_res.text}",
        )

    token_data = token_res.json()
    access_token = token_data["access_token"]
    user = token_data["user"]
    user_id = user["id"]

    # Fetch display name from profiles table
    name = None
    try:
        profile_url = f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}&select=name"
        profile_headers = {"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient() as client:
            profile_res = await client.get(profile_url, headers=profile_headers, timeout=10.0)
        if profile_res.status_code == 200:
            rows = profile_res.json()
            if rows:
                name = rows[0].get("name")
    except Exception:
        pass  # Non-fatal; name just stays None

    return LoginResponse(
        access_token=access_token,
        refresh_token=token_data["refresh_token"],
        user_id=user_id,
        email=user["email"],
        name=name,
    )


# ── General chat ───────────────────────────────────────────────────────────

@app.post("/chat/respond", response_model=ChatResponse)
async def chat_respond(body: ChatRequest):
    try:
        llm = _get_llm_service()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    history = [{"role": m.role, "content": m.content} for m in body.conversation_history]
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
    conversation_id: Optional[str] = None,
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

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                url, headers=_supabase_service_headers(), params=params, timeout=10.0
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to reach Supabase while fetching chat history.",
        )

    if res.status_code != 200:
        _raise_supabase_http_error("fetch_chat_history", res)

    rows = res.json()
    messages = [
        ChatHistoryItem(
            role=row.get("role", "assistant"),
            content=row.get("content", ""),
            created_at=row.get("created_at"),
        )
        for row in (rows if isinstance(rows, list) else [])
        if isinstance(row, dict)
    ]
    return ChatHistoryResponse(messages=messages)


@app.post("/chat/messages", status_code=status.HTTP_201_CREATED)
async def chat_messages(body: ChatPersistRequest):
    url = f"{SUPABASE_URL}/rest/v1/chat_messages"
    headers = {**_supabase_service_headers(), "Prefer": "return=minimal"}
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
    conversation_id: Optional[str] = None,
):
    try:
        await _delete_chat_history_rows(user_id=user_id, mode=mode, conversation_id=conversation_id)
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to reach Supabase while deleting chat history.",
        )
    return {"message": "deleted"}


@app.get("/chat/conversations", response_model=ChatConversationsResponse)
async def chat_conversations(user_id: str, mode: Literal["general", "anxiety", "depression"]):
    url = f"{SUPABASE_URL}/rest/v1/chat_messages"
    params = {
        "user_id": f"eq.{user_id}",
        "mode": f"eq.{mode}",
        "select": "conversation_id,role,content,created_at",
        "order": "created_at.asc",
        "limit": "1000",
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                url, headers=_supabase_service_headers(), params=params, timeout=10.0
            )
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

    by_conversation: Dict[str, dict] = {}
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
                "user_messages": [content] if row_role == "user" and content else [],
            }
            continue
        if row_created > (existing.get("updated_at") or ""):
            existing["updated_at"] = row_created
            existing["latest_content"] = content or existing.get("latest_content", "")
        if row_role == "user" and content and len(existing["user_messages"]) < 3:
            existing["user_messages"].append(content)

    items = [
        ChatConversationItem(
            conversation_id=cid,
            title=_build_conversation_title(
                user_messages=agg.get("user_messages", []),
                fallback=agg.get("latest_content") or "New chat",
            ),
            updated_at=agg.get("updated_at") or "",
        )
        for cid, agg in by_conversation.items()
    ]
    items.sort(key=lambda i: i.updated_at, reverse=True)
    return ChatConversationsResponse(conversations=items)


# ── GAD-7 Protocol ────────────────────────────────────────────────────────

@app.post("/protocol/gad7/start")
async def gad7_start(body: GAD7ResetRequest):
    """Start a fresh GAD-7 session and return the first screening question."""
    _reset_gad7_session(body.user_id, body.conversation_id)
    await _delete_gad7_session_row(body.user_id, body.conversation_id)
    protocol = GAD7Protocol()
    await _save_gad7_session(body.user_id, body.conversation_id, protocol)
    return GAD7Response(
        reply=protocol.get_age_screening(),
        completed=False,
        state=protocol.get_state(),
    )


@app.post("/protocol/gad7/respond", response_model=GAD7Response)
async def gad7_respond(body: GAD7Request):
    # Load persisted state
    protocol = await _load_gad7_session(body.user_id, body.conversation_id)
    pre_state = protocol.get_state()

    # AI classifies user intent; protocol still enforces deterministic state transitions.
    detected_intent = _classify_gad7_intent_with_ai(body.user_message, pre_state)
    normalized_input = _map_intent_to_protocol_text(detected_intent, body.user_message)

    # Process input through the protocol state machine
    result = protocol.process_user_input(normalized_input)

    protocol_reply: str = result.get("reply", "")
    completed: bool = bool(result.get("completed", False))
    crisis: bool = bool(result.get("crisis", False))
    withdrawn: bool = bool(result.get("withdrawn", False))
    delete_partial: bool = bool(result.get("delete_partial", False))

    # Optionally wrap with a short LLM empathy prefix
    session_key = f"{body.user_id}:{body.conversation_id}"
    post_state = protocol.get_state()
    no_result: bool = bool(result.get("no_result", False))
    terminal_reason: Optional[str] = result.get("terminal_reason") or post_state.get("terminal_reason")
    # Lock state: when protocol expects one of the scoring options, keep replies strict.
    is_locked_frequency_step = bool(post_state.get("awaiting_frequency")) or detected_intent.startswith("freq_")

    if is_locked_frequency_step:
        final_reply = protocol_reply
    else:
        final_reply = _build_gad7_conversational_reply(
            session_key=session_key,
            intent=detected_intent,
            user_message=body.user_message,
            protocol_reply=protocol_reply,
            completed=completed,
            crisis=crisis,
            withdrawn=withdrawn,
        )

    # Persist updated state
    await _save_gad7_session(
        body.user_id, body.conversation_id, protocol, completed=completed
    )

    # Persist finalized research outcome once per session.
    if completed and not post_state.get("assessment_saved", False):
        assessment_payload = _build_gad7_assessment_payload(
            user_id=body.user_id,
            conversation_id=body.conversation_id,
            protocol=protocol,
            terminal_reason=terminal_reason,
            completed=completed,
            crisis=crisis,
        )
        if assessment_payload is not None:
            saved = await _insert_gad7_assessment(assessment_payload)
            protocol.assessment_saved = saved
        else:
            # Completed non-record outcomes (withdrawn/excluded) should not retry.
            protocol.assessment_saved = True
        post_state = protocol.get_state()
        await _save_gad7_session(
            body.user_id, body.conversation_id, protocol, completed=completed
        )

    # Delete partial data if participant withdrew or was excluded
    if delete_partial:
        try:
            await _delete_chat_history_rows(
                user_id=body.user_id,
                mode="anxiety",
                conversation_id=body.conversation_id,
            )
        except Exception as exc:
            print(f"[GAD7] failed to delete partial data: {exc}")

    return GAD7Response(
        reply=final_reply,
        completed=completed,
        score=result.get("score"),
        severity=result.get("severity"),
        crisis=crisis,
        withdrawn=withdrawn,
        delete_partial=delete_partial,
        no_result=no_result,
        terminal_reason=terminal_reason,
        state=post_state,
    )


@app.post("/protocol/gad7/reset")
async def gad7_reset(body: GAD7ResetRequest):
    """Hard reset: clears in-memory and DB state."""
    _reset_gad7_session(body.user_id, body.conversation_id)
    await _delete_gad7_session_row(body.user_id, body.conversation_id)
    return {"message": "reset"}


@app.post("/protocol/phq9/start")
async def phq9_start(body: GAD7ResetRequest):
    _reset_phq9_session(body.user_id, body.conversation_id)
    await _delete_phq9_session_row(body.user_id, body.conversation_id)
    protocol = PHQ9Protocol()
    await _save_phq9_session(body.user_id, body.conversation_id, protocol)
    return GAD7Response(
        reply=protocol.get_age_screening(),
        completed=False,
        state=protocol.get_state(),
    )


@app.post("/protocol/phq9/respond", response_model=GAD7Response)
async def phq9_respond(body: GAD7Request):
    protocol = await _load_phq9_session(body.user_id, body.conversation_id)
    pre_state = protocol.get_state()

    detected_intent = _classify_phq9_intent_with_ai(body.user_message, pre_state)
    normalized_input = _map_phq9_intent_to_protocol_text(detected_intent, body.user_message)
    result = protocol.process_user_input(normalized_input)

    protocol_reply: str = result.get("reply", "")
    completed: bool = bool(result.get("completed", False))
    crisis: bool = bool(result.get("crisis", False))
    withdrawn: bool = bool(result.get("withdrawn", False))
    delete_partial: bool = bool(result.get("delete_partial", False))

    post_state = protocol.get_state()
    no_result: bool = bool(result.get("no_result", False))
    terminal_reason: Optional[str] = result.get("terminal_reason") or post_state.get("terminal_reason")
    session_key = f"{body.user_id}:{body.conversation_id}"
    is_locked_frequency_step = bool(post_state.get("awaiting_frequency")) or detected_intent.startswith("freq_")

    if is_locked_frequency_step:
        final_reply = protocol_reply
    else:
        final_reply = _build_phq9_conversational_reply(
            session_key=session_key,
            intent=detected_intent,
            user_message=body.user_message,
            protocol_reply=protocol_reply,
            completed=completed,
            crisis=crisis,
            withdrawn=withdrawn,
        )

    await _save_phq9_session(body.user_id, body.conversation_id, protocol, completed=completed)

    if completed and not post_state.get("assessment_saved", False):
        assessment_payload = _build_phq9_assessment_payload(
            user_id=body.user_id,
            conversation_id=body.conversation_id,
            protocol=protocol,
            terminal_reason=terminal_reason,
            completed=completed,
            crisis=crisis,
        )
        if assessment_payload is not None:
            saved = await _insert_phq9_assessment(assessment_payload)
            protocol.assessment_saved = saved
        else:
            protocol.assessment_saved = True
        post_state = protocol.get_state()
        await _save_phq9_session(body.user_id, body.conversation_id, protocol, completed=completed)

    if delete_partial:
        try:
            await _delete_chat_history_rows(
                user_id=body.user_id,
                mode="depression",
                conversation_id=body.conversation_id,
            )
        except Exception as exc:
            print(f"[PHQ9] failed to delete partial data: {exc}")

    return GAD7Response(
        reply=final_reply,
        completed=completed,
        score=result.get("score"),
        severity=result.get("severity"),
        crisis=crisis,
        withdrawn=withdrawn,
        delete_partial=delete_partial,
        no_result=no_result,
        terminal_reason=terminal_reason,
        state=post_state,
    )


@app.post("/protocol/phq9/reset")
async def phq9_reset(body: GAD7ResetRequest):
    _reset_phq9_session(body.user_id, body.conversation_id)
    await _delete_phq9_session_row(body.user_id, body.conversation_id)
    return {"message": "reset"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
