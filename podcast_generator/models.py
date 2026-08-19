import uuid
import os
from django.db import models
from django.utils import timezone
from django.conf import settings


class PodcastGenerationJob(models.Model):
    """
    Model for storing Podcast Generation job information
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='podcast_jobs', help_text="User who created this job")
    
    # Input parameters
    podcast_idea = models.TextField(help_text="Main idea or topic for the podcast")
    document_content = models.TextField(blank=True, null=True, help_text="Optional document content for additional context")
    # Optional: original PDF / document URL. If provided, a preprocessing task
    # downloads the file and populates ``document_content`` automatically.
    document_source_url = models.URLField(
        max_length=1000,
        blank=True,
        null=True,
        help_text="Remote PDF/doc URL to ingest into document_content",
    )
    document_presigned_url = models.URLField(
        max_length=1000,
        blank=True,
        null=True,
        help_text="Presigned version of document_source_url (auto-generated)",
    )
    speaker_count = models.IntegerField(default=1, choices=((1, "Monologue"), (2, "Dialogue")), help_text="Number of speakers in the podcast")
    
    # Speaker 1 information
    speaker1_name = models.CharField(max_length=100, default="Speaker 1", help_text="Name of the first speaker")
    speaker1_audio_sample = models.URLField(max_length=1000, help_text="URL to the audio sample for speaker 1")
    speaker1_image = models.URLField(max_length=1000, help_text="URL to the image for speaker 1")
    speaker1_video_url = models.URLField(max_length=1000, blank=True, null=True, help_text="URL to a pre-recorded video for speaker 1 (public)")
    speaker1_video_presigned_url = models.URLField(max_length=1000, blank=True, null=True, help_text="Presigned version of speaker1_video_url")
    speaker1_voice_id = models.CharField(max_length=50, blank=True, null=True, help_text="Voice ID from Minimax for speaker 1")
    speaker1_image_analysis = models.TextField(blank=True, null=True, help_text="Analysis of speaker 1's image by Gemini")
    speaker1_webhook_secret = models.CharField(max_length=255, blank=True, null=True, help_text="Secret for speaker 1 webhook validation")
    
    # Speaker 2 information (for dialogue)
    speaker2_name = models.CharField(max_length=100, default="Speaker 2", blank=True, null=True, help_text="Name of the second speaker")
    speaker2_audio_sample = models.URLField(max_length=1000, blank=True, null=True, help_text="URL to the audio sample for speaker 2")
    speaker2_image = models.URLField(max_length=1000, blank=True, null=True, help_text="URL to the image for speaker 2")
    speaker2_video_url = models.URLField(max_length=1000, blank=True, null=True, help_text="URL to a pre-recorded video for speaker 2 (public)")
    speaker2_video_presigned_url = models.URLField(max_length=1000, blank=True, null=True, help_text="Presigned version of speaker2_video_url")
    speaker2_voice_id = models.CharField(max_length=50, blank=True, null=True, help_text="Voice ID from Minimax for speaker 2")
    speaker2_image_analysis = models.TextField(blank=True, null=True, help_text="Analysis of speaker 2's image by Gemini")
    speaker2_webhook_secret = models.CharField(max_length=255, blank=True, null=True, help_text="Secret for speaker 2 webhook validation")
 
    # ------------------------------------------------------------------
    # Stage-skip flags – allow a client to bypass heavy steps.
    # These map to CLI flags like --skip-audio, --skip-video, etc.
    # ------------------------------------------------------------------
    skip_audio = models.BooleanField(default=False, help_text="Skip TTS/audio generation stage")
    skip_video = models.BooleanField(default=False, help_text="Skip silent speaker-video generation stage")
    skip_lipsync = models.BooleanField(default=False, help_text="Skip lipsync stage – implies skip_video is False")
    skip_image = models.BooleanField(default=False, help_text="Skip preliminary image/background processing stage")
    
    # Folder where all media for this job will be stored (e.g. "d41d8cd9--280625-123045")
    media_folder = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        help_text="Timestamped project folder for storing all generated media",
    )
    
    # Generated content
    script = models.JSONField(blank=True, null=True, help_text="Generated script with dialogue and emotions")
    background_prompt = models.TextField(blank=True, null=True, help_text="Prompt for generating consistent background")
    background_image_reference = models.URLField(max_length=1000, blank=True, null=True, help_text="URL to client-supplied background image to use instead of generating one")
    
    # Output URLs
    final_video_url = models.URLField(max_length=1000, blank=True, null=True, help_text="Final podcast video (public URL)")
    final_video_presigned_url = models.URLField(max_length=1000, blank=True, null=True, help_text="Presigned version of final_video_url")
    
    # Processing status tracking
    voice_clone_status = models.CharField(
        max_length=20,
        default='pending',
        choices=(
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ),
        help_text="Status of voice cloning process"
    )
    
    script_generation_status = models.CharField(
        max_length=20,
        default='pending',
        choices=(
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ),
        help_text="Status of script generation process"
    )
    
    image_analysis_status = models.CharField(
        max_length=20,
        default='pending',
        choices=(
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ),
        help_text="Status of image analysis process"
    )
    
    audio_generation_status = models.CharField(
        max_length=20,
        default='pending',
        choices=(
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ),
        help_text="Status of audio generation process"
    )
    
    video_generation_status = models.CharField(
        max_length=20,
        default='pending',
        choices=(
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ),
        help_text="Status of video generation process"
    )
    
    lipsync_status = models.CharField(
        max_length=20,
        default='pending',
        choices=(
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ),
        help_text="Status of lipsync process"
    )
    
    video_combination_status = models.CharField(
        max_length=20,
        default='pending',
        choices=(
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ),
        help_text="Status of video combination process"
    )
    
    # Overall job status
    # Top-level pipeline status – matches PodcastJobService.STATUS_FLOW
    status = models.CharField(
        max_length=30,
        default='pending',
        choices=(
            ('pending', 'Pending'),
            ('script_processing', 'Script Processing'),
            ('audio_pending', 'Audio Pending'),
            ('audio_processing', 'Audio Processing'),
            ('video_pending', 'Video Pending'),
            ('video_processing', 'Video Processing'),
            ('lipsync_pending', 'Lipsync Pending'),
            ('lipsync_processing', 'Lipsync Processing'),
            ('final_combination', 'Final Combination'),
            ('completed', 'Completed'),
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
        verbose_name = "Podcast Generation Job"
        verbose_name_plural = "Podcast Generation Jobs"
        ordering = ['-created_at']

    def __str__(self):
        return f"PodcastGeneration {self.id} - {self.status}"


class PodcastDialogue(models.Model):
    """
    Model for storing individual dialogue segments in a podcast
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    podcast_job = models.ForeignKey(PodcastGenerationJob, related_name='dialogues', on_delete=models.CASCADE)
    speaker_name = models.CharField(max_length=100, help_text="Name of the speaker")
    speaker_voice_id = models.CharField(max_length=50, help_text="Voice ID to use for this dialogue")
    
    # Track associated Minimax speech job so we can correlate webhook callbacks
    speech_job_id = models.UUIDField(
        blank=True,
        null=True,
        editable=False,
        help_text="UUID of the MinimaxSpeechJob for this dialogue"
    )
    
    sequence_number = models.IntegerField(help_text="Order of this dialogue in the conversation")
    dialogue_text = models.TextField(help_text="Text content of this dialogue segment")
    emotion = models.CharField(max_length=50, default="auto", help_text="Emotion to apply to this dialogue")
    
    # Generated output paths
    audio_url = models.URLField(max_length=1000, blank=True, null=True, help_text="Audio clip (public URL)")
    audio_presigned_url = models.URLField(max_length=1000, blank=True, null=True, help_text="Presigned version of audio_url")
    video_url = models.URLField(max_length=1000, blank=True, null=True, help_text="Silent video (public URL)")
    video_presigned_url = models.URLField(max_length=1000, blank=True, null=True, help_text="Presigned version of video_url")
    lipsync_url = models.URLField(max_length=1000, blank=True, null=True, help_text="Lip-synced video (public URL)")
    lipsync_presigned_url = models.URLField(max_length=1000, blank=True, null=True, help_text="Presigned version of lipsync_url")
    
    # Processing status
    status = models.CharField(
        max_length=20,
        default='pending',
        choices=(
            ('pending', 'Pending'),
            ('audio_processing', 'Audio Processing'),
            ('audio_completed', 'Audio Completed'),
            ('video_processing', 'Video Processing'),
            ('video_completed', 'Video Completed'),
            ('lipsync_processing', 'Lipsync Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ),
        help_text="Current status of the dialogue processing"
    )
    error_message = models.TextField(blank=True, null=True, help_text="Error message if processing failed")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sequence_number']
        
    def __str__(self):
        return f"Dialogue {self.sequence_number}: {self.speaker_name} - {self.status}"