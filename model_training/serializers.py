from rest_framework import serializers
from model_training.models import (
    TrainedModel, TrainingImage, LoraTrainingJob
)


class TrainingImageSerializer(serializers.ModelSerializer):
    """Serializer for TrainingImage model"""
    class Meta:
        model = TrainingImage
        fields = ['id', 'model', 'image_url', 'created_at']
        read_only_fields = ['id', 'created_at']


class TrainedModelSerializer(serializers.ModelSerializer):
    """Serializer for TrainedModel model"""
    training_images = TrainingImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = TrainedModel
        fields = [
            'id', 'name', 'model_id', 'trigger_word', 'replicate_owner',
            'replicate_model_name', 'replicate_model_version', 'base_image_url',
            'training_images_urls', 'prompt', 'negative_prompt', 'seed', 
            'steps', 'lora_rank', 'resolution', 'batch_size', 'learning_rate',
            'status', 'training_started_at', 'training_completed_at',
            'created_at', 'updated_at', 'training_images'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'status', 
                           'training_started_at', 'training_completed_at']


class LoraTrainingInputSerializer(serializers.Serializer):
    """Serializer for LoRA training input parameters"""
    model_name = serializers.CharField(required=True, help_text="Name for the LoRA model")
    input_image_urls = serializers.ListField(
        child=serializers.URLField(), 
        required=True,
        help_text="List of URLs for training images"
    )
    trigger_word = serializers.CharField(
        required=True, 
        help_text="Trigger word to use with the trained model"
    )
    seed = serializers.IntegerField(
        required=False, 
        allow_null=True,
        help_text="Random seed for training"
    )
    steps = serializers.IntegerField(
        required=False, 
        default=1000,
        help_text="Number of training steps"
    )
    lora_rank = serializers.IntegerField(
        required=False, 
        default=4,
        help_text="LoRA rank parameter"
    )
    resolution = serializers.IntegerField(
        required=False, 
        default=512,
        help_text="Training resolution"
    )
    batch_size = serializers.IntegerField(
        required=False, 
        default=1,
        help_text="Training batch size"
    )
    learning_rate = serializers.FloatField(
        required=False, 
        default=1e-4,
        help_text="Learning rate"
    )
    client_webhook_url = serializers.URLField(
        required=False, 
        allow_null=True, 
        allow_blank=True,
        help_text="Client webhook URL for direct callbacks"
    )


class LoraTrainingOutputSerializer(serializers.ModelSerializer):
    """Serializer for LoRA training job details and status"""
    class Meta:
        model = LoraTrainingJob
        fields = [
            'id', 'model_name', 'replicate_training_id', 'replicate_model_version',
            'replicate_model_owner', 'status', 'input_image_urls', 'trigger_word',
            'seed', 'steps', 'lora_rank', 'resolution', 'batch_size', 
            'learning_rate', 'error_message', 'created_at', 'started_at', 
            'completed_at'
        ]
        read_only_fields = fields


class ModelTrainSerializer(serializers.Serializer):
    """Legacy serializer for model training API compatibility"""
    name = serializers.CharField(required=True)
    trigger_word = serializers.CharField(required=True)
    image_urls = serializers.ListField(
        child=serializers.URLField(), 
        required=True
    )
    seed = serializers.IntegerField(required=False, allow_null=True)
    steps = serializers.IntegerField(required=False, default=1000)
    client_webhook_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)