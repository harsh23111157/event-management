"""Root URL configuration."""
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.views.generic.base import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def health_check(request):
    return HttpResponse("OK", content_type="text/plain", status=200)

urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("", RedirectView.as_view(url="/dashboard/", permanent=False), name="home"),
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.urls_api")),
    path("api/v1/", include("apps.events.urls_api")),
    path("api/v1/", include("apps.venues.urls_api")),
    path("api/v1/", include("apps.operations.urls_api")),
    path("api/v1/", include("apps.vendors.urls_api")),
    path("api/v1/", include("apps.finance.urls_api")),
    path("api/v1/", include("apps.reports.urls_api")),
    path("api/v1/", include("apps.dashboard.urls_api")),
    path("api/v1/", include("apps.ai_assistant.urls_api")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="api-docs"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc-short"),
    path("", include("apps.accounts.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("events/", include("apps.events.urls")),
    path("venues/", include("apps.venues.urls")),
    path("operations/", include("apps.operations.urls")),
    path("vendors/", include("apps.vendors.urls")),
    path("expenses/", include("apps.finance.urls")),
    path("reports/", include("apps.reports.urls")),
    path("audit-logs/", include("apps.audit.urls")),
    path("ai/", include("apps.ai_assistant.urls")),
    path("assistant/", RedirectView.as_view(url="/ai/", permanent=False)),
    path("workflow/", RedirectView.as_view(url="/dashboard/workflow/", permanent=False)),
    path("how-it-works/", RedirectView.as_view(url="/dashboard/workflow/", permanent=False)),
]

handler400 = "apps.accounts.views.handler400"
handler403 = "apps.accounts.views.handler403"
handler404 = "apps.accounts.views.handler404"
handler500 = "apps.accounts.views.handler500"
