from django.apps import AppConfig


class ApplicationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.applications'
    verbose_name = 'Applications'

    def ready(self):
        # Import signals when app is ready
        from . import signals  # noqa: F401
