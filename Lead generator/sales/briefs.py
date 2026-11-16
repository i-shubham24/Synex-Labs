"""Pre-call brief: generated when a prospect is marked 'call booked'."""

import json
import logging
from typing import Dict, Any

from database.prospect_repository import ProspectRepository
from database.email_repository import EmailRepository
from brain.gemini_analyzer import GeminiAnalyzer, GeminiUnavailable
from brain.prompts import BRIEF_SYSTEM_INSTRUCTION
from .packages import load_packages, recommend, price_text

logger = logging.getLogger("sales.briefs")


def _template_brief(p: Dict[str, Any]) -> Dict[str, Any]:
    pkg = recommend(p)
    issues = p.get("issues") or []
    return {
        "summary": f"{p['name']} is a {p.get('niche') or 'local business'} in {p.get('city') or 'their area'}. "
                   f"{issues[0] if issues else 'Their online presence can be stronger.'}",
        "talking_points": issues[:4] or ["How customers find them today", "What a new site should achieve"],
        "questions": [
            "How do most new customers find you today?",
            "What would a good website change for your business?",
            "Who will update the site, and how often?",
            "Is there a date you want it live by?",
        ],
        "recommended_package": pkg["name"],
        "price_note": f"Starts at {price_text(pkg, p)}, live in about {pkg['timelineDays']} days.",
    }


def build_brief(prospect_id: int) -> Dict[str, Any]:
    p = ProspectRepository.get(prospect_id)
    if not p:
        raise ValueError("prospect not found")
    gemini = GeminiAnalyzer()
    brief = None
    if gemini.is_configured():
        thread = EmailRepository.thread(prospect_id)
        convo = "\n".join(
            f"{'Us' if e['direction'] == 'out' else 'Them'}: {(e.get('body') or '')[:400]}" for e in thread[-4:]
        ) or "No email thread (contacted by WhatsApp or phone)."
        pkgs = "\n".join(f"- {x['name']} ({x['kind']}): {price_text(x, p)}, {x['timelineDays']} days" for x in load_packages())
        prompt = (
            f"Business: {p['name']}\nType: {p.get('niche')}\nCity: {p.get('city')}\n"
            f"Rating: {p.get('rating') or 'n/a'} ({p.get('review_count') or 0} reviews)\n"
            f"Website: {p.get('website') or 'none'}\nStatus: {p.get('tier')}\n"
            f"Findings:\n" + "\n".join(f"- {i}" for i in (p.get('issues') or [])) +
            f"\n\nConversation so far:\n{convo}\n\nPackages:\n{pkgs}"
        )
        try:
            data = gemini.generate_json(prompt, BRIEF_SYSTEM_INSTRUCTION)
            if data.get("summary"):
                brief = {
                    "summary": str(data.get("summary")),
                    "talking_points": [str(x) for x in data.get("talking_points") or []][:5],
                    "questions": [str(x) for x in data.get("questions") or []][:4],
                    "recommended_package": str(data.get("recommended_package") or recommend(p)["name"]),
                    "price_note": str(data.get("price_note") or ""),
                }
        except (GeminiUnavailable, ValueError) as e:
            logger.info(f"Brief via template ({e})")
    brief = brief or _template_brief(p)
    ProspectRepository.update(prospect_id, brief=json.dumps(brief))
    return brief
