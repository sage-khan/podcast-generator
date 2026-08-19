from rest_framework import serializers
from image_generation.models import Character, Pose, LoraGenerationJob, FluxUltraProJob, FluxKontextProJob, FluxKontextMultiJob, FluxKontextMultiListJob, FluxKontextPortraitSeriesJob


class CharacterSerializer(serializers.ModelSerializer):
    """Serializer for retrieving Character instances"""
    class Meta:
        model = Character
        fields = [
            'id', 'prompt', 'negative_prompt', 'image_url', 'replicate_url', 
            'created_at', 'status', 'replicate_prediction_id', 'seed', 
            'aspect_ratio', 'image_prompt', 'output_format', 'output_quality',
            'safety_tolerance', 'image_prompt_strength', 'raw', 'error_message',
            'output_urls'
        ]
        read_only_fields = ['id', 'created_at', 'image_url', 'replicate_url', 'status', 
                          'replicate_prediction_id', 'error_message', 'output_urls']


class CharacterGenerateSerializer(serializers.Serializer):
    """Serializer for the character generation API endpoint"""
    prompt = serializers.CharField(required=True)
    negative_prompt = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    seed = serializers.IntegerField(required=False, allow_null=True)
    aspect_ratio = serializers.CharField(required=False, allow_null=True, default="1:1")
    image_prompt = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    output_format = serializers.CharField(required=False, allow_null=True, default="jpg")
    output_quality = serializers.IntegerField(required=False, allow_null=True, default=80)
    safety_tolerance = serializers.IntegerField(required=False, allow_null=True, default=2)
    image_prompt_strength = serializers.FloatField(required=False, allow_null=True, default=0.1)
    raw = serializers.BooleanField(required=False, allow_null=True, default=False)
    client_webhook_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)


class PoseSerializer(serializers.ModelSerializer):
    """Serializer for retrieving Pose instances"""
    character_id = serializers.UUIDField(source='character.id', read_only=True)
    
    class Meta:
        model = Pose
        fields = [
            'id', 'character_id', 'image_url', 'replicate_url', 'created_at', 
            'status', 'replicate_prediction_id', 'pose_prompt', 'pose_type',
            'error_message', 'output_urls'
        ]
        read_only_fields = ['id', 'created_at', 'image_url', 'replicate_url', 'status', 
                          'replicate_prediction_id', 'error_message', 'output_urls']


class PoseGenerateSerializer(serializers.Serializer):
    """Serializer for the pose generation API endpoint"""
    character_id = serializers.UUIDField(required=False)
    subject = serializers.URLField(required=False, help_text="An image URL of a person. Best images are square close ups of a face, but they do not have to be.")
    prompt = serializers.CharField(required=False, default="A headshot photo", help_text="Describe the subject. Include clothes and hairstyle for more consistency.")
    pose_prompt = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    pose_type = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    seed = serializers.IntegerField(required=False, allow_null=True, help_text="Set a seed for reproducibility. Random by default.")
    aspect_ratio = serializers.CharField(required=False, allow_null=True, default="1:1")
    output_format = serializers.CharField(required=False, allow_null=True, default="webp", help_text="Format of the output images")
    output_quality = serializers.IntegerField(required=False, default=80, min_value=0, max_value=100, 
                                           help_text="Quality of the output images, from 0 to 100. 100 is best quality, 0 is lowest quality.")
    negative_prompt = serializers.CharField(required=False, allow_null=True, allow_blank=True, help_text="Things you do not want to see in your image")
    randomise_poses = serializers.BooleanField(required=False, default=True, help_text="Randomise the poses used.")
    number_of_outputs = serializers.IntegerField(required=False, default=3, min_value=1, max_value=20, help_text="The number of images to generate.")
    disable_safety_checker = serializers.BooleanField(required=False, default=False, help_text="Disable safety checker for generated images.")
    number_of_images_per_pose = serializers.IntegerField(required=False, default=1, min_value=1, max_value=4, 
                                                       help_text="The number of images to generate for each pose.")
    client_webhook_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    
    def validate(self, data):
        """Validate that either character_id or subject is provided"""
        if not data.get('character_id') and not data.get('subject'):
            raise serializers.ValidationError("Either character_id or subject (image URL) must be provided")
        return data


class CharacterStatusSerializer(serializers.Serializer):
    """Serializer for character generation status responses"""
    id = serializers.UUIDField()
    prompt = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    image_url = serializers.URLField(required=False)
    replicate_url = serializers.URLField(required=False)
    output_urls = serializers.ListField(child=serializers.URLField(), required=False)
    error_message = serializers.CharField(required=False, allow_null=True)


class PoseStatusSerializer(serializers.Serializer):
    """Serializer for pose generation status responses"""
    id = serializers.UUIDField()
    character_id = serializers.UUIDField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    image_url = serializers.URLField(required=False)
    replicate_url = serializers.URLField(required=False)
    output_urls = serializers.ListField(child=serializers.URLField(), required=False)
    error_message = serializers.CharField(required=False, allow_null=True)


class LoraGenerationSerializer(serializers.ModelSerializer):
    """Serializer for retrieving LoraGenerationJob instances"""
    class Meta:
        model = LoraGenerationJob
        fields = [
            'id', 'model_id', 'prompt', 'negative_prompt', 'created_at', 'completed_at',
            'status', 'replicate_prediction_id', 'num_outputs', 'seed', 'go_fast', 
            'lora_scale', 'megapixels', 'aspect_ratio', 'output_format', 'guidance_scale',
            'output_quality', 'prompt_strength', 'extra_lora_scale', 'num_inference_steps',
            'width', 'height', 'error_message', 'output_urls'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at', 'status', 
                          'replicate_prediction_id', 'error_message', 'output_urls']


class LoraGenerationInputSerializer(serializers.Serializer):
    """Serializer for the LoRA image generation API endpoint"""
    model_id = serializers.CharField(required=True, 
                                     help_text="Replicate LoRA model ID in format owner/name:version")
    prompt = serializers.CharField(required=True)
    negative_prompt = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    # Image to image and inpainting parameters
    image = serializers.URLField(required=False, allow_null=True, allow_blank=True,
                                help_text="Input image URL for image-to-image or inpainting mode")
    mask = serializers.URLField(required=False, allow_null=True, allow_blank=True,
                               help_text="Image mask URL for inpainting mode")
    num_outputs = serializers.IntegerField(required=False, default=4, min_value=1, max_value=10)
    seed = serializers.IntegerField(required=False, allow_null=True)
    go_fast = serializers.BooleanField(required=False, default=False)
    lora_scale = serializers.FloatField(required=False, default=1.0)
    megapixels = serializers.CharField(required=False, default="1")
    aspect_ratio = serializers.CharField(required=False, default="1:1")
    output_format = serializers.CharField(required=False, default="webp")
    guidance_scale = serializers.FloatField(required=False, default=3.0)
    output_quality = serializers.IntegerField(required=False, default=80)
    prompt_strength = serializers.FloatField(required=False, default=0.8)
    # Model parameter (dev or schnell)
    model = serializers.CharField(required=False, default="dev",
                                 help_text="Model type: 'dev' or 'schnell'")
    # Safety checker parameter
    disable_safety_checker = serializers.BooleanField(required=False, default=False)
    # Extra LoRA parameters
    extra_lora = serializers.CharField(required=False, allow_null=True, allow_blank=True,
                                      help_text="URL or identifier for additional LoRA weights")
    extra_lora_scale = serializers.FloatField(required=False, allow_null=True, default=1.0)
    num_inference_steps = serializers.IntegerField(required=False, default=28)
    width = serializers.IntegerField(required=False, allow_null=True)
    height = serializers.IntegerField(required=False, allow_null=True)
    webhook_events_filter = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=["start", "output", "completed"],
        help_text="List of events to trigger webhook for (e.g., ['start', 'output', 'completed'])"
    )
    client_webhook_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)


class LoraGenerationStatusSerializer(serializers.Serializer):
    """Serializer for LoRA generation status responses"""
    id = serializers.UUIDField()
    model_id = serializers.CharField()
    prompt = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(required=False, allow_null=True)
    replicate_prediction_id = serializers.CharField(required=False, allow_null=True)
    output_urls = serializers.ListField(child=serializers.URLField(), required=False)
    error_message = serializers.CharField(required=False, allow_null=True)


# Serializers for Flux-1.1-pro-ultra
class FluxUltraProSerializer(serializers.ModelSerializer):
    """Serializer for retrieving FluxUltraProJob instances"""
    class Meta:
        model = FluxUltraProJob
        fields = [
            'id', 'prompt', 'negative_prompt', 'created_at', 'completed_at',
            'status', 'replicate_prediction_id', 'seed', 'aspect_ratio', 
            'image_prompt', 'output_format', 'safety_tolerance', 
            'image_prompt_strength', 'raw', 'error_message', 'output_urls'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at', 'status', 
                          'replicate_prediction_id', 'error_message', 'output_urls']


class FluxUltraProInputSerializer(serializers.Serializer):
    """Serializer for the Flux-1.1-pro-ultra image generation API endpoint"""
    prompt = serializers.CharField(required=True)
    negative_prompt = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    seed = serializers.IntegerField(required=False, allow_null=True)
    aspect_ratio = serializers.CharField(required=False, allow_null=True, default="1:1")
    image_prompt = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    output_format = serializers.CharField(required=False, allow_null=True, default="jpg")
    safety_tolerance = serializers.IntegerField(required=False, allow_null=True, default=2)
    image_prompt_strength = serializers.FloatField(required=False, allow_null=True, default=0.1)
    raw = serializers.BooleanField(required=False, allow_null=True, default=False)
    webhook_events_filter = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=["start", "output", "completed"],
        help_text="List of events to trigger webhook for (e.g., ['start', 'output', 'completed'])"
    )
    client_webhook_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)


class FluxUltraProStatusSerializer(serializers.Serializer):
    """Serializer for Flux-1.1-pro-ultra generation status responses"""
    id = serializers.UUIDField()
    prompt = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(required=False, allow_null=True)
    replicate_prediction_id = serializers.CharField(required=False, allow_null=True)
    output_urls = serializers.ListField(child=serializers.URLField(), required=False)
    error_message = serializers.CharField(required=False, allow_null=True)


# Serializers for Flux Kontext Pro
class FluxKontextProSerializer(serializers.ModelSerializer):
    """Serializer for retrieving FluxKontextProJob instances"""
    class Meta:
        model = FluxKontextProJob
        fields = [
            'id', 'prompt', 'created_at', 'completed_at', 'status', 
            'replicate_prediction_id', 'seed', 'input_image', 'aspect_ratio', 
            'output_format', 'safety_tolerance', 'error_message', 'output_url'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at', 'status', 
                          'replicate_prediction_id', 'error_message', 'output_url']


class FluxKontextProInputSerializer(serializers.Serializer):
    """Serializer for the Flux Kontext Pro image editing API endpoint"""
    prompt = serializers.CharField(required=True, 
                                 help_text="Text description of what you want to generate, or the instruction on how to edit the given image")
    input_image = serializers.URLField(required=True, 
                                     help_text="Image to use as reference. Must be jpeg, png, gif, or webp")
    seed = serializers.IntegerField(required=False, allow_null=True)
    aspect_ratio = serializers.CharField(required=False, default="match_input_image",
                                       help_text="Aspect ratio of the generated image")
    output_format = serializers.CharField(required=False, default="png")
    safety_tolerance = serializers.IntegerField(required=False, default=2, min_value=0, max_value=6,
                                              help_text="Safety tolerance, 0 is most strict and 6 is most permissive")
    webhook_events_filter = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=["start", "output", "completed"],
        help_text="List of events to trigger webhook for (e.g., ['start', 'output', 'completed'])"
    )
    client_webhook_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)


class FluxKontextProStatusSerializer(serializers.Serializer):
    """Serializer for Flux Kontext Pro status responses"""
    id = serializers.UUIDField()
    prompt = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(required=False, allow_null=True)
    replicate_prediction_id = serializers.CharField(required=False, allow_null=True)
    output_url = serializers.URLField(required=False)
    error_message = serializers.CharField(required=False, allow_null=True)


# Serializers for Flux Kontext Multi-Image
class FluxKontextMultiSerializer(serializers.ModelSerializer):
    """Serializer for retrieving FluxKontextMultiJob instances"""
    class Meta:
        model = FluxKontextMultiJob
        fields = [
            'id', 'prompt', 'created_at', 'completed_at', 'status', 
            'replicate_prediction_id', 'seed', 'input_image_1', 'input_image_2', 
            'aspect_ratio', 'error_message', 'output_url'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at', 'status', 
                          'replicate_prediction_id', 'error_message', 'output_url']


class FluxKontextMultiInputSerializer(serializers.Serializer):
    """Serializer for the Flux Kontext Multi-Image API endpoint"""
    prompt = serializers.CharField(required=True,
                                 help_text="Text description of how to combine or transform the two input images")
    input_image_1 = serializers.URLField(required=True,
                                       help_text="First input image. Must be jpeg, png, gif, or webp")
    input_image_2 = serializers.URLField(required=True, 
                                       help_text="Second input image. Must be jpeg, png, gif, or webp")
    seed = serializers.IntegerField(required=False, allow_null=True)
    aspect_ratio = serializers.CharField(required=False, default="match_input_image",
                                       help_text="Aspect ratio of the generated image")
    output_format = serializers.CharField(required=False, default="png",
                                        help_text="Output format for the generated image")
    safety_tolerance = serializers.IntegerField(required=False, default=2, max_value=2,
                                             help_text="Safety tolerance, 0 is most strict and 2 is most permissive")
    webhook_events_filter = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=["start", "output", "completed"],
        help_text="List of events to trigger webhook for (e.g., ['start', 'output', 'completed'])"
    )
    client_webhook_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)


class FluxKontextMultiStatusSerializer(serializers.Serializer):
    """Serializer for Flux Kontext Multi-Image status responses"""
    id = serializers.UUIDField()
    prompt = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(required=False, allow_null=True)
    replicate_prediction_id = serializers.CharField(required=False, allow_null=True)
    output_url = serializers.URLField(required=False)
    error_message = serializers.CharField(required=False, allow_null=True)


# Serializers for Flux Kontext Multi-Image List
class FluxKontextMultiListSerializer(serializers.ModelSerializer):
    """Serializer for retrieving FluxKontextMultiListJob instances"""
    class Meta:
        model = FluxKontextMultiListJob
        fields = [
            'id', 'prompt', 'created_at', 'completed_at', 'status', 
            'replicate_prediction_id', 'seed', 'input_images', 
            'aspect_ratio', 'output_format', 'safety_tolerance',
            'error_message', 'output_url'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at', 'status', 
                          'replicate_prediction_id', 'error_message', 'output_url']


class FluxKontextMultiListInputSerializer(serializers.Serializer):
    """Serializer for the Flux Kontext Multi-Image List API endpoint"""
    prompt = serializers.CharField(required=True,
                                 help_text="Text description of how to combine or transform the input images")
    input_images = serializers.ListField(
        child=serializers.URLField(),
        required=True, 
        help_text="List of input images. Must be jpeg, png, gif, or webp."
    )
    seed = serializers.IntegerField(required=False, allow_null=True,
                                  help_text="Random seed. Set for reproducible generation")
    aspect_ratio = serializers.CharField(required=False, default="match_input_image",
                                       help_text="Aspect ratio of the generated image")
    output_format = serializers.CharField(required=False, default="png",
                                        help_text="Output format for the generated image")
    safety_tolerance = serializers.IntegerField(required=False, default=2, max_value=2,
                                             help_text="Safety tolerance, 0 is most strict and 2 is most permissive")
    webhook_events_filter = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=["start", "output", "completed"],
        help_text="List of events to trigger webhook for (e.g., ['start', 'output', 'completed'])"
    )
    client_webhook_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)


class FluxKontextMultiListStatusSerializer(serializers.Serializer):
    """Serializer for Flux Kontext Multi-Image List status responses"""
    id = serializers.UUIDField()
    prompt = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(required=False, allow_null=True)
    replicate_prediction_id = serializers.CharField(required=False, allow_null=True)
    output_url = serializers.URLField(required=False)
    error_message = serializers.CharField(required=False, allow_null=True)


# Serializers for Flux Kontext Portrait-Series
class FluxKontextPortraitSeriesInputSerializer(serializers.Serializer):
    """Serializer for Flux Kontext Portrait-Series generation input"""
    input_image = serializers.URLField(required=True, help_text="Image of the person to create a series of photos for")
    background = serializers.CharField(required=False, default="white", help_text="The background of the photo (e.g. white, black, etc)")
    num_images = serializers.IntegerField(required=False, default=4, min_value=1, max_value=13, help_text="Number of poses to generate (1-13)")
    randomize_images = serializers.BooleanField(required=False, default=False, help_text="Whether to randomize the poses")
    output_format = serializers.CharField(required=False, default="png", help_text="Output format for the generated images")
    safety_tolerance = serializers.IntegerField(required=False, default=2, min_value=0, max_value=2, help_text="Safety tolerance (0-2, where 0 is strictest)")
    client_webhook_url = serializers.URLField(required=False, allow_null=True, help_text="Optional URL for receiving job status updates")
    webhook_events_filter = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="List of webhook events to subscribe to (start, output, logs, completed)"
    )

    def validate_input_image(self, value):
        """Validate input_image is a URL to an image file"""
        # Basic URL validation is already done by the URLField
        # Additional validation for file extension could be added here if needed
        return value


class FluxKontextPortraitSeriesStatusSerializer(serializers.ModelSerializer):
    """Serializer for Flux Kontext Portrait-Series job status"""
    class Meta:
        model = FluxKontextPortraitSeriesJob
        fields = [
            'id', 'status', 'input_image', 'background', 'num_images',
            'randomize_images', 'output_format', 'safety_tolerance',
            'output_urls', 'replicate_url', 'error_message',
            'created_at', 'completed_at'
        ]
        read_only_fields = fields