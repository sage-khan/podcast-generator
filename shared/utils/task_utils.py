import logging
import os
from typing import Optional, List, Dict, Any, Union, Callable
from functools import wraps
import time

logger = logging.getLogger(__name__)

def get_celery_app():
    """
    Get the Celery app instance, importing lazily to avoid circular imports
    
    Returns:
        CeleryApp: The Celery app instance
    """
    try:
        # Import the app from the new modular structure
        from config.celery import app
        return app
    except ImportError as e:
        # Fallback to the old structure for backward compatibility
        try:
            from django_character_ai.celery_app_config import app
            logger.warning("Using deprecated celery app import path. Update references to use 'config.celery'")
            return app
        except ImportError:
            logger.error(f"Failed to import Celery app: {str(e)}")
            raise


def queue_task(
    task_path: str, 
    args: Optional[List] = None, 
    kwargs: Optional[Dict[str, Any]] = None, 
    countdown: int = 5,
    queue: Optional[str] = None,
    retry: bool = True,
    max_retries: int = 3,
    retry_backoff: bool = True
) -> str:
    """
    Queue a Celery task with reliable execution in Docker environments
    
    Args:
        task_path: Full path to the task (e.g., 'app.tasks.my_task')
        args: Positional arguments to pass to the task
        kwargs: Keyword arguments to pass to the task
        countdown: Delay in seconds before task execution
        queue: Optional queue name
        retry: Whether to retry the task on failure
        max_retries: Maximum number of retries
        retry_backoff: Whether to use exponential backoff for retries
        
    Returns:
        str: Task ID
    """
    try:
        app = get_celery_app()
        
        # Use send_task with full path for better reliability in Docker
        result = app.send_task(
            task_path,
            args=args or [],
            kwargs=kwargs or {},
            countdown=countdown,  # Small delay for connection stability
            queue=queue,
            retry=retry,
            retry_policy={
                'max_retries': max_retries,
                'interval_start': 0,
                'interval_step': 1 if retry_backoff else 0,
                'interval_max': 5 if retry_backoff else 0,
            }
        )
        
        logger.info(f"Task {task_path} queued with ID: {result.id}")
        return result.id
    
    except Exception as e:
        logger.error(f"Error queueing task {task_path}: {str(e)}")
        raise


def with_task_logging(func: Callable) -> Callable:
    """
    Decorator to add standardized logging to Celery tasks
    
    Args:
        func: The task function to decorate
        
    Returns:
        Callable: Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        task_name = func.__name__
        task_id = kwargs.get('task_id', 'unknown')
        
        # Get actual task ID from current task if available
        try:
            from celery import current_task
            if current_task and current_task.request and current_task.request.id:
                task_id = current_task.request.id
        except ImportError:
            pass
        
        start_time = time.time()
        logger.info(f"Starting task {task_name} [{task_id}]")
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Task {task_name} [{task_id}] completed in {execution_time:.2f}s")
            return result
        
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Task {task_name} [{task_id}] failed after {execution_time:.2f}s: {str(e)}")
            raise
    
    return wrapper


def create_celery_task(app, task_path: str, **task_options):
    """
    Create a Celery task with better defaults for reliability
    
    Args:
        app: Celery app instance
        task_path: Full path to the task
        **task_options: Additional options for the task
        
    Returns:
        Decorator: Celery task decorator
    """
    # Set sensible defaults
    default_options = {
        'bind': True,  # Bind task to get access to task instance
        'retry_backoff': True,  # Use exponential backoff
        'retry_backoff_max': 600,  # Maximum backoff of 10 minutes
        'max_retries': 5,  # Maximum of 5 retries
        'default_retry_delay': 5,  # 5 second initial delay
        'rate_limit': '10/m',  # Limit to 10 per minute
        'ignore_result': False,  # Store results for tracking
    }
    
    # Merge with user options (user options take precedence)
    options = {**default_options, **task_options}
    
    def decorator(func):
        # Add task logging
        @with_task_logging
        # Add Celery task decorator
        @app.task(**options)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator
