import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import LoraTrainingJob, TrainedModel, LoraGenerationJob

logger = logging.getLogger(__name__)

@receiver(post_save, sender=LoraTrainingJob)
def handle_lora_training_job_update(sender, instance, created, **kwargs):
    """Handle updates to LoraTrainingJob instances.
    
    This signal is triggered when a LoraTrainingJob is saved.
    If the job status has changed to 'succeeded', it ensures a TrainedModel 
    is created for the trained model.
    """
    # Skip if this is a new job (initial creation)
    if created:
        logger.info(f"New LoraTrainingJob created: {instance.id}")
        return
    
    # Check if status is 'succeeded' and we have a model URL
    if instance.status == 'succeeded' and instance.model_url:
        logger.info(f"LoraTrainingJob {instance.id} succeeded with model URL: {instance.model_url}")
        
        # Check if a TrainedModel already exists for this job
        trained_model = TrainedModel.objects.filter(
            replicate_model_version=instance.replicate_model_version
        ).first()
        
        if not trained_model:
            logger.info(f"Creating new TrainedModel for LoraTrainingJob {instance.id}")
            
            # Create a new TrainedModel
            TrainedModel.objects.create(
                name=instance.model_name,
                model_id=instance.replicate_training_id,
                replicate_owner=instance.replicate_model_owner,
                replicate_model_version=instance.replicate_model_version,
                training_images_urls=instance.training_image_urls,
                status="ready",
                steps=instance.num_training_steps,
                learning_rate=instance.learning_rate,
                training_started_at=instance.created_at,
                training_completed_at=timezone.now()
            )
            
            logger.info(f"TrainedModel created for LoraTrainingJob {instance.id}")
        else:
            logger.info(f"TrainedModel already exists for LoraTrainingJob {instance.id}")
    
    # Log other status changes
    elif instance.status in ['failed', 'canceled']:
        logger.warning(f"LoraTrainingJob {instance.id} {instance.status}. Error: {instance.error_message}")

@receiver(post_save, sender=LoraGenerationJob)
def handle_lora_generation_job_update(sender, instance, created, **kwargs):
    """Handle updates to LoraGenerationJob instances.
    
    This signal is triggered when a LoraGenerationJob is saved.
    Updates timestamps for completed jobs.
    """
    # Skip if this is a new job (initial creation)
    if created:
        logger.info(f"New LoraGenerationJob created: {instance.id}")
        return
    
    # Update completed_at timestamp when job completes
    if instance.status in ['succeeded', 'failed', 'canceled'] and not instance.completed_at:
        instance.completed_at = timezone.now()
        
        # Save without triggering the signal again
        LoraGenerationJob.objects.filter(id=instance.id).update(completed_at=instance.completed_at)
        
        logger.info(f"LoraGenerationJob {instance.id} {instance.status} at {instance.completed_at}")
