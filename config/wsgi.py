"""WSGI config for the eventops project."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

_django_app = get_wsgi_application()


def application(environ, start_response):
    # Respond to health checks before Django middleware runs.
    # This avoids ALLOWED_HOSTS 400 errors from Railway's health checker.
    if environ.get("PATH_INFO") == "/health/":
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"OK"]
    return _django_app(environ, start_response)
