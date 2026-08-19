import uuid
from django.db import models
from django.utils import timezone


class MinimaxVoiceCloneJob(models.Model):
    """
    Model for storing Minimax voice cloning job information
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    voice_file = models.URLField(max_length=1000, help_text="URL to the reference audio for voice cloning")
    model = models.CharField(max_length=50, default="speech-02-turbo", help_text="The text-to-speech model to train")
    accuracy = models.FloatField(default=0.7, help_text="Text validation accuracy threshold (0-1)")
    need_noise_reduction = models.BooleanField(default=False, help_text="Enable noise reduction")
    need_volume_normalization = models.BooleanField(default=False, help_text="Enable volume normalization")
    
    # Output fields
    output_url = models.URLField(max_length=1000, blank=True, null=True, help_text="URL to the generated audio")
    audio_url = models.URLField(max_length=1000, blank=True, null=True, help_text="URL to locally stored audio")
    replicate_url = models.URLField(max_length=1000, blank=True, null=True, help_text="URL to the Replicate prediction")
    replicate_id = models.CharField(max_length=100, blank=True, null=True, help_text="Replicate prediction ID for tracking job status")
    preview = models.URLField(max_length=1000, blank=True, null=True, help_text="Preview URL from the model")
    voice_id = models.CharField(max_length=50, blank=True, null=True, help_text="The voice ID of the trained model")
    
    # Status fields
    status = models.CharField(
        max_length=20,
        default='starting',
        choices=(
            ('starting', 'Starting'),
            ('processing', 'Processing'),
            ('succeeded', 'Succeeded'),
            ('failed', 'Failed'),
            ('canceled', 'Canceled'),
        ),
        help_text="Current status of the job"
    )
    error_message = models.TextField(blank=True, null=True, help_text="Error message if job failed")
    
    # Meta information
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the job was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="When the job was last updated")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When the job was completed")
    
    # For webhook callbacks
    webhook_url = models.URLField(max_length=1000, blank=True, null=True, help_text="URL for Replicate to send webhook updates")
    webhook_secret = models.CharField(max_length=255, blank=True, null=True, help_text="Secret for webhook validation")
    client_webhook_url = models.URLField(max_length=1000, blank=True, null=True, help_text="URL to send client webhook updates")

    class Meta:
        verbose_name = "Minimax Voice Clone Job"
        verbose_name_plural = "Minimax Voice Clone Jobs"
        ordering = ['-created_at']

    def __str__(self):
        return f"VoiceClone {self.id} - {self.status}"


class MinimaxSpeechJob(models.Model):
    """
    Model for storing Minimax Speech job information (for both HD and Turbo models)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    text = models.TextField(help_text="Text to be spoken")
    voice_id = models.CharField(
        max_length=50, 
        default="Wise_Woman",
        help_text="Desired voice ID (e.g., 'Wise_Woman', 'Friendly_Person', etc.)"
    )
    language = models.CharField(
        max_length=10, 
        default='en',
        help_text="Language code (e.g., 'en', 'es', 'fr')"
    )
    speed = models.FloatField(
        default=1.0, 
        help_text="Speech speed multiplier (0.5-2.0)"
    )
    pitch = models.IntegerField(
        default=0,
        help_text="Speech pitch (-12 to 12)"
    )
    volume = models.FloatField(
        default=1.0,
        help_text="Speech volume (0-10)"
    )
    bitrate = models.IntegerField(
        default=128000,
        help_text="Bitrate for the generated speech"
    )
    channel = models.CharField(
        max_length=10,
        default="mono",
        help_text="Number of audio channels"
    )
    emotion = models.CharField(
        max_length=20,
        default="auto",
        help_text="Speech emotion"
    )
    sample_rate = models.IntegerField(
        default=32000,
        help_text="Sample rate for the generated speech"
    )
    language_boost = models.CharField(
        max_length=20,
        default="English",
        help_text="Enhance recognition of specific languages and dialects"
    )
    english_normalization = models.BooleanField(
        default=False,
        help_text="Enable English text normalization for better number reading"
    )
    model_version = models.CharField(
        max_length=20,
        choices=(
            ('hd', 'HD'),
            ('turbo', 'Turbo'),
        ),
        help_text="Which model version to use"
    )
    
    # Output fields
    output_url = models.URLField(max_length=1000, blank=True, null=True, help_text="URL to the generated audio")
    audio_url = models.URLField(max_length=1000, blank=True, null=True, help_text="URL to locally stored audio")
    replicate_url = models.URLField(max_length=1000, blank=True, null=True, help_text="URL to the Replicate prediction")
    
    # Status fields
    status = models.CharField(
        max_length=20,
        default='starting',
        choices=(
            ('starting', 'Starting'),
            ('processing', 'Processing'),
            ('succeeded', 'Succeeded'),
            ('failed', 'Failed'),
            ('canceled', 'Canceled'),
        ),
        help_text="Current status of the job"
    )
    error_message = models.TextField(blank=True, null=True, help_text="Error message if job failed")
    
    # Meta information
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the job was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="When the job was last updated")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When the job was completed")
    
    # For webhook callbacks
    webhook_url = models.URLField(max_length=1000, blank=True, null=True, help_text="URL for Replicate to send webhook updates")
    webhook_secret = models.CharField(max_length=255, blank=True, null=True, help_text="Secret for webhook validation")
    client_webhook_url = models.URLField(max_length=1000, blank=True, null=True, help_text="URL to send client webhook updates")

    class Meta:
        verbose_name = "Minimax Speech Job"
        verbose_name_plural = "Minimax Speech Jobs"
        ordering = ['-created_at']

    def __str__(self):
        return f"Speech-{self.model_version} {self.id} - {self.status}"
