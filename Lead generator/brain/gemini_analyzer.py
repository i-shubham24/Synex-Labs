import json
import logging
import re
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import requests

from config.settings import settings
from .prompts import SYSTEM_INSTRUCTION, ANALYSIS_PROMPT_TEMPLATE

logger = logging.getLogger("gemini_analyzer")


class LeadAnalysisResult(BaseModel):
    """Pydantic model representing Gemini's structured qualification output."""
    is_valid_lead: bool = Field(description="Whether the post is a genuine commercial buyer")
    project_category: str = Field(description="Category of the project")
    budget_indicator: str = Field(description="Estimated budget level")
    draft_icebreaker: str = Field(description="2-sentence conversational outreach message")
    confidence_score: float = Field(default=0.0, description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(default="", description="Explanation of qualification decision")


class GeminiAnalyzer:
    """
    Connects to Google Gemini Free Tier API.
    Performs AI lead filtering and generates tailored icebreakers.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self._client = None

        if self.api_key:
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
        Falls back to rule-based offline parsing if API key is not configured.
        """
        if not self.is_configured():
            logger.info("Gemini API key not configured. Using heuristic offline analysis.")
            return self._heuristic_fallback(title, content)

        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            platform=platform,
            source_channel=source_channel or "N/A",
            title=title or "N/A",
            author=author or "Anonymous",
            flair=flair or "None",
            content=content[:3000],  # Guard against massive token overflow
        )

        try:
            if self._client:
                return self._call_sdk(prompt)
            else:
                return self._call_rest(prompt)
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}. Falling back to REST/Heuristics.")
            try:
                return self._call_rest(prompt)
            except Exception as rest_err:
                logger.error(f"REST call also failed: {rest_err}")
                return self._heuristic_fallback(title, content, error_note=str(e))

    def _call_sdk(self, prompt: str) -> LeadAnalysisResult:
        """Invokes Gemini using official google-genai SDK."""
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            temperature=0.2,
        )

        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )

        raw_text = response.text or ""
        return self._parse_json_response(raw_text)

    def _call_rest(self, prompt: str) -> LeadAnalysisResult:
        """Direct REST fallback to Google Generative Language API."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            },
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("No candidates returned from Gemini API")

        parts = candidates[0].get("content", {}).get("parts", [])
        raw_text = parts[0].get("text", "") if parts else ""
        return self._parse_json_response(raw_text)

    def _parse_json_response(self, raw_text: str) -> LeadAnalysisResult:
        """Cleans and validates the JSON output from Gemini."""
        cleaned = raw_text.strip()
        # Remove potential markdown markdown ```json ... ``` wrappers
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        data = json.loads(cleaned)
        return LeadAnalysisResult(
            is_valid_lead=bool(data.get("is_valid_lead", False)),
            project_category=str(data.get("project_category", "Custom Web App")),
            budget_indicator=str(data.get("budget_indicator", "Not mentioned")),
            draft_icebreaker=str(data.get("draft_icebreaker", "")),
            confidence_score=float(data.get("confidence_score", 0.8)),
            reasoning=str(data.get("reasoning", "")),
        )

    def _heuristic_fallback(self, title: str, content: str, error_note: str = "") -> LeadAnalysisResult:
        """
        Offline fallback when Gemini API key is missing or quota is exhausted.
        Ensures the system never crashes and can be tested locally.
        """
        text = f"{title} {content}".lower()
        is_hiring = any(k in text for k in ["hiring", "need a developer", "need a website", "looking for developer", "build an app"])
        is_selling = any(k in text for k in ["for hire", "i will build", "hire me", "my portfolio"])

        is_valid = is_hiring and not is_selling

        return LeadAnalysisResult(
            is_valid_lead=is_valid,
            project_category="Website Redesign" if "redesign" in text else "Custom Web App",
            budget_indicator="Not mentioned",
            draft_icebreaker=(
                "Hey! Saw you're looking for help building this out. At SynexLabs we specialize in "
                "custom high-performance web applications and would love to share a couple of architecture ideas."
                if is_valid else ""
            ),
            confidence_score=0.5,
            reasoning=f"Heuristic offline rule evaluation. {error_note}".strip(),
        )
