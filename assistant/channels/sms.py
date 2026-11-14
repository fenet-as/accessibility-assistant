"""Low-bandwidth SMS channel for Ethiopian learners.

Handles GSM segment limits, Ethiopian phone normalization (+251), inbound menus,
and optional outbound dispatch through Africa's Talking, an Android SIM gateway, or Twilio.
"""

import logging
import re
from typing import List, Optional, Tuple
from urllib.parse import parse_qs

import httpx
from fastapi import Request

from assistant.container import Container
from assistant.domain.language import contains_ethiopic
from assistant.domain.models import ChatRequest, ChatStatus

logger = logging.getLogger(__name__)

ASCII_LIMIT = 160
UNICODE_LIMIT = 70

MENU_EN = "ALX Assistant: Reply with your question, or:\n1: Jobs\n2: Human Tutor\n3: Amharic (አማርኛ)"
MENU_AM = "ALX ረዳት፡ ጥያቄዎን በአማርኛ ይጻፉ ወይም:\n1: ክፍት የሥራ ቦታዎች\n2: የቀጥታ መምህር እርዳታ"
HELP_COMMANDS = {"HELP", "INFO"}
AMHARIC_COMMANDS = {"3", "AMHARIC", "አማርኛ"}
JOBS_COMMANDS = {"1", "JOBS", "JOB", "ሥራ", "ስራ"}
HUMAN_COMMANDS = {"2", "HUMAN", "HELP ME", "TUTOR", "እርዳታ", "መምህር"}


def normalize_ethiopian_phone(phone: str) -> str:
    """Turn local Ethio Telecom (09…) / Safaricom (07…) numbers into E.164 (+251…)."""
    if not phone:
        return ""
    clean = re.sub(r"[^\d+]", "", phone.strip())
    if clean.startswith(("09", "07")) and len(clean) == 10:
        return "+251" + clean[1:]
    if clean.startswith("251") and len(clean) == 12:
        return "+" + clean
    if clean.startswith("+251"):
        return clean
    if clean.startswith("+"):
        return clean
    return "+251" + clean.lstrip("0")


def split_segments(text: str) -> List[str]:
    """Split text into SMS-sized segments without breaking words."""
    limit = UNICODE_LIMIT if contains_ethiopic(text) else ASCII_LIMIT
    if len(text) <= limit:
        return [text]

    segments: List[str] = []
    current = ""
    for word in text.split(" "):
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                segments.append(current)
            current = word
    if current:
        segments.append(current)
    return segments


async def parse_inbound_payload(request: Request) -> Tuple[str, str]:
    """Accept Africa's Talking, Twilio, Android GSM gateway, or plain JSON webhooks."""
    content_type = request.headers.get("content-type", "")
    sender = ""
    body = ""

    if "application/json" in content_type:
        try:
            data = await request.json()
            sender = data.get("sender") or data.get("from") or data.get("From") or ""
            body = data.get("body") or data.get("text") or data.get("message") or data.get("Body") or ""
        except Exception:
            pass
    else:
        try:
            raw = await request.body()
            if raw:
                flat = {k.lower(): v[0] for k, v in parse_qs(raw.decode("utf-8")).items()}
                sender = flat.get("from") or flat.get("sender") or flat.get("phonenumber") or ""
                body = flat.get("text") or flat.get("body") or flat.get("message") or ""
        except Exception:
            pass

    if not sender:
        sender = request.query_params.get("from") or request.query_params.get("sender") or "+251911000000"
    if not body:
        body = request.query_params.get("text") or request.query_params.get("body") or "HELP"
    return str(sender), str(body)


class SMSAdapter:
    def __init__(self, container: Container):
        self.container = container
        settings = container.settings
        self.at_api_key = settings.africas_talking_api_key
        self.at_username = settings.africas_talking_username
        self.android_gateway_url = settings.android_gateway_url
        self.android_gateway_token = settings.android_gateway_token
        self.twilio_sid = settings.twilio_account_sid
        self.twilio_token = settings.twilio_auth_token
        self.twilio_number = settings.twilio_phone_number

    def normalize_ethiopian_phone(self, phone: str) -> str:
        return normalize_ethiopian_phone(phone)

    def split_segments(self, text: str) -> List[str]:
        return split_segments(text)

    def send_outbound_sms(self, to_phone: str, message: str) -> bool:
        """Send one SMS segment. Returns True if a gateway accepted it, or if none is configured."""
        to_phone = normalize_ethiopian_phone(to_phone)
        logger.info("SMS outbound to %s: %s", to_phone, message[:80])

        if self.at_api_key:
            try:
                url = (
                    "https://api.sandbox.africastalking.com/version1/messaging"
                    if self.at_username == "sandbox"
                    else "https://api.africastalking.com/version1/messaging"
                )
                with httpx.Client(timeout=10.0) as client:
                    res = client.post(
                        url,
                        headers={
                            "apiKey": self.at_api_key,
                            "Accept": "application/json",
                            "Content-Type": "application/x-www-form-urlencoded",
                        },
                        data={"username": self.at_username, "to": to_phone, "message": message},
                    )
                    return res.status_code in (200, 201)
            except httpx.HTTPError as exc:
                logger.warning("Africa's Talking dispatch failed: %s", exc)

        if self.android_gateway_url:
            try:
                headers = {"Content-Type": "application/json"}
                if self.android_gateway_token:
                    headers["Authorization"] = f"Bearer {self.android_gateway_token}"
                with httpx.Client(timeout=10.0) as client:
                    res = client.post(
                        f"{self.android_gateway_url}/message",
                        headers=headers,
                        json={"to": to_phone, "message": message},
                    )
                    return res.status_code in (200, 201)
            except httpx.HTTPError as exc:
                logger.warning("Android gateway dispatch failed: %s", exc)

        if self.twilio_sid and self.twilio_token and self.twilio_number:
            try:
                with httpx.Client(timeout=10.0) as client:
                    res = client.post(
                        f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_sid}/Messages.json",
                        auth=(self.twilio_sid, self.twilio_token),
                        data={"From": self.twilio_number, "To": to_phone, "Body": message},
                    )
                    return res.status_code in (200, 201)
            except httpx.HTTPError as exc:
                logger.warning("Twilio dispatch failed: %s", exc)

        return True  # Simulator / no gateway configured: treat as delivered locally

    def handle_inbound_sms(
        self,
        sender: str,
        body: str,
        dispatch_replies: bool = False,
    ) -> List[str]:
        sender = normalize_ethiopian_phone(sender)
        text = body.strip()
        command = text.upper()
        session = f"sms-{sender}"

        if command in HELP_COMMANDS:
            segments = [MENU_EN]
        elif command in AMHARIC_COMMANDS:
            segments = [MENU_AM]
        elif command in JOBS_COMMANDS:
            segments = split_segments(self.container.careers.sms_summary())
        elif command in HUMAN_COMMANDS:
            ticket = self.container.escalations.create(session).ticket_id
            segments = [
                f"ALX Tutor: Human tutor request received (ticket {ticket}). "
                "A tutor has been notified and will reach out via SMS/Phone."
            ]
        else:
            request = ChatRequest(session=session, message=text, scope=self.container.settings.default_scope)
            response = self.container.tutor.answer(request)
            self.container.analytics.record_question(request, response)
            if response.status == ChatStatus.NOT_FOUND:
                from assistant.domain.messages import NOT_FOUND, localized
                reply = localized(NOT_FOUND, response.language)
            else:
                reference = f" (Ref: {response.citations[0].section})" if response.citations else ""
                reply = f"{response.answer}{reference}"
            segments = split_segments(reply)

        if dispatch_replies and sender:
            for segment in segments:
                self.send_outbound_sms(sender, segment)
        return segments
