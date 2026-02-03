"""
Django settings for local development.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

# Extend ALLOWED_HOSTS from base.py (reads from DJANGO_ALLOWED_HOSTS env var)
ALLOWED_HOSTS += ['0.0.0.0']  # noqa: F405

# Debug toolbar
INSTALLED_APPS += ['debug_toolbar']  # noqa: F405
MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')  # noqa: F405
INTERNAL_IPS = ['127.0.0.1']

# Use console email backend in development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable whitenoise manifest storage in development
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Trust X-Forwarded-Proto from traefik (so Django knows it's HTTPS)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
