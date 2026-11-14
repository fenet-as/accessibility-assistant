"""
Telegram Channel Adapter for ALX Accessibility Assistant.
Normalizes Telegram updates to core ChatRequest and formats replies with inline keyboards.
"""

import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
import httpx
from dotenv import load_dotenv

_base_dir = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(_base_dir / ".env", override=True)

from assistant.core.models import ChatRequest, ChatStatus
from assistant.core.grounding import GroundingEngine

engine = GroundingEngine()


class TelegramAdapter:
    def __init__(self, token: Optional[str] = None):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "") if token is None else token
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""

    def is_configured(self) -> bool:
        return bool(self.token)

    async def get_me(self) -> Optional[Dict[str, Any]]:
        """Validate token and fetch bot metadata from Telegram API."""
        if not self.is_configured():
            return None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(f"{self.base_url}/getMe")
                if res.status_code == 200:
                    return res.json().get("result")
        except Exception:
            return None
        return None

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

    async def poll(self):
        """Run long-polling loop to listen for updates without webhooks."""
        if not self.is_configured():
            print("\n❌ [Telegram Bot] TELEGRAM_BOT_TOKEN is not set in .env!")
            print("👉 Get a token from @BotFather on Telegram and add it to your .env file:")
            print("   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ\n")
            return

        bot_info = await self.get_me()
        if not bot_info:
            print("\n❌ [Telegram Bot] Authentication failed! Please verify TELEGRAM_BOT_TOKEN in .env.")
            return

        username = bot_info.get("username", "UnknownBot")
        first_name = bot_info.get("first_name", "Assistant")
        print("\n" + "=" * 60)
        print(f"🤖 Telegram Bot Connected: @{username} ({first_name})")
        print("⚡ Mode: Long-Polling (No Webhook/Tunnel required!)")
        print("👂 Listening for messages... Send /start to your bot in Telegram.")
        print("=" * 60 + "\n")

        offset = 0
        async with httpx.AsyncClient(timeout=35.0) as client:
            while True:
                try:
                    res = await client.get(
                        f"{self.base_url}/getUpdates",
                        params={"offset": offset, "timeout": 25}
                    )
                    if res.status_code == 200:
                        updates = res.json().get("result", [])
                        for update in updates:
                            offset = update["update_id"] + 1
                            result = await self.handle_update(update)
                            action = result.get("action")
                            cid = result.get("chat_id")
                            if action:
                                print(f"📩 Handled '{action}' for Chat ID {cid}")
                    elif res.status_code == 409:
                        print("⚠️ [Telegram Bot] Conflict: Webhook is active or another instance is running. Waiting 5s...")
                        await asyncio.sleep(5)
                    else:
                        await asyncio.sleep(2)
                except httpx.TimeoutException:
                    continue
                except asyncio.CancelledError:
                    print("\n🛑 [Telegram Bot] Stopped polling.")
                    break
                except Exception as e:
                    print(f"⚠️ [Telegram Bot] Network error: {e}. Retrying in 3s...")
                    await asyncio.sleep(3)


if __name__ == "__main__":
    adapter = TelegramAdapter()
    try:
        asyncio.run(adapter.poll())
    except KeyboardInterrupt:
        print("\n🛑 Bot exited.")

