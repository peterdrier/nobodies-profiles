"""
Django settings for production.
"""
from .base import *  # noqa: F401, F403

DEBUG = False

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# HTTPS settings (handled by traefik, but set these for completeness)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False  # Traefik handles this
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Use SMTP email backend in production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
