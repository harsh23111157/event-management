from django.test import TestCase, override_settings
from apps.ai_assistant.services import OpenRouterService


class OpenRouterServiceTests(TestCase):
    @override_settings(OPENROUTER_API_KEY="")
    def test_safe_fallback_when_api_key_empty(self):
        self.assertFalse(OpenRouterService.is_configured())
        result = OpenRouterService.generate_event_summary({"name": "Test Event"})
        self.assertIn("error", result)
        self.assertIn("not configured", result["error"])
        self.assertEqual(result["text"], "")
        self.assertEqual(result["risk"], "")
