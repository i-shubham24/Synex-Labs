"""
Module 3: Telegram Interactive Callback Handler.
Polls Telegram Bot API for button clicks and runs the matching outreach action.
Runs zero-cost long-polling without needing a public domain or webhook.
"""

import re
import time
import logging
from typing import Optional, List, Dict
import requests

from config.settings import settings
from config.redact import redact
from database.repository import LeadRepository

logger = logging.getLogger("delivery.telegram_listener")


class TelegramCallbackListener:
    """Long-polling listener for interactive Telegram inline button clicks."""

    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.offset = 0
        self.running = False
        self._failures = 0

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
                for update in self._get_updates():
                    self.offset = update["update_id"] + 1
                    if "callback_query" in update:
                        self._handle_callback(update["callback_query"])
                if self._failures:
                    logger.info("[Telegram Listener] Connection to Telegram restored.")
                self._failures = 0
            except Exception as e:
                # Back off while Telegram is unreachable, and keep the log readable
                self._failures += 1
                if self._failures == 1 or self._failures % 20 == 0:
                    logger.error(
                        f"[Telegram Listener] Telegram unreachable ({self._failures}x): "
                        f"{type(e).__name__}: {redact(str(e))[:160]}"
                    )
                time.sleep(min(300.0, 5.0 * self._failures))
            time.sleep(settings.TELEGRAM_POLL_INTERVAL)

    def stop(self):
        self.running = False

    def _get_updates(self):
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {"offset": self.offset, "timeout": 20, "allowed_updates": ["callback_query"]}
        resp = requests.get(url, params=params, timeout=25.0)
        return resp.json().get("result", []) if resp.ok else []

    # ------------------------------------------------------------------ dispatch

    def _handle_callback(self, callback_query: dict):
        from outreach import actions
        from delivery.telegram_bot import stage_buttons, TelegramAlerter

        query_id = callback_query.get("id")
        data = callback_query.get("data", "")
        message = callback_query.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")

        def done(toast: str, keyboard: Optional[List[List[Dict[str, str]]]] = None, label: Optional[str] = None):
            self._answer_callback(query_id, toast)
            if keyboard is not None or label:
                self._set_buttons(chat_id, message_id, keyboard or [[{"text": label, "callback_data": "noop"}]])

        try:
            if data == "noop":
                return self._answer_callback(query_id, "")

            m = re.fullmatch(r"contacted_(\d+)", data)
            if m:
                LeadRepository.mark_as_contacted(int(m.group(1)))
                return done(f"✅ Lead #{m.group(1)} marked as contacted", label=f"✅ Claimed & Contacted (Lead #{m.group(1)})")

            m = re.fullmatch(r"pcontacted_(\d+)", data)
            if m:
                pid = int(m.group(1))
                result = actions.mark_contacted(pid)
                return done("✅ " + result["message"], keyboard=[stage_buttons(pid)])

            m = re.fullmatch(r"pskip_(\d+)", data)
            if m:
                actions.set_prospect_stage(int(m.group(1)), "skipped")
                return done("🚫 Skipped", label=f"🚫 Skipped (Prospect #{m.group(1)})")

            m = re.fullmatch(r"pemail_(\d+)", data)
            if m:
                pid = int(m.group(1))
                result = actions.send_opener_email(pid)
                return done("📧 " + result["message"], keyboard=[stage_buttons(pid)])

            m = re.fullmatch(r"pstage_(\d+)_([a-z_]+)", data)
            if m:
                pid, stage = int(m.group(1)), m.group(2)
                result = actions.set_prospect_stage(pid, stage)
                if result.get("brief"):
                    from database.prospect_repository import ProspectRepository
                    TelegramAlerter().send_brief(ProspectRepository.get(pid), result["brief"])
                return done(result["message"], label=f"• {stage.replace('_', ' ').capitalize()} (Prospect #{pid})")

            m = re.fullmatch(r"fsent_(\d+)", data)
            if m:
                result = actions.followup_done(int(m.group(1)))
                return done(result["message"], label="✅ Follow-up sent")

            m = re.fullmatch(r"femail_(\d+)", data)
            if m:
                result = actions.send_followup_email(int(m.group(1)))
                return done(result["message"], label="📧 Follow-up emailed")

            m = re.fullmatch(r"fstop_(\d+)", data)
            if m:
                actions.stop_sequence(int(m.group(1)))
                return done("🔕 Follow-ups stopped", label="🔕 Stopped")

            m = re.fullmatch(r"rsend_(\d+)", data)
            if m:
                result = actions.send_reply(int(m.group(1)))
                return done(result["message"], label="📧 Answer sent")

            m = re.fullmatch(r"rdone_(\d+)", data)
            if m:
                actions.mark_reply_handled(int(m.group(1)))
                return done("✅ Handled", label="✅ Handled")

            self._answer_callback(query_id, "Unknown button")
        except actions.ActionError as e:
            self._answer_callback(query_id, f"⚠️ {e}"[:190])
        except Exception as e:
            logger.error(f"Error processing callback {data!r}: {e}")
            self._answer_callback(query_id, "Error, check the dashboard log.")

    # ------------------------------------------------------------------ telegram helpers

    def _answer_callback(self, query_id: str, text: str):
        url = f"https://api.telegram.org/bot{self.bot_token}/answerCallbackQuery"
        try:
            requests.post(url, json={"callback_query_id": query_id, "text": text[:190]}, timeout=5.0)
        except Exception:
            pass

    def _set_buttons(self, chat_id: int, message_id: int, keyboard: List[List[Dict[str, str]]]):
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/editMessageReplyMarkup",
                json={"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": keyboard}},
                timeout=5.0,
            )
        except Exception:
            pass
