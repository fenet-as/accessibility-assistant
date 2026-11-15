import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from assistant.api.dependencies import get_container, get_sms_adapter, get_telegram_adapter
from assistant.channels.sms import SMSAdapter, parse_inbound_payload
from assistant.channels.telegram import TelegramAdapter
from assistant.container import Container

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.get("/sms/inbound", tags=["SMS Channel"])
async def sms_inbound_check() -> Dict[str, Any]:
    """Health/verification check for SMS webhooks (e.g. Telerivet, Africa's Talking)."""
    return {"status": "ok", "message": "SMS webhook endpoint is active"}


@router.post("/sms/inbound", tags=["SMS Channel"])
async def sms_inbound(
    request: Request,
    sms: SMSAdapter = Depends(get_sms_adapter),
) -> Dict[str, Any]:
    """
    Universal 2-way inbound SMS webhook.
    Accepts Telerivet, Africa's Talking, Android GSM gateway, Twilio, or plain JSON.
    Normalizes Ethiopian numbers and returns Telerivet/gateway auto-reply messages.
    """
    sender, body = await parse_inbound_payload(request)
    normalized = sms.normalize_ethiopian_phone(sender)
    segments = sms.handle_inbound_sms(normalized, body, dispatch_replies=True)
    return {
        "status": "success",
        "sender": normalized,
        "segments": segments,
        "count": len(segments),
        "messages": [{"content": seg} for seg in segments],  # Telerivet auto-reply
    }


@router.post("/sms/delivery", tags=["SMS Channel"])
async def sms_delivery_report(
    payload: Dict[str, Any],
    container: Container = Depends(get_container),
) -> Dict[str, Any]:
    """Africa's Talking style delivery report callback."""
    provider_id = str(payload.get("id") or payload.get("messageId") or "")
    status_value = str(payload.get("status") or payload.get("failureReason") or "unknown")
    if provider_id and container.tutor.store.db:
        container.tutor.store.db.update_sms_status(provider_id, status_value)
    return {"status": "ok"}


@router.post("/telegram/webhook", tags=["Telegram Channel"])
async def telegram_webhook(
    update: Dict[str, Any],
    request: Request,
    telegram: TelegramAdapter = Depends(get_telegram_adapter),
    container: Container = Depends(get_container),
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """Webhook target for the Telegram Bot API. Requires TELEGRAM_WEBHOOK_SECRET when set."""
    expected = container.settings.telegram_webhook_secret
    if expected and x_telegram_bot_api_secret_token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Telegram webhook secret")

    # Staff claim/close commands from the staff chat.
    message = update.get("message") or {}
    text = (message.get("text") or "").strip()
    chat_id = str(message.get("chat", {}).get("id") or "")
    if chat_id and container.settings.telegram_staff_chat_id and chat_id == container.settings.telegram_staff_chat_id:
        if text.startswith("/claim "):
            ticket = text.split(None, 1)[1].strip()
            staff = str(message.get("from", {}).get("username") or message.get("from", {}).get("id") or "staff")
            claimed = container.escalations.claim(ticket, staff)
            return {"status": "ok", "action": "claim", "ok": bool(claimed)}
        if text.startswith("/close "):
            ticket = text.split(None, 1)[1].strip()
            closed = container.escalations.close(ticket)
            return {"status": "ok", "action": "close", "ok": bool(closed)}

    return {"status": "ok", "result": await telegram.handle_update(update)}
