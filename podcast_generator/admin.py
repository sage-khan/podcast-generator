from django.contrib import admin
from .models import PodcastGenerationJob, PodcastDialogue


class PodcastDialogueInline(admin.TabularInline):
    model = PodcastDialogue
    readonly_fields = [
        'speaker_name', 'dialogue_text', 'emotion', 'status', 
        'audio_url', 'video_url', 'lipsync_url',
        'error_message'
    ]
    extra = 0
    can_delete = False


@admin.register(PodcastGenerationJob)
class PodcastGenerationJobAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'podcast_idea', 'speaker_count', 'status',
        'video_generation_status', 'video_combination_status', 'created_at'
    ]
    list_filter = ['status', 'video_generation_status', 'video_combination_status', 'speaker_count']
    search_fields = ['podcast_idea', 'id', 'speaker1_name', 'speaker2_name']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'status', 'error_message',
        'webhook_secret',
        'speaker1_voice_id', 'speaker2_voice_id',
        'speaker1_image_analysis', 'speaker2_image_analysis',
        'background_prompt',
        'voice_clone_status', 'script_generation_status', 
        'image_analysis_status', 'audio_generation_status',
        'video_generation_status', 'lipsync_status', 
        'video_combination_status', 'final_video_url',
        'webhook_url', 'webhook_secret', 'client_webhook_url'
    ]
    fieldsets = [
        ('Basic Information', {
            'fields': [
                'id', 'podcast_idea', 'document_content',
                'speaker_count', 'status', 'error_message'
            ]
        }),
        ('Speaker 1', {
            'fields': [
                'speaker1_name', 'speaker1_image', 'speaker1_audio_sample',
                'speaker1_voice_id', 'speaker1_image_analysis'
            ]
        }),
        ('Speaker 2', {
            'fields': [
                'speaker2_name', 'speaker2_image', 'speaker2_audio_sample',
                'speaker2_voice_id', 'speaker2_image_analysis'
            ],
            'classes': ('collapse',),
        }),
        ('Processing Details', {
            'fields': [
                'background_prompt', 'webhook_url', 'webhook_secret',
                'client_webhook_url'
            ],
            'classes': ('collapse',),
        }),
        ('Status Tracking', {
            'fields': [
                'voice_clone_status', 'script_generation_status',
                'image_analysis_status', 'audio_generation_status',
                'video_generation_status', 'lipsync_status',
                'video_combination_status'
            ],
            'classes': ('collapse',),
        }),
        ('Final Output', {
            'fields': [
                'final_video_url'
            ]
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at', 'completed_at'],
            'classes': ('collapse',),
        }),
    ]
    inlines = [PodcastDialogueInline]


@admin.register(PodcastDialogue)
class PodcastDialogueAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'podcast_job', 'speaker_name', 'text_preview', 
        'emotion', 'status'
    ]
    list_filter = ['status', 'emotion']
    search_fields = ['dialogue_text', 'speaker_name', 'podcast_job__id', 'podcast_job__podcast_idea']
    readonly_fields = [
        'id', 'podcast_job', 'speaker_name', 'dialogue_text', 'emotion', 
        'status', 'audio_url', 'video_url', 'lipsync_url',
        'error_message'
    ]
    
    def text_preview(self, obj):
        """Return a truncated version of the dialogue text"""
        max_length = 50
        if len(obj.dialogue_text) > max_length:
            return f"{obj.dialogue_text[:max_length]}..."
        return obj.dialogue_text
    text_preview.short_description = "Text"