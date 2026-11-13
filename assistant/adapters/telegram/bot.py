"""
Telegram Channel Adapter for ALX Accessibility Assistant.
Normalizes Telegram updates to core ChatRequest and formats replies with inline keyboards.
"""

import os
from typing import Dict, Any, Optional
import httpx
from assistant.core.models import ChatRequest, ChatStatus
from assistant.core.grounding import GroundingEngine

engine = GroundingEngine()


class TelegramAdapter:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""

    def is_configured(self) -> bool:
        return bool(self.token)

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send message via Telegram Bot API."""
        if not self.is_configured():
            return False

        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(f"{self.base_url}/sendMessage", json=payload)
                return res.status_code == 200
            except Exception:
                return False

    async def handle_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming Telegram update (from webhook or long-polling).
        Returns a normalized dict describing the handled action.
        """
        message = update.get("message") or update.get("edited_message")
        callback_query = update.get("callback_query")

        chat_id = None
        user_text = ""
        user_lang = "auto"

        if callback_query:
            chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
            data = callback_query.get("data", "")
            if data.startswith("lang_"):
                user_lang = data.split("_")[1]
                reply_text = (
                    "ቋንቋ ወደ አማርኛ ተቀይሯል። ጥያቄዎን ይጠይቁ።"
                    if user_lang == "am"
                    else "Language switched to English. Ask your question."
                )
                if chat_id:
                    await self.send_message(chat_id, reply_text)
                return {"action": "set_language", "lang": user_lang, "chat_id": chat_id}

            if data == "human_help":
                user_text = "/human"

        elif message:
            chat_id = message.get("chat", {}).get("id")
            user_text = message.get("text", "").strip()

        if not chat_id or not user_text:
            return {"status": "ignored"}

        # Command: /start
        if user_text.startswith("/start"):
            welcome = (
                "👋 <b>Welcome to the ALX Learning & Career Assistant!</b>\n"
                "እንኳን ወደ ALX የትምህርት እና የሥራ ረዳት በደህና መጡ!\n\n"
                "You can ask me questions about your course materials in English or Amharic.\n"
                "Commands:\n"
                "• /jobs - View accessible job postings\n"
                "• /human - Request live human tutor help\n"
                "• /help - Instructions"
            )
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "English", "callback_data": "lang_en"},
                        {"text": "አማርኛ", "callback_data": "lang_am"}
                    ],
                    [
                        {"text": "💼 View Jobs", "callback_data": "jobs_view"},
                        {"text": "🆘 Human Help", "callback_data": "human_help"}
                    ]
                ]
            }
            await self.send_message(chat_id, welcome, reply_markup=keyboard)
            return {"action": "start", "chat_id": chat_id}

        # Command: /human
        if user_text.startswith("/human"):
            room_name = f"ALX-Help-{os.urandom(3).hex().upper()}"
            jitsi_link = f"https://meet.jit.si/{room_name}"
            msg = (
                "🆘 <b>Live Human Escalation / የቀጥታ ረዳት</b>\n\n"
                "A live support session has been prepared. "
                "You are in full control of your screen sharing.\n\n"
                f"🔗 <b>Meeting Link:</b> <a href='{jitsi_link}'>{jitsi_link}</a>"
            )
            await self.send_message(chat_id, msg)
            return {"action": "human_escalate", "chat_id": chat_id, "room": room_name}

        # Command: /jobs
        if user_text.startswith("/jobs"):
            jobs_msg = (
                "💼 <b>Career Gateway - Available Positions</b>\n\n"
                "1. <b>Junior Virtual Assistant</b>\n"
                "   • Company: African Remote Operations\n"
                "   • Accommodations: Screen reader friendly, flexible hours\n\n"
                "2. <b>Digital Project Coordinator</b>\n"
                "   • Company: EthioTech Talent Hub\n"
                "   • Accommodations: Accessible tools, interview accommodations\n\n"
                "<i>To request interview accommodations, visit the web assistant portal.</i>"
            )
            await self.send_message(chat_id, jobs_msg)
            return {"action": "jobs", "chat_id": chat_id}

        # General Course Query: Normalized Core Processing
        req = ChatRequest(
            session=f"tg-{chat_id}",
            message=user_text,
            language=user_lang,
            scope="course:va-1"
        )
        response = engine.process_query(req)

        # Format Telegram Response
        formatted = f"{response.answer}\n"
        if response.citations:
            formatted += "\n📚 <b>Citations:</b>\n"
            for c in response.citations:
                formatted += f"• {c.title} ({c.section})\n"

        keyboard = None
        if "get_human_help" in response.actions or response.status == ChatStatus.NOT_FOUND:
            keyboard = {
                "inline_keyboard": [
                    [{"text": "Connect with Human Tutor 🆘", "callback_data": "human_help"}]
                ]
            }

        await self.send_message(chat_id, formatted, reply_markup=keyboard)
        return {
            "action": "answer",
            "chat_id": chat_id,
            "status": response.status.value,
            "citations": len(response.citations)
        }

