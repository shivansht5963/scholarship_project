from django.apps import AppConfig


class KarmaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'karma'
    
    def ready(self):
        import karma.signals  # Register signals
