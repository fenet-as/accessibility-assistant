from typing import Any, Dict

from fastapi import APIRouter, Depends, Request

from assistant.api.dependencies import get_sms_adapter, get_telegram_adapter
from assistant.channels.sms import SMSAdapter, parse_inbound_payload
from assistant.channels.telegram import TelegramAdapter

router = APIRouter(prefix="/api")


@router.post("/sms/inbound", tags=["SMS Channel"])
async def sms_inbound(
    request: Request,
    sms: SMSAdapter = Depends(get_sms_adapter),
) -> Dict[str, Any]:
    """
    Universal 2-way inbound SMS webhook.
    Accepts Africa's Talking, Android GSM gateway, Twilio, or plain JSON.
    Normalizes Ethiopian numbers and optionally dispatches replies.
    """
    sender, body = await parse_inbound_payload(request)
    normalized = sms.normalize_ethiopian_phone(sender)
    segments = sms.handle_inbound_sms(normalized, body, dispatch_replies=True)
    return {
        "status": "success",
        "sender": normalized,
        "segments": segments,
        "count": len(segments),
    }


@router.post("/telegram/webhook", tags=["Telegram Channel"])
async def telegram_webhook(
    update: Dict[str, Any],
    telegram: TelegramAdapter = Depends(get_telegram_adapter),
) -> Dict[str, Any]:
    """Webhook target for the Telegram Bot API."""
    return {"status": "ok", "result": await telegram.handle_update(update)}
