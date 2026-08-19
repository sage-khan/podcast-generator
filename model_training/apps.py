from django.apps import AppConfig


class ModelTrainingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'model_training'
    verbose_name = 'Model Training'
    
    def ready(self):
        """
        Initialize any app-specific configurations or signal handlers.
        
        This method is called when Django starts up and the app is ready.
        """
        # Import signal handlers to register them
        try:
            import model_training.signals  # noqa
        except ImportError:
            pass