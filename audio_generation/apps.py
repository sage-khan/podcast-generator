from django.apps import AppConfig


class AudioGenerationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audio_generation'
    verbose_name = 'Audio Generation'

    def ready(self):
        """
        Import signal handlers when the app is ready
        """
        import audio_generation.signals  # noqa
