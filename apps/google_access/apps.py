from django.apps import AppConfig


class GoogleAccessConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.google_access'
    verbose_name = 'Google Access Management'

    def ready(self):
        # Import signals when app is ready
        from . import signals  # noqa: F401
