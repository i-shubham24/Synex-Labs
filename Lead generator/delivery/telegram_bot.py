"""
Module 3: Delivery & Alerting Layer (The "Hands").
Routes leads, prospects, follow-ups and replies to the SynexLabs private Telegram
channel with one-tap buttons. Human-in-the-loop: the bot never DMs anyone itself;
WhatsApp buttons open the chat with the message typed, you press send.
"""

import html
import logging
from typing import Dict, Any, Optional, List
import requests

from config.settings import settings
from config.redact import redact
from database.repository import LeadRepository

logger = logging.getLogger("delivery.telegram")


def _e(value: Any) -> str:
    """Escapes text for Telegram HTML parse mode."""
    return html.escape(str(value or ""), quote=False)


def _author_handle(platform: str, author: str) -> str:
    platform = (platform or "").lower()
    if platform == "reddit":
        return f"u/{author}"
    if platform in ("twitter", "bluesky"):
        return f"@{author}"
    return author or "Unknown"


def _is_http_url(url: str) -> bool:
    return bool(url) and url.lower().startswith(("http://", "https://"))


def stage_buttons(pid: int) -> List[Dict[str, str]]:
    return [
        {"text": "💬 Replied", "callback_data": f"pstage_{pid}_replied"},
        {"text": "🗓 Call booked", "callback_data": f"pstage_{pid}_call_booked"},
        {"text": "🙅 No", "callback_data": f"pstage_{pid}_not_interested"},
    ]


class TelegramAlerter:
    """Dispatches qualified leads and prospects to Telegram Bot channel."""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def _send(self, text: str, keyboard: Optional[List[List[Dict[str, str]]]] = None) -> bool:
        if not self.is_configured():
            logger.info("Telegram bot credentials not configured. Skipping alert dispatch.")
            return False
        payload: Dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": text[:4000],
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        rows = [row for row in (keyboard or []) if row]
        if rows:
            payload["reply_markup"] = {"inline_keyboard": rows}
        try:
            resp = requests.post(f"https://api.telegram.org/bot{self.bot_token}/sendMessage", json=payload, timeout=10.0)
            if resp.ok:
                return True
            logger.error(f"Telegram API error: {redact(resp.text[:300])}")
            return False
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {redact(str(e))}")
            return False

    def send_text(self, text: str) -> bool:
        return self._send(text)

    # ------------------------------------------------------------------ social / website leads

    def send_lead_alert(self, lead: Dict[str, Any]) -> bool:
        """Formats and sends a high-intent lead card with inline action buttons."""
        lead_id = lead["id"]
        platform = lead.get("platform") or "reddit"
        url = lead.get("url", "")
        website = platform == "website"
        head = "📨 <b>NEW WEBSITE ENQUIRY</b>" if website else "🔥 <b>NEW HIGH-INTENT LEAD DETECTED</b>"
        tags = []
        if "india" in (lead.get("country") or "").lower():
            tags.append("🇮🇳 India")
        if lead.get("first_website"):
            tags.append("1st priority: no website yet")
        elif lead.get("old_website"):
            tags.append("2nd priority: old website upgrade")
        if tags:
            head += "\n<b>" + _e(" · ".join(tags)) + "</b>"
        draft_label = "Drafted reply (send from your own inbox)" if website else "Drafted Icebreaker"
        lines = [
            head, "",
            f"<b>Platform:</b> {_e(platform.capitalize())} ({_e(lead.get('source_channel'))})",
            f"<b>Category:</b> {_e(lead.get('project_category') or 'Web Development')}",
        ]
        if not website:
            lines.append(f"<b>Estimated Budget:</b> {_e(lead.get('budget_indicator') or 'Not mentioned')}")
        lines.append(f"<b>{'From' if website else 'Author'}:</b> {_e(_author_handle(platform, lead.get('author')))}")
        if lead.get("reply_email"):
            lines.append(f"<b>Email:</b> {_e(lead['reply_email'])}")
        lines += ["", f"<b>Title:</b> {_e(lead.get('title'))}"]
        if website and lead.get("content"):
            lines += ["", f"<i>{_e(lead['content'][:700])}</i>"]
        lines += ["", f"💡 <b>{draft_label}:</b>", f"<i>\"{_e(lead.get('draft_icebreaker'))}\"</i>"]

        row = []
        if _is_http_url(url):
            row.append({"text": "🔗 Open Lead Post", "url": url})
        row.append({"text": "✅ Mark Contacted", "callback_data": f"contacted_{lead_id}"})
        if self._send("\n".join(lines), [row]):
            LeadRepository.mark_as_alerted(lead_id)
            logger.info(f"Successfully alerted lead #{lead_id} on Telegram.")
            return True
        return False

    # ------------------------------------------------------------------ maps prospects

    def _contact_row(self, p: Dict[str, Any], message: str, email_callback: Optional[str]) -> List[Dict[str, str]]:
        from outreach.links import whatsapp_link
        from outreach import emailer

        row = []
        wa = whatsapp_link(p.get("phone") or "", message, p.get("city"))
        if wa:
            row.append({"text": "💬 WhatsApp", "url": wa})
        if email_callback and p.get("email") and emailer.is_configured() and p.get("email_status") != "bounced":
            row.append({"text": "📧 Email it", "callback_data": email_callback})
        if _is_http_url(p.get("maps_url", "")):
            row.append({"text": "📍 Maps", "url": p["maps_url"]})
        return row

    def send_prospect_alert(self, p: Dict[str, Any]) -> bool:
        """Sends a local-business prospect card. Caller updates the prospect status."""
        from prospector.scoring import TIER_LABELS  # local import avoids a package cycle

        tier = p.get("tier", "")
        icon = {
            "no_website": "🏪",
            "social_only": "📱",
            "broken_website": "🧯",
            "weak_website": "🛠",
            "no_website_unverified": "🔎",
        }.get(tier, "📍")

        from prospector.priority import label as priority_label
        from outreach.links import country_code_for

        text, group = priority_label(tier, bool(p.get("old_site")))
        rank = {"first": "1ST PRIORITY · ", "upgrade": "2ND PRIORITY · "}.get(group, "")
        india = country_code_for(p.get("city") or "") == settings.PRIORITY_COUNTRY_CODE
        headline = (text or TIER_LABELS.get(tier, tier)).upper()
        lines = [
            f"{'🇮🇳 ' if india else ''}{icon} <b>{rank}{_e(headline)}</b>  ·  heat {int(p.get('heat_score') or 0)}/100",
            "",
            f"<b>Business:</b> {_e(p.get('name'))}",
            f"<b>Niche / City:</b> {_e(p.get('niche'))} · {_e(p.get('city'))}",
        ]
        if p.get("rating"):
            lines.append(f"<b>Rating:</b> {p['rating']} ({int(p.get('review_count') or 0)} reviews)")
        if p.get("phone"):
            lines.append(f"<b>Phone:</b> {_e(p['phone'])}")
        if p.get("email"):
            lines.append(f"<b>Email:</b> {_e(p['email'])}")
        if p.get("website"):
            lines.append(f"<b>Website:</b> {_e(p['website'])}")
        if p.get("address"):
            lines.append(f"<b>Address:</b> {_e(p['address'])}")
        for social in (p.get("socials") or [])[:2]:
            lines.append(f"<b>Social:</b> {_e(social)}")

        issues = p.get("issues") or []
        if issues:
            lines += ["", "<b>Why pitch them:</b>"] + [f"• {_e(i)}" for i in issues[:5]]

        if p.get("opener"):
            tag = "Drafted opener" if p.get("opener_source") == "gemini" else "Template opener"
            lines += ["", f"💬 <b>{tag}:</b>", f"<i>{_e(p['opener'])}</i>"]
        lines += ["", "<i>Tap WhatsApp (message is pre-typed), then ✅ Contacted.</i>"]

        row1 = self._contact_row(p, p.get("opener") or "", f"pemail_{p['id']}")
        row2 = [
            {"text": "✅ Contacted", "callback_data": f"pcontacted_{p['id']}"},
            {"text": "🚫 Skip", "callback_data": f"pskip_{p['id']}"},
        ]
        return self._send("\n".join(lines), [row1, row2])

    # ------------------------------------------------------------------ follow-ups

    def send_followup_card(self, p: Dict[str, Any], number: int, message: str) -> bool:
        lines = [
            f"🔁 <b>FOLLOW-UP {number} DUE</b>  ·  {_e(p.get('name'))}",
            f"{_e(p.get('niche'))} · {_e(p.get('city'))}" + (f" · via {_e(p['channel'])}" if p.get("channel") else ""),
        ]
        if p.get("phone"):
            lines.append(f"<b>Phone:</b> {_e(p['phone'])}")
        lines += ["", f"<i>{_e(message)}</i>", "", "<i>Send it, then tap ✅ Sent.</i>"]
        row1 = self._contact_row(p, message, f"femail_{p['id']}")
        row2 = [
            {"text": "✅ Sent", "callback_data": f"fsent_{p['id']}"},
            {"text": "💬 Replied", "callback_data": f"pstage_{p['id']}_replied"},
            {"text": "🔕 Stop", "callback_data": f"fstop_{p['id']}"},
        ]
        return self._send("\n".join(lines), [row1, row2])

    # ------------------------------------------------------------------ email replies

    def send_reply_alert(self, email_row: Dict[str, Any], p: Dict[str, Any]) -> bool:
        label = (email_row.get("label") or "other").replace("_", " ")
        lines = [
            f"💬 <b>REPLY FROM {_e(p.get('name')).upper()}</b>  ·  {_e(label)}",
            f"<b>From:</b> {_e(email_row.get('from_addr'))}",
        ]
        if email_row.get("summary"):
            lines.append(f"<b>Summary:</b> {_e(email_row['summary'])}")
        lines += ["", f"<i>{_e((email_row.get('body') or '')[:900])}</i>"]
        keyboard = []
        if email_row.get("draft_reply"):
            lines += ["", "✍️ <b>Drafted answer:</b>", f"<i>{_e(email_row['draft_reply'])}</i>"]
            keyboard.append([{"text": "📧 Send this answer", "callback_data": f"rsend_{email_row['id']}"}])
        keyboard.append([
            {"text": "🗓 Call booked", "callback_data": f"pstage_{p['id']}_call_booked"},
            {"text": "✅ Handled", "callback_data": f"rdone_{email_row['id']}"},
        ])
        return self._send("\n".join(lines), keyboard)

    # ------------------------------------------------------------------ sales

    def send_brief(self, p: Dict[str, Any], brief: Dict[str, Any]) -> bool:
        lines = [f"🗓 <b>PRE-CALL BRIEF</b>  ·  {_e(p.get('name'))}", "", _e(brief.get("summary"))]
        if brief.get("talking_points"):
            lines += ["", "<b>Talking points</b>"] + [f"• {_e(x)}" for x in brief["talking_points"]]
        if brief.get("questions"):
            lines += ["", "<b>Ask them</b>"] + [f"• {_e(x)}" for x in brief["questions"]]
        if brief.get("recommended_package"):
            lines += ["", f"<b>Suggest:</b> {_e(brief['recommended_package'])}"]
        if brief.get("price_note"):
            lines.append(_e(brief["price_note"]))
        return self._send("\n".join(lines))
