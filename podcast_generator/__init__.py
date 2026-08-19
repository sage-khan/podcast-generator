default_app_config = 'podcast_generator.apps.PodcastGeneratorConfig'

# This will make sure the app is always imported when Django starts
# so that shared_task will use this app
from celery import Celery

# Create the celery app
app = Celery('podcast_generator')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs
app.autodiscover_tasks()