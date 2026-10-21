"""Продакшен: Render (бэкенд) + Neon (PostgreSQL) + Vercel (фронтенд)."""
import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import env_bool

DEBUG = env_bool("DEBUG", False)

if not SECRET_KEY:  # noqa: F405
    raise ImproperlyConfigured("Не задана переменная окружения SECRET_KEY")
if not DATABASE_URL:  # noqa: F405
    raise ImproperlyConfigured("Не задана переменная окружения DATABASE_URL (строка подключения Neon)")

# Render сам выставляет RENDER_EXTERNAL_HOSTNAME (например farmotoria-api.onrender.com)
render_host = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if render_host and render_host not in ALLOWED_HOSTS:  # noqa: F405
    ALLOWED_HOSTS.append(render_host)  # noqa: F405
    CSRF_TRUSTED_ORIGINS.append(f"https://{render_host}")  # noqa: F405

# HTTPS терминируется на прокси Render
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SECURE_REDIRECT_EXEMPT = [r"^api/farmotoria/ping/$"]  # health check Render ходит по http
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
