"""Локальная разработка: python manage.py runserver"""
from .base import *  # noqa: F401,F403
from .base import env_list

DEBUG = True
SECRET_KEY = SECRET_KEY or "django-insecure-local-dev-only"  # noqa: F405
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")

# В разработке статику отдаёт runserver, манифест не нужен
STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}  # noqa: F405
