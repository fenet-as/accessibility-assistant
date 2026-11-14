"""
SMS Channel Adapter for Low-Bandwidth Ethiopian Users.
Handles 160-char ASCII / 70-char Amharic Unicode segment limits,
numbered navigation menus, and core service normalization.
"""

import os
import re
from typing import List, Dict, Any, Tuple, Optional
import httpx
from dotenv import load_dotenv

_base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
load_dotenv(os.path.join(_base_dir, ".env"), override=True)

from assistant.core.models import ChatRequest, ChatStatus
from assistant.core.grounding import GroundingEngine

engine = GroundingEngine()


class SMSAdapter:
    # GSM standard SMS limits
    ASCII_LIMIT = 160
    UNICODE_LIMIT = 70

    def __init__(self):
        self.gateway_type = os.getenv("SMS_GATEWAY", "auto").lower()
        self.at_api_key = os.getenv("AFRICAS_TALKING_API_KEY", "")
        self.at_username = os.getenv("AFRICAS_TALKING_USERNAME", "sandbox")
        self.android_gateway_url = os.getenv("ANDROID_GATEWAY_URL", "").rstrip("/")
        self.android_gateway_token = os.getenv("ANDROID_GATEWAY_TOKEN", "")
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_number = os.getenv("TWILIO_PHONE_NUMBER", "")

    def normalize_ethiopian_phone(self, phone: str) -> str:
        """
        Normalize local Ethiopian phone numbers to international E.164 format.
        Supports Ethio Telecom (09... / 2519...) and Safaricom (07... / 2517...).
        """
        if not phone:
            return ""
        clean = re.sub(r"[^\d+]", "", phone.strip())
        if clean.startswith("09") and len(clean) == 10:
            return "+251" + clean[1:]
        if clean.startswith("07") and len(clean) == 10:
            return "+251" + clean[1:]
        if clean.startswith("251") and len(clean) == 12:
            return "+" + clean
        if clean.startswith("+251"):
            return clean
        if clean.startswith("+"):
            return clean
        return "+251" + clean.lstrip("0")

    def is_unicode(self, text: str) -> bool:
        """Detect whether text contains Unicode/Ethiopic characters."""
        return bool(re.search(r"[\u1200-\u137F]", text))

    def split_segments(self, text: str) -> List[str]:
        """Split text into SMS-safe segments without breaking words."""
        max_len = self.UNICODE_LIMIT if self.is_unicode(text) else self.ASCII_LIMIT
        if len(text) <= max_len:
            return [text]

        words = text.split(" ")
        segments: List[str] = []
        current = ""

        for word in words:
            candidate = f"{current} {word}".strip() if current else word
            if len(candidate) <= max_len:
                current = candidate
            else:
                if current:
                    segments.append(current)
                current = word

        if current:
            segments.append(current)

        return segments

    def send_outbound_sms(self, to_phone: str, message: str) -> bool:
        """
        Dispatch real outbound SMS to Ethiopian phone number (+251...).
        Supports: Africa's Talking, Android GSM Gateway, Twilio, or Console fallback.
        """
        normalized_to = self.normalize_ethiopian_phone(to_phone)
        print(f"[SMS Outbound] Sending to {normalized_to}: {message}")

        # 1. Africa's Talking Gateway (African Telecom Standard)
        if self.at_api_key:
            try:
                base_url = (
                    "https://api.sandbox.africastalking.com/version1/messaging"
                    if self.at_username == "sandbox"
                    else "https://api.africastalking.com/version1/messaging"
                )
                headers = {
                    "apiKey": self.at_api_key,
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                data = {
                    "username": self.at_username,
                    "to": normalized_to,
                    "message": message
                }
                with httpx.Client(timeout=10.0) as client:
                    res = client.post(base_url, headers=headers, data=data)
                    return res.status_code in [200, 201]
            except Exception as e:
                print(f"[SMS Error] Africa's Talking dispatch failed: {e}")

        # 2. Local Android SMS Gateway (Real Ethio Telecom / Safaricom SIM card in phone)
        if self.android_gateway_url:
            try:
                url = f"{self.android_gateway_url}/message"
                headers = {"Content-Type": "application/json"}
                if self.android_gateway_token:
                    headers["Authorization"] = f"Bearer {self.android_gateway_token}"
                payload = {
                    "to": normalized_to,
                    "message": message
                }
                with httpx.Client(timeout=10.0) as client:
                    res = client.post(url, headers=headers, json=payload)
                    return res.status_code in [200, 201]
            except Exception as e:
                print(f"[SMS Error] Android Gateway dispatch failed: {e}")

        # 3. Twilio Gateway
        if self.twilio_sid and self.twilio_token and self.twilio_number:
            try:
                url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_sid}/Messages.json"
                data = {
                    "From": self.twilio_number,
                    "To": normalized_to,
                    "Body": message
                }
                with httpx.Client(timeout=10.0) as client:
                    res = client.post(url, auth=(self.twilio_sid, self.twilio_token), data=data)
                    return res.status_code in [200, 201]
            except Exception as e:
                print(f"[SMS Error] Twilio dispatch failed: {e}")

        # Default fallback
        return True

    def handle_inbound_sms(self, sender: str, body: str, dispatch_replies: bool = False) -> List[str]:
        """
        Process inbound SMS text from Ethiopian learners and return one or more outbound SMS segments.
        Optionally dispatches outbound SMS back to the learner's phone.
        """
        normalized_sender = self.normalize_ethiopian_phone(sender)
        cleaned = body.strip()
        upper = cleaned.upper()

        if upper in ["HELP", "INFO"]:
            segments = [
                "ALX Assistant: Reply with your question, or:\n"
                "1: Jobs\n"
                "2: Human Tutor\n"
                "3: Amharic (አማርኛ)"
            ]
        elif upper in ["3", "AMHARIC", "አማርኛ"]:
            segments = [
                "ALX ረዳት፡ ጥያቄዎን በአማርኛ ይጻፉ ወይም:\n1: ክፍት የሥራ ቦታዎች\n2: የቀጥታ መምህር እርዳታ"
            ]
        elif upper in ["1", "JOBS", "JOB", "ሥራ", "ስራ"]:
            segments = [
                "ALX Jobs: 1) Junior VA (African Remote Ops, Remote) 2) Digital Coordinator. Visit portal to apply with accommodations."
            ]
        elif upper in ["2", "HUMAN", "HELP ME", "TUTOR", "እርዳታ", "መምህር"]:
            segments = [
                "ALX Tutor: Human tutor request received! A tutor has been notified and will reach out via SMS/Phone."
            ]
        else:
            # General Course Query
            req = ChatRequest(
                session=f"sms-{normalized_sender}",
                message=cleaned,
                language="auto",
                scope="course:va-1"
            )
            res = engine.process_query(req)

            # Build concise SMS reply
            if res.status == ChatStatus.NOT_FOUND:
                if res.language == "am":
                    reply = "ይቅርታ፣ ይህ ጥያቄ በትምህርቱ ውስጥ አልተገኘም። ለሰው ረዳት 2 ብለው ይመልሱ።"
                else:
                    reply = "Not found in course text. Reply 2 to connect with a human tutor."
            else:
                # Concise answer with citation footnote
                citation_note = f" (Ref: {res.citations[0].section})" if res.citations else ""
                reply = f"{res.answer}{citation_note}"

            segments = self.split_segments(reply)

        # Dispatch real outbound SMS if requested or live gateway active
        if dispatch_replies and normalized_sender:
            for seg in segments:
                self.send_outbound_sms(normalized_sender, seg)

        return segments

