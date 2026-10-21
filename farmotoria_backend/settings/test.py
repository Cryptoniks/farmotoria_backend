"""Настройки для pytest. Если задан DATABASE_URL (как в CI) — тесты идут в PostgreSQL."""
from .base import *  # noqa: F401,F403

DEBUG = False
SECRET_KEY = "test-secret-key-for-pytest-only-0123456789"
ALLOWED_HOSTS = ["testserver", "localhost"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}  # noqa: F405
LOGGING = {"version": 1, "disable_existing_loggers": False}
MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]  # noqa: F405
