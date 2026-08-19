from django.db import models
import uuid
import logging

logger = logging.getLogger(__name__)


class TrainedModel(models.Model):
    """Model for storing trained LoRA models"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic identifiers
    name = models.CharField(max_length=255)
    model_id = models.CharField(max_length=255, null=True, blank=True)  # Replicate training ID
    trigger_word = models.CharField(max_length=255, null=True, blank=True)
    replicate_owner = models.CharField(max_length=255, default="your-replicate-username")
    replicate_model_name = models.CharField(max_length=255, null=True, blank=True)
    replicate_model_version = models.CharField(max_length=255, null=True, blank=True)  # Increased to 255 from original 100
    
    # URLs
    base_image_url = models.URLField(max_length=1024, null=True, blank=True)
    training_images_urls = models.JSONField(default=list, null=True, blank=True)
    
    # Parameters
    prompt = models.TextField(null=True, blank=True)
    negative_prompt = models.TextField(null=True, blank=True)
    seed = models.IntegerField(null=True, blank=True)
    steps = models.IntegerField(default=1000)
    
    # Training configuration
    lora_rank = models.IntegerField(default=4, help_text="LoRA rank parameter")
    resolution = models.IntegerField(default=512, help_text="Training resolution")
    batch_size = models.IntegerField(default=1, help_text="Training batch size")
    learning_rate = models.FloatField(default=1e-4, help_text="Learning rate")
    
    # Status
    status = models.CharField(max_length=20, default="not_started")
    training_started_at = models.DateTimeField(null=True, blank=True)
    training_completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Trained Model"
        verbose_name_plural = "Trained Models"
        ordering = ['-created_at']

    def __str__(self):
        return f"Model: {self.name}"


class TrainingImage(models.Model):
    """Model for storing images used for training"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(TrainedModel, on_delete=models.CASCADE, related_name='training_images')
    image_url = models.URLField(max_length=1024)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Training Image"
        verbose_name_plural = "Training Images"
        ordering = ['-created_at']

    def __str__(self):
        return f"Training image for {self.model.name}"


class LoraTrainingJob(models.Model):
    """Model for tracking LoRA training jobs"""
    STATUS_CHOICES = [
        ('starting', 'Starting'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic info
    model_name = models.CharField(max_length=255, help_text="Name for the LoRA model")
    replicate_training_id = models.CharField(max_length=255, unique=True, null=True, blank=True, help_text="ID returned by Replicate for the training job")
    replicate_model_version = models.CharField(max_length=255, null=True, blank=True, help_text="Version ID of the trained model")
    replicate_model_owner = models.CharField(max_length=255, default="your-replicate-username")
    
    # Status and webhook info
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='starting')
    webhook_url = models.URLField(max_length=1024, null=True, blank=True)
    webhook_secret = models.CharField(max_length=100, null=True, blank=True)
    webhook_events_filter_used = models.JSONField(default=list, null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    client_webhook_url = models.URLField(max_length=1024, blank=True, null=True, help_text="Client webhook URL for direct callbacks")
    
    # Training parameters
    input_image_urls = models.JSONField(default=list, help_text="List of URLs for training images")
    trigger_word = models.CharField(max_length=255, help_text="Trigger word to use with the trained model")
    seed = models.IntegerField(null=True, blank=True, help_text="Random seed for training")
    steps = models.IntegerField(default=1000, help_text="Number of training steps")
    lora_rank = models.IntegerField(default=4, help_text="LoRA rank parameter")
    
    # Optional parameters
    resolution = models.IntegerField(default=512, help_text="Training resolution")
    batch_size = models.IntegerField(default=1, help_text="Training batch size")
    learning_rate = models.FloatField(default=1e-4, help_text="Learning rate")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "LoRA Training Job"
        verbose_name_plural = "LoRA Training Jobs"

    def __str__(self):
        return f"LoRA Training: {self.model_name} (ID: {self.replicate_training_id or 'N/A'})"