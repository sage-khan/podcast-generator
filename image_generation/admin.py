from django.contrib import admin
from .models import (
    Character, Pose, LoraGenerationJob,
    FluxUltraProJob, FluxKontextProJob, 
    FluxKontextMultiJob, FluxKontextMultiListJob,
    FluxKontextPortraitSeriesJob
)

@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ('id', 'prompt', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('prompt', 'negative_prompt', 'id')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'prompt', 'negative_prompt', 'image_url', 'replicate_url', 'created_at')
        }),
        ('Status', {
            'fields': ('status', 'replicate_prediction_id', 'error_message')
        }),
        ('Webhook Configuration', {
            'fields': ('webhook_url', 'webhook_secret', 'webhook_events_filter_used', 'client_webhook_url'),
            'classes': ('collapse',),
        }),
        ('Generation Parameters', {
            'fields': ('seed', 'aspect_ratio', 'image_prompt', 'output_format', 'output_quality', 
                       'safety_tolerance', 'image_prompt_strength', 'raw', 'output_urls'),
            'classes': ('collapse',),
        }),
    )

@admin.register(Pose)
class PoseAdmin(admin.ModelAdmin):
    list_display = ('id', 'character', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('character__prompt', 'pose_prompt', 'id')
    readonly_fields = ('id', 'created_at')
    autocomplete_fields = ['character']
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'character', 'image_url', 'replicate_url', 'created_at')
        }),
        ('Pose Details', {
            'fields': ('pose_prompt', 'pose_type')
        }),
        ('Status', {
            'fields': ('status', 'replicate_prediction_id', 'error_message')
        }),
        ('Webhook Configuration', {
            'fields': ('webhook_url', 'webhook_secret', 'webhook_events_filter_used', 'client_webhook_url'),
            'classes': ('collapse',),
        }),
        ('Output', {
            'fields': ('output_urls',),
            'classes': ('collapse',),
        }),
    )

@admin.register(LoraGenerationJob)
class LoraGenerationJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'model_id', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('prompt', 'model_id', 'replicate_prediction_id')
    readonly_fields = ('id', 'created_at', 'completed_at')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'model_id', 'created_at', 'completed_at')
        }),
        ('Content', {
            'fields': ('prompt', 'negative_prompt')
        }),
        ('Status', {
            'fields': ('status', 'replicate_prediction_id', 'error_message')
        }),
        ('Webhook Configuration', {
            'fields': ('webhook_url', 'webhook_secret', 'webhook_events_filter_used', 'client_webhook_url'),
            'classes': ('collapse',),
        }),
        ('Output', {
            'fields': ('output_urls', 'replicate_url'),
            'classes': ('collapse',),
        }),
        ('Generation Parameters', {
            'fields': ('num_outputs', 'seed', 'go_fast', 'lora_scale', 'megapixels', 'aspect_ratio',
                      'width', 'height', 'output_format', 'guidance_scale', 'output_quality',
                      'prompt_strength', 'extra_lora_scale', 'num_inference_steps'),
            'classes': ('collapse',),
        }),
        ('Advanced Features', {
            'fields': ('image', 'mask', 'disable_safety_checker', 'model', 'extra_lora'),
            'classes': ('collapse',),
        }),
    )

@admin.register(FluxUltraProJob)
class FluxUltraProJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'prompt', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('prompt', 'id', 'replicate_id')
    readonly_fields = ('id', 'created_at', 'completed_at')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'created_at', 'completed_at')
        }),
        ('Content', {
            'fields': ('prompt', 'negative_prompt', 'input_image')
        }),
        ('Status', {
            'fields': ('status', 'replicate_id', 'replicate_url', 'error_message')
        }),
        ('Webhook Configuration', {
            'fields': ('webhook_secret', 'webhook_events_filter', 'webhook_events_filter_used', 'client_webhook_url'),
            'classes': ('collapse',),
        }),
        ('Output', {
            'fields': ('output_url',),
            'classes': ('collapse',),
        }),
        ('Generation Parameters', {
            'fields': ('aspect_ratio', 'output_format', 'safety_tolerance'),
            'classes': ('collapse',),
        }),
    )

@admin.register(FluxKontextProJob)
class FluxKontextProJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'prompt', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('prompt', 'id', 'replicate_id')
    readonly_fields = ('id', 'created_at', 'completed_at')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'created_at', 'completed_at')
        }),
        ('Content', {
            'fields': ('prompt', 'negative_prompt', 'input_image')
        }),
        ('Status', {
            'fields': ('status', 'replicate_id', 'replicate_url', 'error_message')
        }),
        ('Webhook Configuration', {
            'fields': ('webhook_secret', 'webhook_events_filter', 'webhook_events_filter_used', 'client_webhook_url'),
            'classes': ('collapse',),
        }),
        ('Output', {
            'fields': ('output_url',),
            'classes': ('collapse',),
        }),
        ('Generation Parameters', {
            'fields': ('aspect_ratio', 'output_format', 'safety_tolerance'),
            'classes': ('collapse',),
        }),
    )

@admin.register(FluxKontextMultiJob)
class FluxKontextMultiJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'prompt', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('prompt', 'id', 'replicate_id')
    readonly_fields = ('id', 'created_at', 'completed_at')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'created_at', 'completed_at')
        }),
        ('Content', {
            'fields': ('prompt', 'negative_prompt', 'input_image')
        }),
        ('Status', {
            'fields': ('status', 'replicate_id', 'replicate_url', 'error_message')
        }),
        ('Webhook Configuration', {
            'fields': ('webhook_secret', 'webhook_events_filter', 'webhook_events_filter_used', 'client_webhook_url'),
            'classes': ('collapse',),
        }),
        ('Output', {
            'fields': ('output_urls',),
            'classes': ('collapse',),
        }),
        ('Generation Parameters', {
            'fields': ('num_images', 'aspect_ratio', 'output_format', 'safety_tolerance'),
            'classes': ('collapse',),
        }),
    )

@admin.register(FluxKontextMultiListJob)
class FluxKontextMultiListJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'prompt', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('prompt', 'id', 'replicate_id')
    readonly_fields = ('id', 'created_at', 'completed_at')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'created_at', 'completed_at')
        }),
        ('Content', {
            'fields': ('prompt', 'negative_prompt', 'input_images')
        }),
        ('Status', {
            'fields': ('status', 'replicate_id', 'replicate_url', 'error_message')
        }),
        ('Webhook Configuration', {
            'fields': ('webhook_secret', 'webhook_events_filter', 'webhook_events_filter_used', 'client_webhook_url'),
            'classes': ('collapse',),
        }),
        ('Output', {
            'fields': ('output_url',),
            'classes': ('collapse',),
        }),
        ('Generation Parameters', {
            'fields': ('aspect_ratio', 'output_format', 'safety_tolerance'),
            'classes': ('collapse',),
        }),
    )

@admin.register(FluxKontextPortraitSeriesJob)
class FluxKontextPortraitSeriesJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'input_image', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'replicate_id')
    readonly_fields = ('id', 'created_at', 'completed_at')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'created_at', 'completed_at')
        }),
        ('Content', {
            'fields': ('input_image',)
        }),
        ('Status', {
            'fields': ('status', 'replicate_id', 'replicate_url', 'error_message')
        }),
        ('Webhook Configuration', {
            'fields': ('webhook_secret', 'webhook_events_filter', 'webhook_events_filter_used', 'client_webhook_url'),
            'classes': ('collapse',),
        }),
        ('Output', {
            'fields': ('output_urls',),
            'classes': ('collapse',),
        }),
        ('Generation Parameters', {
            'fields': ('background', 'num_images', 'randomize_images', 'output_format', 'safety_tolerance'),
            'classes': ('collapse',),
        }),
    )