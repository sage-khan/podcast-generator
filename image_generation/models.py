from django.db import models
import uuid
import logging

logger = logging.getLogger(__name__)


class Character(models.Model):
    """Model for storing generated characters and their parameters"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core Info
    prompt = models.TextField()
    negative_prompt = models.TextField(blank=True, null=True)
    image_url = models.URLField(max_length=1024) # Increased max_length just in case
    replicate_url = models.URLField(max_length=1024, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Status and webhook information
    status = models.CharField(max_length=20, choices=[
        ('starting', 'Starting'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
    ], default='starting')
    replicate_prediction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    webhook_url = models.URLField(max_length=1024, null=True, blank=True)
    webhook_secret = models.CharField(max_length=100, null=True, blank=True)
    webhook_events_filter_used = models.JSONField(default=list, null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    client_webhook_url = models.URLField(blank=True, null=True, help_text="Client webhook URL for direct callbacks")
    
    # Generation Hyperparameters (Allow Null/Blank for flexibility)
    seed = models.IntegerField(null=True, blank=True)
    aspect_ratio = models.CharField(max_length=10, null=True, blank=True)
    image_prompt = models.URLField(max_length=1024, null=True, blank=True) # URL for image prompt used
    output_format = models.CharField(max_length=10, null=True, blank=True)
    output_quality = models.IntegerField(null=True, blank=True)
    safety_tolerance = models.IntegerField(null=True, blank=True)
    image_prompt_strength = models.FloatField(null=True, blank=True)
    raw = models.BooleanField(null=True, blank=True)
    num_inference_steps = models.IntegerField(null=True, blank=True, default=30, help_text="Number of denoising steps for generation")
    guidance_scale = models.FloatField(null=True, blank=True, default=7.5, help_text="Classifier-free guidance scale")
    
    # Output URLs (for batch generation)
    output_urls = models.JSONField(default=list, null=True, blank=True)
    
    class Meta:
        verbose_name = "Character"
        verbose_name_plural = "Characters"
        ordering = ['-created_at']

    def __str__(self):
        return f"Character {self.id}: {self.prompt[:50]}"


class Pose(models.Model):
    """Model for storing character poses"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='poses')
    image_url = models.URLField(max_length=1024)
    replicate_url = models.URLField(max_length=1024, blank=True, null=True, help_text="URL to the image on Replicate's delivery server")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Pose parameters
    pose_prompt = models.TextField(blank=True, null=True, help_text="The specific prompt used for this pose")
    pose_type = models.CharField(max_length=50, blank=True, null=True, help_text="Type of pose (e.g., sitting, standing)")
    
    # Status and webhook information
    status = models.CharField(max_length=20, choices=[
        ('starting', 'Starting'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
    ], default='starting')
    replicate_prediction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    webhook_url = models.URLField(max_length=1024, null=True, blank=True)
    webhook_secret = models.CharField(max_length=100, null=True, blank=True)
    webhook_events_filter_used = models.JSONField(default=list, null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    client_webhook_url = models.URLField(blank=True, null=True, help_text="Client webhook URL for direct callbacks")
    
    # Output URLs (for batch generation)
    output_urls = models.JSONField(default=list, null=True, blank=True)
    
    class Meta:
        verbose_name = "Pose"
        verbose_name_plural = "Poses"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Pose {self.id} for Character {self.character.id}"

class LoraGenerationJob(models.Model):
    """Model for handling LoRA model image generation jobs"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core Info
    model_id = models.CharField(max_length=255, help_text="Replicate LoRA model ID in format owner/name:version")
    prompt = models.TextField()
    negative_prompt = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Status and webhook information
    status = models.CharField(max_length=20, choices=[
        ('queued', 'Queued'),
        ('starting', 'Starting'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
    ], default='queued')
    replicate_prediction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    webhook_url = models.URLField(max_length=1024, null=True, blank=True)
    webhook_secret = models.CharField(max_length=100, null=True, blank=True)
    webhook_events_filter = models.JSONField(default=list, null=True, blank=True, help_text="List of events to trigger webhook for (e.g., ['start', 'output', 'completed'])")
    webhook_events_filter_used = models.JSONField(default=list, null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    client_webhook_url = models.URLField(blank=True, null=True, help_text="Client webhook URL for direct callbacks")
    
    # Generation Parameters
    num_outputs = models.IntegerField(default=4, help_text="Number of images to generate")
    seed = models.IntegerField(null=True, blank=True)
    go_fast = models.BooleanField(default=False, help_text="Enable faster but lower quality generation")
    lora_scale = models.FloatField(default=1.0, help_text="Strength of the LoRA effect")
    megapixels = models.CharField(max_length=10, default="1", help_text="Approximate resolution scale")
    aspect_ratio = models.CharField(max_length=10, default="1:1", help_text="Aspect ratio of the generated images")
    output_format = models.CharField(max_length=10, default="webp", help_text="Output image format")
    guidance_scale = models.FloatField(default=3.0, help_text="Classifier-free guidance strength")
    output_quality = models.IntegerField(default=80, help_text="Output image quality (0-100)")
    prompt_strength = models.FloatField(default=0.8, help_text="Influence of the prompt on the result")
    extra_lora_scale = models.FloatField(default=1.0, null=True, blank=True, help_text="Additional scaling for LoRA weights")
    num_inference_steps = models.IntegerField(default=28, help_text="Number of denoising steps")
    
    # Optional custom dimensions for "custom" aspect_ratio
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    
    # Output URLs
    output_urls = models.JSONField(default=list, null=True, blank=True)
    
    class Meta:
        verbose_name = "LoRA Generation Job"
        verbose_name_plural = "LoRA Generation Jobs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"LoRA Generation {self.id}: {self.prompt[:50]}"


class FluxUltraProJob(models.Model):
    """Model for Flux-1.1-pro-ultra image generation jobs"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core Info
    prompt = models.TextField()
    negative_prompt = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Status and webhook information
    status = models.CharField(max_length=20, choices=[
        ('starting', 'Starting'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
    ], default='starting')
    replicate_prediction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    webhook_url = models.URLField(max_length=1024, null=True, blank=True)
    webhook_secret = models.CharField(max_length=100, null=True, blank=True)
    webhook_events_filter = models.JSONField(default=list, null=True, blank=True, help_text="List of events to trigger webhook for (e.g., ['start', 'output', 'completed'])")
    webhook_events_filter_used = models.JSONField(default=list, null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    client_webhook_url = models.URLField(blank=True, null=True, help_text="Client webhook URL for direct callbacks")
    
    # Generation Parameters (based on Flux-1.1-pro-ultra docs)
    seed = models.IntegerField(null=True, blank=True, help_text="Random seed for reproducible generation")
    aspect_ratio = models.CharField(max_length=10, default="1:1", help_text="Aspect ratio of the generated image")
    image_prompt = models.URLField(max_length=1024, null=True, blank=True, help_text="URL for image prompt used")
    output_format = models.CharField(max_length=10, default="jpg", help_text="Output image format")
    safety_tolerance = models.IntegerField(default=2, help_text="Safety tolerance, 0 is most strict and 6 is most permissive")
    image_prompt_strength = models.FloatField(default=0.1, null=True, blank=True, help_text="Influence of the image prompt on the result")
    raw = models.BooleanField(default=False, help_text="Toggle raw mode for more natural, less synthetic aesthetics")
    
    # Output URLs
    output_urls = models.JSONField(default=list, null=True, blank=True)
    
    class Meta:
        verbose_name = "Flux Ultra Pro Job"
        verbose_name_plural = "Flux Ultra Pro Jobs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Flux Ultra Pro Job {self.id}: {self.prompt[:50]}"


class FluxKontextProJob(models.Model):
    """Model for Flux Kontext Pro image editing jobs"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core Info
    prompt = models.TextField(help_text="Text description of what you want to generate, or the instruction on how to edit the given image")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Status and webhook information
    status = models.CharField(max_length=20, choices=[
        ('starting', 'Starting'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
    ], default='starting')
    replicate_prediction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    webhook_url = models.URLField(max_length=1024, null=True, blank=True)
    webhook_secret = models.CharField(max_length=100, null=True, blank=True)
    webhook_events_filter = models.JSONField(default=list, null=True, blank=True, help_text="List of events to trigger webhook for (e.g., ['start', 'output', 'completed'])")
    webhook_events_filter_used = models.JSONField(default=list, null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    client_webhook_url = models.URLField(blank=True, null=True, help_text="Client webhook URL for direct callbacks")
    
    # Generation Parameters (based on Flux Kontext Pro docs)
    seed = models.IntegerField(null=True, blank=True, help_text="Random seed for reproducible generation")
    input_image = models.URLField(max_length=1024, help_text="Image to use as reference. Must be jpeg, png, gif, or webp")
    aspect_ratio = models.CharField(max_length=20, default="match_input_image", help_text="Aspect ratio of the generated image")
    output_format = models.CharField(max_length=10, default="png", help_text="Output format for the generated image")
    safety_tolerance = models.IntegerField(default=2, help_text="Safety tolerance, 0 is most strict and 6 is most permissive")
    
    # Output URLs
    output_url = models.URLField(max_length=1024, null=True, blank=True)
    
    class Meta:
        verbose_name = "Flux Kontext Pro Job"
        verbose_name_plural = "Flux Kontext Pro Jobs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Flux Kontext Pro Job {self.id}: {self.prompt[:50]}"


class FluxKontextMultiJob(models.Model):
    """Model for Flux Kontext Multi-image editing jobs"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core Info
    prompt = models.TextField(help_text="Text description of how to combine or transform the two input images")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Status and webhook information
    status = models.CharField(max_length=20, choices=[
        ('starting', 'Starting'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
    ], default='starting')
    replicate_prediction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    webhook_url = models.URLField(max_length=1024, null=True, blank=True)
    webhook_secret = models.CharField(max_length=100, null=True, blank=True)
    webhook_events_filter = models.JSONField(default=list, null=True, blank=True, help_text="List of events to trigger webhook for (e.g., ['start', 'output', 'completed'])")
    webhook_events_filter_used = models.JSONField(default=list, null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    client_webhook_url = models.URLField(blank=True, null=True, help_text="Client webhook URL for direct callbacks")
    
    # Generation Parameters (based on Flux Kontext Multi docs)
    seed = models.IntegerField(null=True, blank=True, help_text="Random seed for reproducible generation")
    input_image_1 = models.URLField(max_length=1024, help_text="First input image. Must be jpeg, png, gif, or webp")
    input_image_2 = models.URLField(max_length=1024, help_text="Second input image. Must be jpeg, png, gif, or webp")
    aspect_ratio = models.CharField(max_length=20, default="match_input_image", help_text="Aspect ratio of the generated image")
    output_format = models.CharField(max_length=10, default="png", help_text="Output format for the generated image")
    safety_tolerance = models.IntegerField(default=2, help_text="Safety tolerance, 0 is most strict and 2 is most permissive")
    
    # Output URLs
    output_url = models.URLField(max_length=1024, null=True, blank=True)
    
    class Meta:
        verbose_name = "Flux Kontext Multi-Image Job"
        verbose_name_plural = "Flux Kontext Multi-Image Jobs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Flux Kontext Multi Job {self.id}: {self.prompt[:50]}"


class FluxKontextMultiListJob(models.Model):
    """Model for Flux Kontext Multi-image-list editing jobs"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core Info
    prompt = models.TextField(help_text="Text description of how to combine or transform the input images")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Status and webhook information
    status = models.CharField(max_length=20, choices=[
        ('starting', 'Starting'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
    ], default='starting')
    replicate_prediction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    webhook_url = models.URLField(max_length=1024, null=True, blank=True)
    webhook_secret = models.CharField(max_length=100, null=True, blank=True)
    webhook_events_filter = models.JSONField(default=list, null=True, blank=True, help_text="List of events to trigger webhook for (e.g., ['start', 'output', 'completed'])")
    webhook_events_filter_used = models.JSONField(default=list, null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    client_webhook_url = models.URLField(blank=True, null=True, help_text="Client webhook URL for direct callbacks")
    
    # Generation Parameters (based on Flux Kontext Multi-image-list docs)
    seed = models.IntegerField(null=True, blank=True, help_text="Random seed for reproducible generation")
    input_images = models.JSONField(default=list, help_text="List of input images. Must be jpeg, png, gif, or webp.")
    aspect_ratio = models.CharField(max_length=20, default="match_input_image", help_text="Aspect ratio of the generated image")
    output_format = models.CharField(max_length=10, default="png", help_text="Output format for the generated image")
    safety_tolerance = models.IntegerField(default=2, help_text="Safety tolerance, 0 is most strict and 2 is most permissive")
    
    # Output URLs
    output_url = models.URLField(max_length=1024, null=True, blank=True)
    
    class Meta:
        verbose_name = "Flux Kontext Multi-Image List Job"
        verbose_name_plural = "Flux Kontext Multi-Image List Jobs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Flux Kontext Multi-Image List Job {self.id}: {self.prompt[:50]}"


class FluxKontextPortraitSeriesJob(models.Model):
    """Model for Flux Kontext Portrait-Series jobs"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core Info
    input_image = models.URLField(max_length=1024, help_text="Image of the person to create a series of photos for")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Status and webhook information
    status = models.CharField(max_length=20, choices=[
        ('starting', 'Starting'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled')
    ], default='starting')
    replicate_id = models.CharField(max_length=255, blank=True, null=True)
    replicate_url = models.URLField(max_length=1024, blank=True, null=True)
    webhook_secret = models.CharField(max_length=64, blank=True, null=True)
    webhook_events_filter = models.JSONField(default=list, null=True, blank=True)
    webhook_events_filter_used = models.JSONField(default=list, null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    client_webhook_url = models.URLField(blank=True, null=True, help_text="Client webhook URL for direct callbacks")
    
    # Portrait-series specific parameters
    background = models.CharField(max_length=50, default="white", help_text="The background of the photo")
    num_images = models.IntegerField(default=4, help_text="The number of poses to generate")
    randomize_images = models.BooleanField(default=False, help_text="Whether to randomize the poses")
    output_format = models.CharField(max_length=10, default="png", help_text="Output format for the generated image")
    safety_tolerance = models.IntegerField(default=2, help_text="Safety tolerance, 0 is most strict and 2 is most permissive")
    
    # Output URLs - using JSONField since we expect a list of URLs
    output_urls = models.JSONField(default=list, null=True, blank=True)
    
    class Meta:
        verbose_name = "Flux Kontext Portrait-Series Job"
        verbose_name_plural = "Flux Kontext Portrait-Series Jobs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Flux Kontext Portrait-Series Job {self.id}"