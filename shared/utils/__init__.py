"""
Shared utilities for the application.
"""

from shared.utils.webhook_utils import (
    generate_webhook_secret,
    generate_webhook_url,
    validate_webhook_secret,
    process_replicate_webhook,
    send_client_webhook
)

from shared.utils.model_validation import (
    parse_replicate_model_id,
    format_for_replicate_run,
    prepare_for_replicate_predictions_create,
    validate_webhook_url,
    verify_model_exists,
    validate_replicate_model_version_field,
    generate_payload_for_replicate
)

from shared.utils.task_utils import (
    get_celery_app,
    queue_task,
    with_task_logging,
    create_celery_task
)

# Import ModelManager if present
try:
    from shared.utils.model_manager import ModelManager
except ImportError:
    pass

# Media utilities (video/audio concatenation)
try:
    from shared.utils.media_utils import merge_videos, merge_audios
except ImportError:
    pass

__all__ = [
    # Webhook utilities
    'generate_webhook_secret',
    'generate_webhook_url',
    'validate_webhook_secret',
    'process_replicate_webhook',
    'send_client_webhook',
    
    # Model validation
    'parse_replicate_model_id',
    'format_for_replicate_run',
    'prepare_for_replicate_predictions_create',
    'validate_webhook_url',
    'verify_model_exists',
    'validate_replicate_model_version_field',
    'generate_payload_for_replicate',
    
    # Task utilities
    'get_celery_app',
    'queue_task',
    'with_task_logging',
    'create_celery_task',
    
    # Model manager
    'ModelManager',
    
    # Media utilities
    'merge_videos',
    'merge_audios',
]