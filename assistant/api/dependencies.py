"""FastAPI dependencies: access to the shared container and admin authorization."""

import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status

from assistant.channels.sms import SMSAdapter
from assistant.channels.telegram import TelegramAdapter
from assistant.container import Container


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_sms_adapter(request: Request) -> SMSAdapter:
    return request.app.state.sms


def get_telegram_adapter(request: Request) -> TelegramAdapter:
    return request.app.state.telegram


def require_admin(
    container: Container = Depends(get_container),
    x_admin_token: Optional[str] = Header(default=None),
) -> None:
    """Course management requires X-Admin-Token when ADMIN_TOKEN is set.

    When ADMIN_TOKEN is empty, access is refused unless ALLOW_OPEN_ADMIN=true
    (local development only).
    """
    expected = container.settings.admin_token
    if not expected:
        if container.settings.allow_open_admin:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ADMIN_TOKEN is not configured; set ADMIN_TOKEN or ALLOW_OPEN_ADMIN=true for local use",
        )
    if not secrets.compare_digest(x_admin_token or "", expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin token required")
