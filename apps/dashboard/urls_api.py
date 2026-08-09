from django.urls import path
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import DashboardService


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(DashboardService.full_context())


urlpatterns = [
    path("dashboard/", DashboardAPIView.as_view(), name="api_dashboard"),
]
