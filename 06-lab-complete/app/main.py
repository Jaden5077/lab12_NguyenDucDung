"""
Production AI Agent — Kết hợp tất cả Day 12 concepts + Gemini API

Checklist:
  ✅ Config từ environment (12-factor)
  ✅ Structured JSON logging
  ✅ API Key authentication
  ✅ Rate limiting
  ✅ Cost guard
  ✅ Input validation (Pydantic)
  ✅ Health check + Readiness probe
  ✅ Graceful shutdown
  ✅ Security headers
  ✅ CORS
  ✅ Error handling
  ✅ Gemini API integration (real Q&A)
"""
import os
import time
import signal
import logging
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.config import settings
from app.auth import verify_api_key
from app.rate_limiter import check_rate_limit
from app.cost_guard import check_and_record_cost, get_daily_cost, get_daily_budget

# ─────────────────────────────────────────────────────────
# Gemini API Client
# ─────────────────────────────────────────────────────────
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

gemini_client = None


def init_gemini():
    """Khởi tạo Gemini client."""
    global gemini_client
    if not GEMINI_AVAILABLE:
        return False
    if not settings.gemini_api_key:
        return False

    try:
        gemini_client = genai.Client(api_key=settings.gemini_api_key)
        return True
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to init Gemini: {e}")
        return False


def ask_gemini(question: str) -> str:
    """
    Gọi Gemini API để trả lời câu hỏi.

    Args:
        question: Câu hỏi từ user.

    Returns:
        str: Câu trả lời từ Gemini.

    Raises:
        HTTPException: Nếu Gemini không available hoặc gọi bị lỗi.
    """
    if gemini_client is None:
        raise HTTPException(
            status_code=503,
            detail="Gemini AI is not configured. Set GEMINI_API_KEY in .env"
        )

    try:
        response = gemini_client.models.generate_content(
            model=settings.llm_model,
            contents=question,
        )
        return response.text.strip()
    except Exception as e:
        logger.error(json.dumps({
            "event": "gemini_error",
            "error": str(e),
            "model": settings.llm_model,
        }))
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API error: {str(e)}"
        )


# ─────────────────────────────────────────────────────────
# Logging — JSON structured
# ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0

# ─────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }))

    # Init Gemini
    gemini_ok = init_gemini()
    if gemini_ok:
        logger.info(json.dumps({
            "event": "gemini_ready",
            "model": settings.llm_model,
        }))
    else:
        logger.warning(json.dumps({
            "event": "gemini_unavailable",
            "reason": "missing SDK or API key",
        }))

    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))

# ─────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    start = time.time()
    _request_count += 1
    try:
        response: Response = await call_next(request)
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if "server" in response.headers:
            del response.headers["server"]
        duration = round((time.time() - start) * 1000, 1)
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": duration,
        }))
        return response
    except Exception as e:
        _error_count += 1
        raise

# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000,
                          description="Your question for the agent")

class AskResponse(BaseModel):
    question: str
    answer: str
    model: str
    timestamp: str

# ─────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "llm": {
            "provider": "google-gemini",
            "model": settings.llm_model,
            "status": "connected" if gemini_client else "not configured",
        },
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
            "docs": "GET /docs",
        },
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    _key: str = Depends(verify_api_key),
):
    """
    Gửi câu hỏi đến AI agent (Gemini).

    **Authentication:** Include header `X-API-Key: <your-key>`
    """
    # Rate limit per API key
    check_rate_limit(_key[:8])  # use first 8 chars as key bucket

    # Budget check — estimate input tokens
    input_tokens = len(body.question.split()) * 2
    check_and_record_cost(input_tokens, 0)

    logger.info(json.dumps({
        "event": "agent_call",
        "q_len": len(body.question),
        "model": settings.llm_model,
        "client": str(request.client.host) if request.client else "unknown",
    }))

    # Gọi Gemini API
    answer = ask_gemini(body.question)

    # Record output cost
    output_tokens = len(answer.split()) * 2
    check_and_record_cost(0, output_tokens)

    logger.info(json.dumps({
        "event": "agent_response",
        "answer_len": len(answer),
        "estimated_tokens": input_tokens + output_tokens,
    }))

    return AskResponse(
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/health", tags=["Operations"])
def health():
    """Liveness probe. Platform restarts container if this fails."""
    status = "ok"
    checks = {
        "llm": {
            "provider": "gemini",
            "model": settings.llm_model,
            "connected": gemini_client is not None,
        }
    }
    return {
        "status": status,
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    """Readiness probe. Load balancer stops routing here if not ready."""
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    return {"ready": True, "gemini_connected": gemini_client is not None}


@app.get("/metrics", tags=["Operations"])
def metrics(_key: str = Depends(verify_api_key)):
    """Basic metrics (protected)."""
    daily_cost = get_daily_cost()
    daily_budget = get_daily_budget()
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "daily_cost_usd": round(daily_cost, 4),
        "daily_budget_usd": daily_budget,
        "budget_used_pct": round(daily_cost / daily_budget * 100, 1) if daily_budget > 0 else 0,
        "llm_model": settings.llm_model,
    }


# ─────────────────────────────────────────────────────────
# Graceful Shutdown
# ─────────────────────────────────────────────────────────
def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))

signal.signal(signal.SIGTERM, _handle_signal)


if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    logger.info(f"API Key: {settings.agent_api_key[:4]}****")
    logger.info(f"LLM: Gemini ({settings.llm_model})")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
