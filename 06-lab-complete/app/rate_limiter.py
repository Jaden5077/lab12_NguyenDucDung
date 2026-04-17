"""
Rate Limiter — Sliding Window Counter.

Lab 12: Giới hạn requests để bảo vệ API khỏi lạm dụng.
Algorithm: Sliding Window Log — track timestamps trong deque.
"""
import time
import json
import logging
from collections import defaultdict, deque

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


# In-memory sliding window — mỗi key có 1 deque timestamps
_rate_windows: dict[str, deque] = defaultdict(deque)


def check_rate_limit(key: str) -> None:
    """
    Kiểm tra rate limit cho 1 key (thường là user/API key).

    Algorithm: Sliding Window Log
    - Lưu timestamp mỗi request vào deque
    - Loại bỏ timestamps ngoài window (60s)
    - Nếu count >= limit → reject

    Args:
        key: Identifier để track (API key prefix, user_id, etc.)

    Raises:
        HTTPException 429: Nếu vượt limit
    """
    settings = _get_settings()
    now = time.time()
    window = _rate_windows[key]

    # Xóa timestamps cũ (ngoài window 60s)
    while window and window[0] < now - 60:
        window.popleft()

    if len(window) >= settings.rate_limit_per_minute:
        retry_after = int(60 - (now - window[0]))
        logger.warning(json.dumps({
            "event": "rate_limit_exceeded",
            "key": key[:8],
            "limit": settings.rate_limit_per_minute,
            "retry_after": retry_after,
        }))
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": settings.rate_limit_per_minute,
                "window_seconds": 60,
                "retry_after_seconds": max(retry_after, 1),
            },
            headers={"Retry-After": str(max(retry_after, 1))},
        )

    window.append(now)
