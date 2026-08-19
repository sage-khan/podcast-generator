from django.contrib import admin
from .models import KlingVideoJob, KlingLipsyncJob, GoogleVeo3VideoJob

@admin.register(KlingVideoJob)
class KlingVideoJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'prompt', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'prompt')
    readonly_fields = ('id', 'created_at', 'updated_at', 'completed_at')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'created_at', 'updated_at', 'completed_at')
        }),
        ('Content', {
            'fields': ('prompt', 'negative_prompt')
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Video Configuration', {
            'fields': ('aspect_ratio', 'start_image', 'end_image', 'reference_images', 
                      'cfg_scale', 'duration')
        }),
        ('Output', {
            'fields': ('output_url', 'video_url', 'replicate_url'),
            'classes': ('collapse',),
        }),
        ('Webhook Configuration', {
            'fields': ('webhook_url', 'webhook_secret', 'client_webhook_url'),
            'classes': ('collapse',),
        }),
    )

@admin.register(KlingLipsyncJob)
class KlingLipsyncJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'text', 'voice_id')
    readonly_fields = ('id', 'created_at', 'updated_at', 'completed_at')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'created_at', 'updated_at', 'completed_at')
        }),
        ('Text Input', {
            'fields': ('text', 'voice_id', 'voice_speed'),
            'classes': ('collapse',),
        }),
        ('Audio Input', {
            'fields': ('audio_file', 'audio_url'),
            'classes': ('collapse',),
        }),
        ('Video Sources', {
            'fields': ('video_id', 'video_url', 'image_url'),
            'classes': ('collapse',),
        }),
        ('Additional Parameters', {
            'fields': ('prompt', 'negative_prompt'),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Output', {
            'fields': ('output_url', 'video_output_url', 'replicate_url'),
            'classes': ('collapse',),
        }),
        ('Webhook Configuration', {
            'fields': ('webhook_url', 'webhook_secret', 'client_webhook_url'),
            'classes': ('collapse',),
        }),
    )

@admin.register(GoogleVeo3VideoJob)
class GoogleVeo3VideoJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'prompt', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'prompt')
    readonly_fields = ('id', 'created_at', 'updated_at', 'completed_at')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'created_at', 'updated_at', 'completed_at')
        }),
        ('Content', {
            'fields': ('prompt', 'negative_prompt', 'enhance_prompt', 'seed')
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Output', {
            'fields': ('output_url', 'video_url', 'replicate_url'),
            'classes': ('collapse',),
        }),
        ('Webhook Configuration', {
            'fields': ('webhook_url', 'webhook_secret', 'client_webhook_url'),
            'classes': ('collapse',),
        }),
    )
