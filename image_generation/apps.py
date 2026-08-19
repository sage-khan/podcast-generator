from django.apps import AppConfig


class ImageGenerationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'image_generation'
    verbose_name = 'Image Generation'
    
    def ready(self):
        """
        Initialize any app-specific configurations or signal handlers.
        
        This method is called when Django starts up and the app is ready.
        """
        # Import signal handlers to register them
        try:
            import image_generation.signals  # noqa
        except ImportError:
            pass