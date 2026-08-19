"""Task modules for background processing in the AI image generation and fine-tuning project."""

# Import key tasks for easier access
from shared.tasks.image_generation_tasks import (
    generate_character_task,
    handle_character_webhook,
    generate_poses_task,
    handle_pose_webhook,
)

from shared.tasks.lora_training_tasks import (
    start_lora_training,
    handle_lora_training_webhook,
)

# Export these tasks directly
__all__ = [
    'generate_character_task',
    'handle_character_webhook',
    'generate_poses_task',
    'handle_pose_webhook',
    'start_lora_training',
    'handle_lora_training_webhook',
]