from django.apps import AppConfig


class VideoGenerationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'video_generation'
    verbose_name = 'Video Generation'

    def ready(self):
        """
        Import signal handlers when the app is ready
        """
        import video_generation.signals  # noqa
