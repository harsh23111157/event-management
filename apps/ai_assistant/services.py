"""OpenRouterService — optional AI integration. Fails safely without breaking the app."""
import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class OpenRouterService:
    @staticmethod
    def is_configured() -> bool:
        return bool(getattr(settings, "OPENROUTER_API_KEY", ""))

    @staticmethod
    def _chat(messages: list[dict], timeout: int = 30) -> str:
        api_key = getattr(settings, "OPENROUTER_API_KEY", "")
        if not api_key:
            raise ValueError("OpenRouter API key is not configured.")
        model = getattr(settings, "OPENROUTER_MODEL", "") or "openrouter/auto"
        base_url = getattr(settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": model, "messages": messages}
        resp = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    @staticmethod
    def generate_event_summary(event_data: dict) -> dict:
        """Returns {'text': str, 'risk': 'low'|'medium'|'high', 'error': str|None}."""
        if not OpenRouterService.is_configured():
            return {"text": "", "risk": "", "error": "AI assistant is not configured. Set OPENROUTER_API_KEY."}
        prompt = (
            "You are an event operations assistant. Analyze only the supplied event data. "
            "Do not invent facts, people, costs, dates, vendors, or incidents. "
            "If information is missing, explicitly state that the information is unavailable.\n\n"
            f"Event data:\n{json.dumps(event_data, indent=2, default=str)}\n\n"
            "Provide: 1) A brief operational summary (2-3 sentences). "
            "2) A risk level (low, medium, or high) with one-sentence justification. "
            "3) Any missing items that should be addressed."
        )
        try:
            text = OpenRouterService._chat([{"role": "user", "content": prompt}])
            return {"text": text, "risk": OpenRouterService._extract_risk(text), "error": None}
        except Exception as exc:
            logger.warning("OpenRouter error: %s", exc)
            return {"text": "", "risk": "", "error": f"AI request failed: {exc}"}

    @staticmethod
    def _extract_risk(text: str) -> str:
        low_text = text.lower()
        if "high risk" in low_text or "risk: high" in low_text:
            return "high"
        if "medium risk" in low_text or "risk: medium" in low_text:
            return "medium"
        if "low risk" in low_text or "risk: low" in low_text:
            return "low"
        return "unknown"
