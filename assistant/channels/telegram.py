"""Telegram channel: webhook handler plus a long-polling runner for local use.

Run the poller (no public URL needed): python -m assistant.channels.telegram
"""

import asyncio
import html
import logging
from typing import Any, Dict, Optional

import httpx

from assistant.container import Container
from assistant.domain.models import HUMAN_HELP_ACTION, ChatRequest, ChatStatus

logger = logging.getLogger(__name__)

API_TIMEOUT_SECONDS = 10.0
POLL_TIMEOUT_SECONDS = 25

WELCOME = (
    "👋 <b>Welcome to the ALX Learning & Career Assistant!</b>\n"
    "እንኳን ወደ ALX የትምህርት እና የሥራ ረዳት በደህና መጡ!\n\n"
    "You can ask me questions about your course materials in English or Amharic.\n"
    "Commands:\n"
    "• /jobs - View accessible job postings\n"
    "• /human - Request live human tutor help\n"
    "• /help - Instructions"
)
LANGUAGE_SWITCHED = {
    "am": "ቋንቋ ወደ አማርኛ ተቀይሯል። ጥያቄዎን ይጠይቁ።",
    "en": "Language switched to English. Ask your question.",
}
START_KEYBOARD = {
    "inline_keyboard": [
        [{"text": "English", "callback_data": "lang_en"}, {"text": "አማርኛ", "callback_data": "lang_am"}],
        [{"text": "💼 View Jobs", "callback_data": "jobs_view"},
         {"text": "🆘 Human Help", "callback_data": "human_help"}],
    ]
}
HUMAN_HELP_KEYBOARD = {
    "inline_keyboard": [[{"text": "Connect with Human Tutor 🆘", "callback_data": "human_help"}]]
}
CALLBACK_COMMANDS = {"human_help": "/human", "jobs_view": "/jobs"}


class TelegramAdapter:
    def __init__(self, container: Container, token: Optional[str] = None):
        self.container = container
        self.token = container.settings.telegram_bot_token if token is None else token
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""
        # Per-chat language preference; resets on restart, which only means auto-detect again.
        self._chat_languages: Dict[int, str] = {}

    def is_configured(self) -> bool:
        return bool(self.token)

    async def get_me(self) -> Optional[Dict[str, Any]]:
        if not self.is_configured():
            return None
        try:
            async with httpx.AsyncClient(timeout=API_TIMEOUT_SECONDS) as client:
                res = await client.get(f"{self.base_url}/getMe")
                return res.json().get("result") if res.status_code == 200 else None
        except httpx.HTTPError:
            return None

    async def send_message(self, chat_id: int, text: str, reply_markup: Optional[Dict[str, Any]] = None) -> bool:
        if not self.is_configured():
            return False
        payload: Dict[str, Any] = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            async with httpx.AsyncClient(timeout=API_TIMEOUT_SECONDS) as client:
                res = await client.post(f"{self.base_url}/sendMessage", json=payload)
                return res.status_code == 200
        except httpx.HTTPError:
            return False

    async def handle_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """Handle one Telegram update (webhook or polling) and describe what was done."""
        chat_id, text = None, ""
        callback = update.get("callback_query")
        message = update.get("message") or update.get("edited_message")

        if callback:
            chat_id = callback.get("message", {}).get("chat", {}).get("id")
            data = callback.get("data", "")
            if data.startswith("lang_"):
                return await self._set_language(chat_id, data.split("_", 1)[1])
            text = CALLBACK_COMMANDS.get(data, "")
        elif message:
            chat_id = message.get("chat", {}).get("id")
            text = (message.get("text") or "").strip()

        if not chat_id or not text:
            return {"status": "ignored"}

        if text.startswith(("/start", "/help")):
            await self.send_message(chat_id, WELCOME, reply_markup=START_KEYBOARD)
            return {"action": "start", "chat_id": chat_id}
        if text.startswith("/human"):
            return await self._escalate(chat_id)
        if text.startswith("/jobs"):
            await self.send_message(chat_id, self.container.careers.telegram_summary())
            return {"action": "jobs", "chat_id": chat_id}
        return await self._answer(chat_id, text)

    async def _set_language(self, chat_id: Optional[int], language: str) -> Dict[str, Any]:
        if language not in LANGUAGE_SWITCHED:
            return {"status": "ignored"}
        if chat_id:
            self._chat_languages[chat_id] = language
            await self.send_message(chat_id, LANGUAGE_SWITCHED[language])
        return {"action": "set_language", "lang": language, "chat_id": chat_id}

    async def _escalate(self, chat_id: int) -> Dict[str, Any]:
        language = self._chat_languages.get(chat_id, "en")
        escalation = self.container.escalations.create(f"tg-{chat_id}", language)
        url = html.escape(escalation.jitsi_room_url)
        await self.send_message(chat_id, (
            "🆘 <b>Live Human Escalation / የቀጥታ ረዳት</b>\n\n"
            f"{html.escape(escalation.message)}\n"
            "You are in full control of your screen sharing.\n\n"
            f"🔗 <b>Meeting Link:</b> <a href='{url}'>{url}</a>"
        ))
        return {"action": "human_escalate", "chat_id": chat_id, "room": escalation.jitsi_room_url}

    async def _answer(self, chat_id: int, text: str) -> Dict[str, Any]:
        request = ChatRequest(
            session=f"tg-{chat_id}",
            message=text,
            language=self._chat_languages.get(chat_id, "auto"),
            scope=self.container.settings.default_scope,
        )
        # Retrieval is CPU-bound; keep it off the event loop.
        response = await asyncio.to_thread(self.container.tutor.answer, request)
        await asyncio.to_thread(self.container.analytics.record_question, request, response)

        reply = html.escape(response.answer)
        if response.citations:
            reply += "\n\n📚 <b>Citations:</b>\n" + "\n".join(
                f"• {html.escape(c.title)} ({html.escape(c.section)})" for c in response.citations
            )
        wants_human = HUMAN_HELP_ACTION in response.actions or response.status == ChatStatus.NOT_FOUND
        await self.send_message(chat_id, reply, reply_markup=HUMAN_HELP_KEYBOARD if wants_human else None)
        return {
            "action": "answer",
            "chat_id": chat_id,
            "status": response.status.value,
            "citations": len(response.citations),
        }

    async def poll(self) -> None:
        """Long-poll Telegram for updates; no webhook or public tunnel required."""
        if not self.is_configured():
            print("TELEGRAM_BOT_TOKEN is not set. Get a token from @BotFather and add it to .env.")
            return
        bot = await self.get_me()
        if not bot:
            print("Telegram authentication failed. Check TELEGRAM_BOT_TOKEN in .env.")
            return

        print(f"Telegram bot @{bot.get('username')} connected. Long-polling; send /start to the bot.")
        offset = 0
        async with httpx.AsyncClient(timeout=POLL_TIMEOUT_SECONDS + 10) as client:
            while True:
                try:
                    res = await client.get(
                        f"{self.base_url}/getUpdates",
                        params={"offset": offset, "timeout": POLL_TIMEOUT_SECONDS},
                    )
                    if res.status_code == 409:
                        logger.warning("Webhook active or another poller running; retrying in 5s")
                        await asyncio.sleep(5)
                        continue
                    if res.status_code != 200:
                        await asyncio.sleep(2)
                        continue
                    for update in res.json().get("result", []):
                        offset = update["update_id"] + 1
                        result = await self.handle_update(update)
                        if result.get("action"):
                            logger.info("Handled %s for chat %s", result["action"], result.get("chat_id"))
                except httpx.TimeoutException:
                    continue
                except httpx.HTTPError as exc:
                    logger.warning("Telegram network error: %s; retrying in 3s", exc)
                    await asyncio.sleep(3)


def main() -> None:
    from assistant.container import get_container

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        asyncio.run(TelegramAdapter(get_container()).poll())
    except KeyboardInterrupt:
        print("Bot stopped.")


if __name__ == "__main__":
    main()
