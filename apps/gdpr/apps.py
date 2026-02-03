"""GDPR app configuration."""
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class GdprConfig(AppConfig):
    """Configuration for the GDPR app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.gdpr'
    verbose_name = _('GDPR')
