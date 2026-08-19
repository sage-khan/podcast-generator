from django.contrib import admin
from .models import MinimaxVoiceCloneJob, MinimaxSpeechJob

@admin.register(MinimaxVoiceCloneJob)
class MinimaxVoiceCloneJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'voice_id', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'voice_id', 'replicate_id')
    readonly_fields = ('id', 'created_at', 'updated_at', 'completed_at')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'created_at', 'updated_at', 'completed_at')
        }),
        ('Voice Configuration', {
            'fields': ('voice_file', 'model', 'accuracy', 'need_noise_reduction', 'need_volume_normalization')
        }),
        ('Status', {
            'fields': ('status', 'replicate_id', 'error_message')
        }),
        ('Output', {
            'fields': ('voice_id', 'output_url', 'audio_url', 'replicate_url', 'preview')
        }),
        ('Webhook Configuration', {
            'fields': ('webhook_url', 'webhook_secret', 'client_webhook_url'),
            'classes': ('collapse',),
        }),
    )

@admin.register(MinimaxSpeechJob)
class MinimaxSpeechJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'voice_id', 'model_version', 'status', 'created_at')
    list_filter = ('status', 'model_version', 'created_at')
    search_fields = ('id', 'voice_id', 'text')
    readonly_fields = ('id', 'created_at', 'updated_at', 'completed_at')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'created_at', 'updated_at', 'completed_at')
        }),
        ('Content', {
            'fields': ('text', 'voice_id', 'model_version')
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Audio Configuration', {
            'fields': ('language', 'speed', 'pitch', 'volume', 'emotion', 
                      'bitrate', 'channel', 'sample_rate', 'language_boost', 'english_normalization'),
            'classes': ('collapse',),
        }),
        ('Output', {
            'fields': ('output_url', 'audio_url', 'replicate_url'),
            'classes': ('collapse',),
        }),
        ('Webhook Configuration', {
            'fields': ('webhook_url', 'webhook_secret', 'client_webhook_url'),
            'classes': ('collapse',),
        }),
    )
