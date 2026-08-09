import json
import logging
import re

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
    def generate_event_summary(event_data: dict, role: str = "ADMIN") -> dict:
        """Returns structured dict with executive_summary, risk_level, risk_justification, parsed_action_items, text, summary, risk, error."""
        if not OpenRouterService.is_configured():
            return {
                "text": "",
                "summary": "",
                "risk": "",
                "risk_level": "",
                "risk_justification": "",
                "executive_summary": "",
                "action_items": [],
                "parsed_action_items": [],
                "error": "AI assistant is not configured. Set OPENROUTER_API_KEY in .env.",
            }
        role_instruction = {
            "FINANCE": "Focus your analysis strictly on budget health, expense distribution, and vendor cost risks.",
            "STAFF": "Focus your analysis strictly on task operational execution, timeline risks, and readiness.",
            "EVENT_MANAGER": "Focus your analysis on overall event planning, venue capacity, task completion, and milestones.",
            "ADMIN": "Provide a holistic executive operational and governance analysis.",
        }.get(role, "Provide an operational analysis.")

        prompt = (
            f"You are an event operations AI advisor. {role_instruction}\n"
            "Analyze only the supplied event data. Do not invent facts, numbers, dates, or vendors.\n"
            "If information is missing, explicitly state that it is not yet recorded.\n\n"
            f"Event data:\n{json.dumps(event_data, indent=2, default=str)}\n\n"
            "Structure your response strictly into these 3 sections with clear headings:\n\n"
            "**1) Executive Summary**\n"
            "Write 2-3 concise, impactful sentences summarizing key operational status and governance observations.\n\n"
            "**2) Risk Level: [Low | Medium | High]**\n"
            "Provide a one-sentence clear justification explaining why this risk level was assigned.\n\n"
            "**3) Actionable Next Steps / Missing Items**\n"
            "Provide 3-6 clear, high-priority bullet points. Format each bullet point as:\n"
            "- Action Title: Brief description of specific task or reconciliation required."
        )
        try:
            text = OpenRouterService._chat([{"role": "user", "content": prompt}])
            parsed = OpenRouterService._parse_sections(text)
            return {
                "text": text,
                "summary": parsed["executive_summary"] or text,
                "executive_summary": parsed["executive_summary"],
                "risk": parsed["risk_level"],
                "risk_level": parsed["risk_level"],
                "risk_justification": parsed["risk_justification"],
                "action_items": parsed["action_items"],
                "parsed_action_items": parsed["parsed_action_items"],
                "error": None,
            }
        except Exception as exc:
            logger.warning("OpenRouter error: %s", exc)
            return {
                "text": "",
                "summary": "",
                "risk": "",
                "risk_level": "",
                "risk_justification": "",
                "executive_summary": "",
                "action_items": [],
                "parsed_action_items": [],
                "error": f"AI request failed: {exc}",
            }

    @staticmethod
    def _parse_sections(text: str) -> dict:
        res = {
            "executive_summary": "",
            "risk_level": "unknown",
            "risk_justification": "",
            "action_items": [],
            "parsed_action_items": [],
        }
        if not text:
            return res

        # Extract risk level
        low_text = text.lower()
        if any(k in low_text for k in ["high risk", "risk: high", "risk level: high", "risk level:** high", "risk level - high"]):
            res["risk_level"] = "high"
        elif any(k in low_text for k in ["medium risk", "risk: medium", "risk level: medium", "risk level:** medium", "risk level - medium"]):
            res["risk_level"] = "medium"
        elif any(k in low_text for k in ["low risk", "risk: low", "risk level: low", "risk level:** low", "risk level - low"]):
            res["risk_level"] = "low"

        # Regex search for sections
        s1 = re.search(
            r"(?:(?:\*\*|###?|##)?\s*(?:1[\.\)]\s*)?Executive Summary[^\n\*\#]*[\*\#]*\s*:?)([\s\S]*?)(?=(?:(?:\*\*|###?|##)?\s*(?:2[\.\)]\s*)?Risk Level)|$)",
            text,
            re.I,
        )
        s2 = re.search(
            r"(?:(?:\*\*|###?|##)?\s*(?:2[\.\)]\s*)?Risk Level[^\n\*\#]*[\*\#]*\s*:?)([\s\S]*?)(?=(?:(?:\*\*|###?|##)?\s*(?:3[\.\)]\s*)?Actionable Next Steps)|$)",
            text,
            re.I,
        )
        s3 = re.search(
            r"(?:(?:\*\*|###?|##)?\s*(?:3[\.\)]\s*)?Actionable Next Steps[^\n\*\#]*[\*\#]*\s*:?)([\s\S]*)$",
            text,
            re.I,
        )

        if s1:
            res["executive_summary"] = s1.group(1).strip().replace("**", "")
        if s2:
            just = s2.group(1).strip()
            # Clean up leading 'Low', 'Medium', 'High', 'Unknown', colons, dashes, asterisks
            just = re.sub(r"^(?:\*\*)?(?:Low|Medium|High|Unknown)(?:\*\*)?[\s:\-\.]*", "", just, flags=re.I).strip().replace("**", "")
            res["risk_justification"] = just
        if s3:
            raw_actions = s3.group(1).strip()
            lines = raw_actions.split("\n")
            curr_item = []
            for line in lines:
                line_str = line.strip()
                if not line_str:
                    continue
                if re.match(r"^(?:[-*•]|\d+[\.\)])\s+", line_str):
                    if curr_item:
                        res["action_items"].append(" ".join(curr_item))
                    item_content = re.sub(r"^(?:[-*•]|\d+[\.\)])\s+", "", line_str)
                    curr_item = [item_content]
                else:
                    if curr_item:
                        curr_item.append(line_str)
                    else:
                        curr_item = [line_str]
            if curr_item:
                res["action_items"].append(" ".join(curr_item))

        # Format action items into title / description if colon exists
        formatted_actions = []
        for item in res["action_items"]:
            cleaned = item.replace("**", "").strip()
            if ":" in cleaned:
                parts = cleaned.split(":", 1)
                formatted_actions.append({"title": parts[0].strip(), "detail": parts[1].strip()})
            else:
                formatted_actions.append({"title": "", "detail": cleaned})
        res["parsed_action_items"] = formatted_actions

        # Fallback if no sections were matched (e.g. general plain text)
        if not res["executive_summary"] and not res["action_items"]:
            res["executive_summary"] = text.strip()

        return res

    @staticmethod
    def _extract_risk(text: str) -> str:
        return OpenRouterService._parse_sections(text)["risk_level"]

