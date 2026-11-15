"""
Module 3: Telegram Interactive Callback Handler.
Polls Telegram Bot API for button clicks (e.g. [Mark as Contacted]).
Updates SQLite database state and edits the message to show it was claimed.
Runs zero-cost long-polling without needing a public domain or webhook.
"""

import time
import logging
from typing import Optional
import requests

from config.settings import settings
from database.repository import LeadRepository

logger = logging.getLogger("delivery.telegram_listener")


class TelegramCallbackListener:
    """Long-polling listener for interactive Telegram inline button clicks."""

    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.offset = 0
        self.running = False

    def is_configured(self) -> bool:
        return bool(self.bot_token and not self.bot_token.startswith("your_"))

    def start_polling(self):
        """Starts continuous polling loop for Telegram button callbacks."""
        if not self.is_configured():
            logger.info("[Telegram Listener] Bot token not configured. Skipping listener.")
            return

        self.running = True
        logger.info("[Telegram Listener] Started polling for button interactions...")

        while self.running:
            try:
                updates = self._get_updates()
                for update in updates:
                    self.offset = update["update_id"] + 1
                    if "callback_query" in update:
                        self._handle_callback(update["callback_query"])
            except Exception as e:
                logger.error(f"[Telegram Listener] Polling error: {e}")
                time.sleep(5.0)

            time.sleep(settings.TELEGRAM_POLL_INTERVAL)

    def stop(self):
        self.running = False

    def _get_updates(self):
        """Calls getUpdates with long polling timeout."""
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {
            "offset": self.offset,
            "timeout": 20,
            "allowed_updates": ["callback_query"],
        }
        resp = requests.get(url, params=params, timeout=25.0)
        if resp.ok:
            return resp.json().get("result", [])
        return []

    def _handle_callback(self, callback_query: dict):
        """Processes [Mark as Contacted] clicks."""
        query_id = callback_query.get("id")
        data = callback_query.get("data", "")
        message = callback_query.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")

        if data.startswith("contacted_"):
            try:
                lead_id = int(data.split("_")[1])
                LeadRepository.mark_as_contacted(lead_id)
                logger.info(f"Lead #{lead_id} marked as contacted via Telegram callback.")

                # 1. Toast notification on user's Telegram client
                self._answer_callback(query_id, text=f"✅ Lead #{lead_id} marked as Contacted!")

                # 2. Update inline buttons to show claimed status
                self._update_message_buttons(chat_id, message_id, lead_id)
            except Exception as e:
                logger.error(f"Error processing callback: {e}")
                self._answer_callback(query_id, text="Error updating lead.")

    def _answer_callback(self, query_id: str, text: str):
        url = f"https://api.telegram.org/bot{self.bot_token}/answerCallbackQuery"
        requests.post(url, json={"callback_query_id": query_id, "text": text}, timeout=5.0)

    def _update_message_buttons(self, chat_id: int, message_id: int, lead_id: int):
        """Replaces button with [✅ Claimed & Contacted]."""
        url = f"https://api.telegram.org/bot{self.bot_token}/editMessageReplyMarkup"
        updated_keyboard = {
            "inline_keyboard": [
                [
                    {"text": f"✅ Claimed & Contacted (Lead #{lead_id})", "callback_data": "noop"}
                ]
            ]
        }
        requests.post(
            url,
            json={
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_markup": updated_keyboard,
            },
            timeout=5.0,
        )
