"""
Render-specific settings for Farmotoria backend.
Used when RENDER environment variable is set.
"""
from .settings import *  # noqa: F401, F403
import os

# Render-specific overrides
if os.getenv("RENDER"):
    # Security settings for Render
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # Render provides $PORT
    if os.getenv("PORT"):
        pass  # Gunicorn handles port binding
    
    # Render health check
    MIDDLEWARE.insert(0, 'django.middleware.security.SecurityMiddleware')
    
    # Static files on Render
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
