"""
ADVANCED — Stateless Agent với Redis Session

Stateless = agent không giữ state trong memory.
Mọi state (session, conversation history) lưu trong Redis.

Tại sao stateless quan trọng khi scale?
  Instance 1: User A gửi request 1 → lưu session trong memory
  Instance 2: User A gửi request 2 → KHÔNG có session! Bug!

  ✅ Giải pháp: Lưu session trong Redis
  Bất kỳ instance nào cũng đọc được session của user.

Demo:
  docker compose up
  # Sau đó test multi-turn conversation
  python test_stateless.py
"""
import os
import time
import json
import logging
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from utils.mock_llm import ask

# ── Redis (bắt buộc để stateless hoạt động đúng khi scale)
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL, decode_responses=True)

try:
    r.ping()
    print("✅ Connected to Redis")
except Exception as e:
    # ❌ KHÔNG fallback về in-memory — sẽ phá vỡ tính stateless khi scale
    raise RuntimeError(
        f"Cannot connect to Redis ({REDIS_URL}). "
        "Stateless agent yêu cầu Redis để hoạt động đúng khi scale.\n"
        f"Original error: {e}"
    )


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

START_TIME = time.time()
INSTANCE_ID = os.getenv("INSTANCE_ID", f"instance-{uuid.uuid4().hex[:6]}")

# Số message tối đa giữ lại trong history (10 turns = 20 messages)
MAX_HISTORY = 20
# TTL mặc định cho mỗi session (giây)
SESSION_TTL = 3600


# ──────────────────────────────────────────────────────────
# Session Storage — Redis List (stateless-compatible)
#
# ✅ Correct pattern: dùng Redis list (rpush / lrange / ltrim)
#   r.rpush(key, value)        → append message vào cuối list
#   r.lrange(key, 0, -1)       → đọc toàn bộ list
#   r.ltrim(key, -MAX, -1)     → giữ chỉ MAX message cuối
#   r.expire(key, TTL)         → đặt TTL để tự dọn dẹp
#
# ❌ Anti-pattern (KHÔNG làm):
#   conversation_history = {}          ← dict trong memory của process
#   history = conversation_history[u]  ← mỗi instance có dict riêng → bug khi scale
# ──────────────────────────────────────────────────────────

def _history_key(session_id: str) -> str:
    """Trả về Redis key cho history của một session."""
    return f"history:{session_id}"


def append_message(session_id: str, role: str, content: str) -> None:
    """
    ✅ Correct: Ghi message vào Redis list.
    Dùng rpush để append, ltrim để giới hạn kích thước, expire để tự dọn.
    """
    key = _history_key(session_id)
    message = json.dumps({
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    r.rpush(key, message)                   # append vào cuối list
    r.ltrim(key, -MAX_HISTORY, -1)          # giữ MAX_HISTORY message cuối
    r.expire(key, SESSION_TTL)              # reset TTL mỗi lần có hoạt động


def get_history(session_id: str) -> list[dict]:
    """
    ✅ Correct: Đọc history từ Redis list bằng lrange.
    Bất kỳ instance nào cũng đọc được — không phụ thuộc memory local.
    """
    key = _history_key(session_id)
    raw_messages = r.lrange(key, 0, -1)    # đọc toàn bộ list
    return [json.loads(m) for m in raw_messages]


def session_exists(session_id: str) -> bool:
    """Kiểm tra session có tồn tại trong Redis không."""
    return r.exists(_history_key(session_id)) > 0


def delete_session(session_id: str) -> None:
    """Xóa toàn bộ history của session khỏi Redis."""
    r.delete(_history_key(session_id))


# ──────────────────────────────────────────────────────────
# App Setup
# ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting instance {INSTANCE_ID}")
    logger.info("Storage: Redis ✅ (stateless-ready)")
    yield
    logger.info(f"Instance {INSTANCE_ID} shutting down")


app = FastAPI(
    title="Stateless Agent",
    version="4.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None   # None = tạo session mới


# ──────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────

@app.post("/chat")
async def chat(body: ChatRequest):
    """
    ✅ Stateless multi-turn conversation.

    State (history) lưu trong Redis — KHÔNG trong memory của instance.
    Bất kỳ instance nào cũng serve được request tiếp theo của cùng user.

    Gửi session_id trong các request tiếp theo để tiếp tục cuộc trò chuyện.
    """
    # Tạo hoặc dùng session hiện có
    session_id = body.session_id or str(uuid.uuid4())

    # ✅ Correct: lưu câu hỏi vào Redis list (không phải dict trong memory)
    append_message(session_id, "user", body.question)

    # Đọc history từ Redis để có context (stateless: không giữ gì trong RAM)
    history = get_history(session_id)
    turn_number = sum(1 for m in history if m["role"] == "user")

    # Gọi LLM
    answer = ask(body.question)

    # ✅ Correct: lưu response vào Redis list
    append_message(session_id, "assistant", answer)

    return {
        "session_id": session_id,
        "question": body.question,
        "answer": answer,
        "turn": turn_number,
        "served_by": INSTANCE_ID,      # ← bất kỳ instance nào cũng serve được
        "storage": "redis",            # ← luôn là redis, không có fallback
    }


@app.get("/chat/{session_id}/history")
def get_chat_history(session_id: str):
    """
    Xem conversation history của một session.
    ✅ Đọc từ Redis bằng lrange — không phụ thuộc instance nào đã xử lý trước.
    """
    if not session_exists(session_id):
        raise HTTPException(404, f"Session '{session_id}' không tồn tại hoặc đã hết hạn")

    # ✅ Correct: r.lrange(key, 0, -1) thay vì dict lookup trong memory
    messages = get_history(session_id)
    return {
        "session_id": session_id,
        "messages": messages,
        "count": len(messages),
    }


@app.delete("/chat/{session_id}")
def delete_chat_session(session_id: str):
    """
    Xóa session (user logout).
    ✅ Xóa Redis key — có hiệu lực trên tất cả instances ngay lập tức.
    """
    if not session_exists(session_id):
        raise HTTPException(404, f"Session '{session_id}' không tồn tại hoặc đã hết hạn")

    delete_session(session_id)
    return {"deleted": session_id}


# ──────────────────────────────────────────────────────────
# Health / Metrics
# ──────────────────────────────────────────────────────────

@app.get("/health")
def health():
    try:
        r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    return {
        "status": "ok" if redis_ok else "degraded",
        "instance_id": INSTANCE_ID,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "storage": "redis",
        "redis_connected": redis_ok,
    }


@app.get("/ready")
def ready():
    try:
        r.ping()
    except Exception:
        raise HTTPException(503, "Redis không khả dụng — instance chưa sẵn sàng")
    return {"ready": True, "instance": INSTANCE_ID}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)