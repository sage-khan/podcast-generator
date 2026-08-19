from django.contrib import admin
from .models import TrainedModel, TrainingImage, LoraTrainingJob

@admin.register(TrainedModel)
class TrainedModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'status', 'replicate_model_version', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'model_id', 'trigger_word')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'model_id', 'trigger_word', 'created_at', 'updated_at')
        }),
        ('Replicate Details', {
            'fields': ('replicate_owner', 'replicate_model_name', 'replicate_model_version')
        }),
        ('URLs', {
            'fields': ('base_image_url', 'training_images_urls')
        }),
        ('Parameters', {
            'fields': ('prompt', 'negative_prompt', 'seed', 'steps')
        }),
        ('Training Configuration', {
            'fields': ('lora_rank', 'resolution', 'batch_size', 'learning_rate'),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('status', 'training_started_at', 'training_completed_at')
        }),
    )

@admin.register(TrainingImage)
class TrainingImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'model', 'created_at')
    list_filter = ('created_at', 'model')
    search_fields = ('model__name', 'image_url')
    readonly_fields = ('id', 'created_at')
    autocomplete_fields = ['model']

@admin.register(LoraTrainingJob)
class LoraTrainingJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'model_name', 'status', 'replicate_model_version', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('model_name', 'replicate_training_id')
    readonly_fields = ('id', 'created_at', 'updated_at', 'completed_at')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'model_name', 'created_at', 'updated_at', 'completed_at')
        }),
        ('Replicate Details', {
            'fields': ('replicate_training_id', 'replicate_model_version', 'replicate_model_owner')
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Webhook Configuration', {
            'fields': ('webhook_url', 'webhook_secret', 'webhook_events_filter_used', 'client_webhook_url'),
            'classes': ('collapse',),
        }),
        ('Training Parameters', {
            'fields': ('class_word', 'instance_prompt', 'training_image_urls', 'num_training_steps',
                      'learning_rate', 'instance_data_dir', 'model_url'),
            'classes': ('collapse',),
        }),
    )