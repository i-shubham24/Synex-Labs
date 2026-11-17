import json
import logging
import re
import threading
import time
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import requests

from config.settings import settings
from .prompts import (
    SYSTEM_INSTRUCTION,
    ANALYSIS_PROMPT_TEMPLATE,
    PROSPECT_SYSTEM_INSTRUCTION,
    PROSPECT_OPENER_TEMPLATE,
)

logger = logging.getLogger("gemini_analyzer")


class GeminiUnavailable(Exception):
    """
    Raised when Gemini cannot be reached (missing key, quota exhausted, network error).
    Callers must leave the item pending and retry later. The engine never guesses
    a lead decision without the model.
    """


class LeadAnalysisResult(BaseModel):
    """Pydantic model representing Gemini's structured qualification output."""
    is_valid_lead: bool = Field(description="Whether the post is a genuine commercial buyer")
    project_category: str = Field(description="Category of the project")
    budget_indicator: str = Field(description="Estimated budget level")
    draft_icebreaker: str = Field(description="2-sentence conversational outreach message")
    confidence_score: float = Field(default=0.0, description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(default="", description="Explanation of qualification decision")
    country: str = Field(default="Unknown", description="Buyer's country if stated or implied")
    first_website: bool = Field(default=False, description="No website yet")
    old_website: bool = Field(default=False, description="Wants to upgrade an old / unresponsive site")


class GeminiAnalyzer:
    """
    Connects to Google Gemini Free Tier API.
    Performs AI lead filtering and generates tailored icebreakers / prospect openers.
    """

    # Shared across instances so every caller respects the free-tier RPM limit.
    _pace_lock = threading.Lock()
    _last_call_at = 0.0
    # Last failure, read by the health monitor
    last_error: Optional[str] = None
    last_error_at: float = 0.0
    # model -> time until which it is skipped (daily quota used up or model retired)
    _exhausted: Dict[str, float] = {}

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self._client = None

        if self.is_configured():
            try:
                from google import genai
                self._client = genai.Client(
                    api_key=self.api_key,
                    http_options={"api_version": "v1beta"},
                )
            except Exception as e:
                logger.warning(f"Could not initialize google-genai SDK: {e}. Will use REST API.")

    def is_configured(self) -> bool:
        """Returns True if a Gemini API key is present."""
        return bool(self.api_key and self.api_key.strip() and not self.api_key.startswith("your_"))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_post(
        self,
        platform: str,
        title: str,
        content: str,
        source_channel: str = "",
        author: str = "",
        flair: str = "",
    ) -> LeadAnalysisResult:
        """
        Evaluates a post using Gemini and returns structured LeadAnalysisResult.
        Raises GeminiUnavailable if the model cannot be reached, and ValueError
        if the model returned unparseable output for this one post.
        """
        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            platform=platform,
            source_channel=source_channel or "N/A",
            title=title or "N/A",
            author=author or "Anonymous",
            flair=flair or "None",
            content=(content or "")[:3000],  # Guard against massive token overflow
        )
        data = self._parse_json(self._generate(prompt, SYSTEM_INSTRUCTION))
        return LeadAnalysisResult(
            is_valid_lead=bool(data.get("is_valid_lead", False)),
            project_category=str(data.get("project_category", "Other")),
            budget_indicator=str(data.get("budget_indicator", "Not mentioned")),
            draft_icebreaker=str(data.get("draft_icebreaker", "")),
            confidence_score=float(data.get("confidence_score", 0.0)),
            reasoning=str(data.get("reasoning", "")),
            country=str(data.get("country") or "Unknown").strip()[:60] or "Unknown",
            first_website=bool(data.get("first_website", False)),
            old_website=bool(data.get("old_website", False)),
        )

    def write_prospect_opener(self, context: Dict[str, Any]) -> str:
        """
        Writes a short first message for a local business prospect, grounded in
        the audit findings passed in `context`. Raises GeminiUnavailable / ValueError.
        """
        prompt = PROSPECT_OPENER_TEMPLATE.format(**context)
        data = self._parse_json(self._generate(prompt, PROSPECT_SYSTEM_INSTRUCTION))
        opener = str(data.get("opener", "")).strip()
        if not opener:
            raise ValueError("Gemini returned an empty opener")
        return opener

    def generate_json(self, prompt: str, system_instruction: str, images: Optional[List[bytes]] = None) -> Dict[str, Any]:
        """Any structured task. Images (PNG bytes) are sent alongside the prompt."""
        return self._parse_json(self._generate(prompt, system_instruction, images=images))

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def _pace(self):
        """Keeps calls under the free-tier requests-per-minute limit."""
        with GeminiAnalyzer._pace_lock:
            wait = settings.GEMINI_MIN_INTERVAL_SECONDS - (time.monotonic() - GeminiAnalyzer._last_call_at)
            if wait > 0:
                time.sleep(wait)
            GeminiAnalyzer._last_call_at = time.monotonic()

    def _generate(self, prompt: str, system_instruction: str, images: Optional[List[bytes]] = None) -> str:
        if not self.is_configured():
            raise GeminiUnavailable("GEMINI_API_KEY is not set in .env")

        # Main model first, then backups. A model that ran out of daily quota (429) or was
        # retired (404) is skipped for a few hours, so the engine keeps working on the next one.
        candidates = [self.model] + [m for m in settings.GEMINI_FALLBACK_MODELS if m != self.model]
        now = time.time()
        usable = [m for m in candidates if GeminiAnalyzer._exhausted.get(m, 0) < now] or candidates[-1:]
        last_exc: Optional[Exception] = None
        for model in usable:
            self._pace()
            try:
                if self._client:
                    text = self._call_sdk(prompt, system_instruction, images, model)
                else:
                    text = self._call_rest(prompt, system_instruction, images, model)
                GeminiAnalyzer.last_error = None
                return text
            except Exception as e:
                last_exc = e
                message = str(e)
                if "429" in message or "RESOURCE_EXHAUSTED" in message or "404" in message or "NOT_FOUND" in message:
                    GeminiAnalyzer._exhausted[model] = now + 3 * 3600
                    logger.warning(f"Gemini model {model} unavailable ({self._short_error(e)[:80]}); trying the next one.")
                    continue
                break  # other errors (network, bad request) are not fixed by another model
        GeminiAnalyzer.last_error = self._short_error(last_exc)
        GeminiAnalyzer.last_error_at = time.time()
        raise GeminiUnavailable(GeminiAnalyzer.last_error) from last_exc

    def _call_sdk(self, prompt: str, system_instruction: str, images: Optional[List[bytes]] = None,
                  model: Optional[str] = None) -> str:
        """Invokes Gemini using official google-genai SDK."""
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.2,
        )
        contents: Any = prompt
        if images:
            contents = [types.Part.from_bytes(data=img, mime_type=self._mime(img)) for img in images] + [prompt]
        response = self._client.models.generate_content(
            model=model or self.model,
            contents=contents,
            config=config,
        )
        return response.text or ""

    def _call_rest(self, prompt: str, system_instruction: str, images: Optional[List[bytes]] = None,
                   model: Optional[str] = None) -> str:
        """Direct REST call to Google Generative Language API (used when the SDK is missing)."""
        import base64

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model or self.model}:generateContent"
        parts = [
            {"inline_data": {"mime_type": self._mime(img), "data": base64.b64encode(img).decode()}}
            for img in (images or [])
        ] + [{"text": prompt}]
        payload = {
            "contents": [{"parts": parts}],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            },
        }
        resp = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
            timeout=30.0,
        )
        resp.raise_for_status()
        candidates = resp.json().get("candidates", [])
        if not candidates:
            raise ValueError("No candidates returned from Gemini API")
        parts = candidates[0].get("content", {}).get("parts", [])
        return parts[0].get("text", "") if parts else ""

    @staticmethod
    def _mime(img: bytes) -> str:
        return "image/jpeg" if img[:2] == b"\xff\xd8" else "image/png"

    @staticmethod
    def _parse_json(raw_text: str) -> Dict[str, Any]:
        """Cleans and parses the JSON output from Gemini. Raises ValueError on bad output."""
        cleaned = (raw_text or "").strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned).strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Gemini returned invalid JSON: {cleaned[:120]}") from e
        if not isinstance(data, dict):
            raise ValueError("Gemini returned JSON that is not an object")
        return data

    @staticmethod
    def _short_error(e: Exception) -> str:
        """One-line error summary with any API key scrubbed out."""
        text = re.sub(r"key=[A-Za-z0-9_\-]+", "key=REDACTED", str(e))
        text = " ".join(text.split())
        if "429" in text or "RESOURCE_EXHAUSTED" in text:
            return "Gemini quota exhausted (429). Remaining items stay pending until quota resets."
        return f"{type(e).__name__}: {text[:200]}"
