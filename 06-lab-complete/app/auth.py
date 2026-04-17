"""
Authentication — API Key + JWT support.

Lab 12: Bảo mật API với authentication.
"""
import time
import json
import logging
from typing import Optional

from fastapi import HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency
_settings = None


def _get_settings():
    global _settings
    if _settings is None:
        from app.config import settings
        _settings = settings
    return _settings


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Xác thực API key từ header X-API-Key.

    Returns:
        str: API key nếu hợp lệ

    Raises:
        HTTPException 401: Nếu key thiếu hoặc sai
    """
    settings = _get_settings()

    if not api_key:
        logger.warning(json.dumps({"event": "auth_fail", "reason": "missing_key"}))
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include header: X-API-Key: <your-key>",
        )

    if api_key != settings.agent_api_key:
        logger.warning(json.dumps({"event": "auth_fail", "reason": "invalid_key"}))
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
        )

    return api_key
