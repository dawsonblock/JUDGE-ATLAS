import hmac
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.models.entities import (
    AuditLog,
)

_TOKEN_ROLE_IMPORTS = "import"
_TOKEN_ROLE_REVIEW = "review"
_TOKEN_ROLE_ADMIN = "admin"


def _compare_token(provided: str | None, expected: str | None) -> bool:
    """Constant-time token comparison using hmac.compare_digest."""
    if not provided or not expected:
        return False
    return hmac.compare_digest(provided.encode(), expected.encode())


def _require_token_for_role(
    settings: Settings,
    x_jta_admin_token: str | None,
    role: str,
) -> None:
    """Fail closed with 403 if token does not match the required role."""
    if role == _TOKEN_ROLE_IMPORTS:
        token = settings.admin_token
        configured = bool(token)
    elif role == _TOKEN_ROLE_REVIEW:
        token = settings.admin_review_token or settings.admin_token
        configured = bool(token)
    else:
        token = settings.admin_token or settings.admin_review_token
        configured = bool(token)

    if not configured:
        raise HTTPException(
            status_code=403,
            detail=f"Admin token not configured for role: {role}",
        )
    if not _compare_token(x_jta_admin_token, token):
        raise HTTPException(status_code=403, detail="Invalid admin token")


def require_admin_imports(
    x_jta_admin_token: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    if not settings.enable_admin_imports:
        raise HTTPException(
            status_code=403, detail="Admin imports are disabled"
        )
    _require_token_for_role(settings, x_jta_admin_token, _TOKEN_ROLE_IMPORTS)


def require_admin_review(
    x_jta_admin_token: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    if not settings.enable_admin_review:
        raise HTTPException(
            status_code=403, detail="Admin review is disabled"
        )
    _require_token_for_role(settings, x_jta_admin_token, _TOKEN_ROLE_REVIEW)


def require_admin_token(
    x_jta_admin_token: str | None = Header(default=None),
) -> str:
    """Require a valid admin token for general admin operations.

    Returns the token value for audit logging purposes.
    """
    settings = get_settings()
    token = settings.admin_token or settings.admin_review_token

    if not token:
        raise HTTPException(
            status_code=403, detail="Admin token not configured"
        )

    if not _compare_token(x_jta_admin_token, token):
        raise HTTPException(status_code=403, detail="Invalid admin token")

    return x_jta_admin_token or "system"


def require_public_event_post(
    x_jta_admin_token: str | None = Header(default=None),
) -> None:
    """Require admin token when public event posting is enabled."""
    settings = get_settings()
    if not settings.enable_public_event_post:
        raise HTTPException(
            status_code=403, detail="Public event posting is disabled"
        )
    _require_token_for_role(settings, x_jta_admin_token, _TOKEN_ROLE_ADMIN)


def log_mutation(
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    payload: dict[str, Any] | None = None,
    request: Request | None = None,
    token_role: str | None = None,
) -> None:
    """Log a mutation action to the audit log."""
    db: Session = SessionLocal()
    try:
        full_payload: dict[str, Any] = payload or {}
        if token_role:
            full_payload = {**full_payload, "token_role": token_role}
        log_entry = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=full_payload,
            actor_ip=(
                request.client.host
                if request and request.client
                else None
            ),
            created_at=datetime.now(timezone.utc),
        )
        db.add(log_entry)
        db.commit()
    except Exception:
        logging.exception("audit log write failed for action=%s", action)
        db.rollback()
    finally:
        db.close()
