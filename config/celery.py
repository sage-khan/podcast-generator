import os
import time
from celery import Celery
from celery.signals import task_failure, task_success, task_retry
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create the Celery app
app = Celery('ai_image_gen')

# Using a string for namespace means all celery-related configuration keys
# should have a `CELERY_` prefix in settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Set a higher retry limit and backoff for tasks in containerized environments
# This helps with network stability issues between containers
app.conf.update(
    task_default_retry_delay=5,  # 5 seconds
    task_max_retries=5,          # Retry up to 5 times
    task_time_limit=600,         # 10 minutes max runtime
    task_soft_time_limit=540,    # Warn at 9 minutes
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    # Timeout settings for Redis
    broker_transport_options={
        'visibility_timeout': 3600,  # 1 hour
        'max_connections': 100,
        'socket_timeout': 5,
        'socket_connect_timeout': 5,
    },
    # Result backend settings
    result_backend_transport_options={
        'socket_timeout': 5,
        'retry_policy': {
            'max_retries': 3,
            'interval_start': 0.5,
            'interval_step': 0.5,
            'interval_max': 3,
        },
    },
    worker_prefetch_multiplier=1,  # Fetch one task at a time
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (prevent memory leaks)
    worker_concurrency=3,  # Limit concurrent tasks per worker
)

# Scheduled periodic tasks
app.conf.beat_schedule = {
    'check-pending-lora-jobs': {
        'task': 'model_training.tasks.check_pending_lora_jobs',
        'schedule': crontab(minute='*/10'),  # Run every 10 minutes
    },
}

# Load tasks from all registered apps
app.autodiscover_tasks()

@task_success.connect
def task_success_handler(sender=None, **kwargs):
    """Log when tasks succeed."""
    task_id = kwargs.get('task_id')
    task_name = sender.name if sender else 'unknown'
    print(f"Task {task_name} [{task_id}] succeeded")

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, **kwargs):
    """Log when tasks fail."""
    task_name = sender.name if sender else 'unknown'
    print(f"Task {task_name} [{task_id}] failed: {exception}")

@task_retry.connect
def task_retry_handler(sender=None, request=None, reason=None, **kwargs):
    """Log when tasks are retried."""
    task_id = request.id if request else 'unknown'
    task_name = sender.name if sender else 'unknown'
    print(f"Task {task_name} [{task_id}] being retried: {reason}")

# Define a custom method to send tasks with more reliability
# This is especially useful in Docker environments where connections can be flaky
def send_task_reliable(task_name, args=None, kwargs=None, countdown=5, **options):
    """Send a task with added reliability features.
    
    Args:
        task_name: Full task path (e.g., 'app.tasks.my_task')
        args: Positional arguments for the task
        kwargs: Keyword arguments for the task
        countdown: Delay in seconds before task execution (helps with network stability)
        **options: Additional options to pass to send_task
        
    Returns:
        AsyncResult object with the task result
    """
    args = args or []
    kwargs = kwargs or {}
    
    # Add a small delay for connection stability
    # This helps ensure network connections are established before task runs
    if 'countdown' not in options:
        options['countdown'] = countdown
    
    # Use the full task path for better reliability
    return app.send_task(task_name, args=args, kwargs=kwargs, **options)
