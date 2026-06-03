import json
import logging
import re
from typing import Any

import google.generativeai as genai

from app.core.config import settings
from app.models.event import Event

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        genai.configure(api_key=self.api_key)
        self._model = genai.GenerativeModel(self.model_name)

    def analyze_event(self, event: Event) -> dict[str, Any]:
        prompt = self._build_prompt(event)
        response = self._model.generate_content(prompt)
        return self._parse_response(response.text)

    def _build_prompt(self, event: Event) -> str:
        payload = json.dumps(event.payload or {}, ensure_ascii=True)
        return f"""You are a business automation analyst. Analyze the following event.

Event ID: {event.id}
Event type: {event.event_type}
Source: {event.source}
Payload: {payload}

Respond with valid JSON only, no markdown, using this exact structure:
{{
  "classification": "short category label",
  "summary": "concise executive summary of the event",
  "recommendations": ["send_email", "generate_report"]
}}

The recommendations array MUST use these exact automation action keys when applicable:
- send_email: notify stakeholders by email
- generate_report: create a PDF report and upload to S3
- notify_team: internal team notification

For payment failures, chargebacks, or other high-severity financial events,
ALWAYS include send_email and generate_report as the first two recommendations.
You may add additional keys after those two if needed.
"""

    def _parse_response(self, raw_text: str) -> dict[str, Any]:
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        data = json.loads(text)

        classification = data.get("classification")
        summary = data.get("summary")
        recommendations = data.get("recommendations")

        if not isinstance(classification, str) or not classification.strip():
            raise ValueError("Gemini response missing valid classification")
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("Gemini response missing valid summary")
        if not isinstance(recommendations, list):
            raise ValueError("Gemini response missing valid recommendations list")

        return {
            "classification": classification.strip(),
            "summary": summary.strip(),
            "recommendations": recommendations,
        }


def get_gemini_client() -> GeminiClient:
    return GeminiClient()
