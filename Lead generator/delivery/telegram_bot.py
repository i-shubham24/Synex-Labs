"""
Module 3: Delivery & Alerting Layer (The "Hands").
Routes verified buyer leads to SynexLabs private Telegram channel
with inline action buttons: [Open Lead URL] and [Mark as Contacted].
Human-in-the-loop: Never auto-DMs or spams platforms directly.
"""

import logging
from typing import Dict, Any, Optional
import requests

from config.settings import settings
from database.repository import LeadRepository

logger = logging.getLogger("delivery.telegram")


class TelegramAlerter:
    """Dispatches qualified leads to Telegram Bot channel."""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send_lead_alert(self, lead: Dict[str, Any]) -> bool:
        """
        Formats and sends a high-intent lead card with inline action buttons.
        """
        if not self.is_configured():
            logger.info("Telegram bot credentials not configured. Skipping alert dispatch.")
            return False

        lead_id = lead["id"]
        platform = lead.get("platform", "reddit").capitalize()
        category = lead.get("project_category", "Web Development")
        budget = lead.get("budget_indicator", "Not mentioned")
        title = lead.get("title", "")
        author = lead.get("author", "Unknown")
        source = lead.get("source_channel", "")
        url = lead.get("url", "")
        icebreaker = lead.get("draft_icebreaker", "")

        message_text = (
            f"🔥 <b>NEW HIGH-INTENT LEAD DETECTED</b>\n\n"
            f"<b>Platform:</b> {platform} ({source})\n"
            f"<b>Category:</b> {category}\n"
            f"<b>Estimated Budget:</b> {budget}\n"
            f"<b>Author:</b> u/{author}\n\n"
            f"<b>Title:</b> {title}\n\n"
            f"💡 <b>Drafted Icebreaker:</b>\n"
            f"<i>\"{icebreaker}\"</i>"
        )

        # Telegram Inline Keyboard Buttons
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "🔗 Open Lead Post", "url": url},
                    {"text": "✅ Mark Contacted", "callback_data": f"contacted_{lead_id}"},
                ]
            ]
        }

        api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message_text,
            "parse_mode": "HTML",
            "reply_markup": reply_markup,
            "disable_web_page_preview": False,
        }

        try:
            resp = requests.post(api_url, json=payload, timeout=10.0)
            if resp.ok:
                LeadRepository.mark_as_alerted(lead_id)
                logger.info(f"Successfully alerted lead #{lead_id} on Telegram.")
                return True
            else:
                logger.error(f"Telegram API error: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False
