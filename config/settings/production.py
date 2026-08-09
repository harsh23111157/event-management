"""Production settings."""
import environ
from .base import *  # noqa: F401,F403

env = environ.Env()

# CSRF — supports Railway domains and custom origins
_custom_csrf = env.list("CSRF_TRUSTED_ORIGINS", default=[])
for c in _custom_csrf:
    if c not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(c)

if "https://*.up.railway.app" not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append("https://*.up.railway.app")

# Security hardening
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
