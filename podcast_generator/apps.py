from django.apps import AppConfig


class PodcastGeneratorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'podcast_generator'
    verbose_name = 'Podcast Generator'
    
    def ready(self):
        """
        Import signals or perform other initialization when the app is ready.
        """
        # Import signals or perform other initialization here if needed
        pass