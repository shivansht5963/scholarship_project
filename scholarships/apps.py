from django.apps import AppConfig


class ScholarshipsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scholarships'

    def ready(self):
        # Register post_save signal to auto-generate certificates on award approval
        from scholarships.signals import _connect_signals
        _connect_signals()
