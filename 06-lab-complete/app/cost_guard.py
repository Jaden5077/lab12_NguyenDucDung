"""
Cost Guard — Budget protection.

Lab 12: Dừng khi vượt budget hàng ngày để tránh chi phí phát sinh.
In-memory tracking (production nên dùng Redis).
"""
import time
import json
import logging

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Lazy import
_settings = None


def _get_settings():
    global _settings
    if _settings is None:
        from app.config import settings
        _settings = settings
    return _settings


# In-memory daily cost tracker
_daily_cost: float = 0.0
_cost_reset_day: str = time.strftime("%Y-%m-%d")


def check_and_record_cost(input_tokens: int, output_tokens: int) -> None:
    """
    Kiểm tra và ghi nhận chi phí.

    Pricing estimate (Gemini Flash):
    - Input:  ~$0.00015 / 1K tokens
    - Output: ~$0.0006  / 1K tokens

    Args:
        input_tokens: Số estimated input tokens
        output_tokens: Số estimated output tokens

    Raises:
        HTTPException 503: Nếu vượt daily budget
    """
    global _daily_cost, _cost_reset_day
    settings = _get_settings()

    today = time.strftime("%Y-%m-%d")
    if today != _cost_reset_day:
        logger.info(json.dumps({
            "event": "budget_reset",
            "previous_day": _cost_reset_day,
            "previous_cost": round(_daily_cost, 6),
        }))
        _daily_cost = 0.0
        _cost_reset_day = today

    if _daily_cost >= settings.daily_budget_usd:
        logger.warning(json.dumps({
            "event": "budget_exhausted",
            "daily_cost": round(_daily_cost, 4),
            "budget": settings.daily_budget_usd,
        }))
        raise HTTPException(503, "Daily budget exhausted. Try tomorrow.")

    # Estimate cost
    cost = (input_tokens / 1000) * 0.00015 + (output_tokens / 1000) * 0.0006
    _daily_cost += cost


def get_daily_cost() -> float:
    """Return current daily cost."""
    return _daily_cost


def get_daily_budget() -> float:
    """Return daily budget limit."""
    return _get_settings().daily_budget_usd
