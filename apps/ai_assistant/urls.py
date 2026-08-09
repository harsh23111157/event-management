from django.urls import path

from .views import AiAssistantView

urlpatterns = [
    path("", AiAssistantView.as_view(), name="ai_assistant"),
]
