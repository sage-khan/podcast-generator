import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Character, Pose

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Character)
def handle_character_update(sender, instance, created, **kwargs):
    """Handle updates to Character instances.
    
    This signal is triggered when a Character is saved.
    Updates related fields and logs state transitions.
    """
    # Skip if this is a new character (initial creation)
    if created:
        logger.info(f"New Character created: {instance.id}")
        return
    
    # Update related poses when the character status changes to 'failed'
    if instance.status == 'failed':
        logger.warning(f"Character {instance.id} failed. Error: {instance.error_message}")
        
        # Fail any poses that depend on this character
        poses = Pose.objects.filter(character=instance, status__in=['starting', 'processing'])
        if poses.exists():
            poses.update(
                status='failed',
                error_message=f"Parent character generation failed: {instance.error_message or 'Unknown error'}"
            )
            logger.info(f"Updated {poses.count()} dependent poses to failed status")

@receiver(post_save, sender=Pose)
def handle_pose_update(sender, instance, created, **kwargs):
    """Handle updates to Pose instances.
    
    This signal is triggered when a Pose is saved.
    Logs state transitions and ensures appropriate data handling.
    """
    # Skip if this is a new pose (initial creation)
    if created:
        logger.info(f"New Pose created: {instance.id} for Character {instance.character.id}")
        return
    
    # Process successful pose generations
    if instance.status == 'succeeded' and instance.output_urls:
        # If we have multiple poses generated but no specific image_url set,
        # use the first output URL as the primary image URL
        if not instance.image_url and instance.output_urls:
            try:
                instance.image_url = instance.output_urls[0]
                # Save without triggering the signal again
                Pose.objects.filter(id=instance.id).update(image_url=instance.image_url)
                logger.info(f"Set primary image URL for Pose {instance.id}")
            except (IndexError, TypeError):
                logger.warning(f"Failed to set primary image URL for Pose {instance.id}")
    
    # Log failures
    elif instance.status == 'failed':
        logger.warning(f"Pose {instance.id} failed. Error: {instance.error_message}")
