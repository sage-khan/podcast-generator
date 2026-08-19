from rest_framework import serializers
from audio_generation.models import MinimaxVoiceCloneJob, MinimaxSpeechJob


class MinimaxVoiceCloneGenerateSerializer(serializers.Serializer):
    """
    Serializer for generating voice clone with Minimax
    """
    # Allow the client (e.g., podcast_generator.clone_voice) to pre-generate a UUID
    # for the voice-clone job. If omitted, the server will automatically assign one.
    id = serializers.UUIDField(required=False, help_text="Optional pre-generated UUID for the job")
    voice_file = serializers.URLField(required=True, help_text="URL to the reference audio for voice cloning (MP3, M4A, or WAV format, 10s to 5min)")
    model = serializers.CharField(required=False, default="speech-02-turbo", help_text="The text-to-speech model to train")
    accuracy = serializers.FloatField(required=False, default=0.7, help_text="Text validation accuracy threshold (0-1)")
    need_noise_reduction = serializers.BooleanField(required=False, default=False, help_text="Enable noise reduction")
    need_volume_normalization = serializers.BooleanField(required=False, default=False, help_text="Enable volume normalization")
    client_webhook_url = serializers.URLField(required=False, allow_null=True, help_text="URL to send webhook updates to")
    
    def validate_accuracy(self, value):
        """Validate that accuracy is between 0 and 1"""
        if value < 0 or value > 1:
            raise serializers.ValidationError("Accuracy must be between 0 and 1")
        return value


class MinimaxVoiceCloneStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = MinimaxVoiceCloneJob
        fields = [
            'id', 'status', 'created_at', 'completed_at', 'error_message',
            'output_url', 'audio_url', 'replicate_url', 'replicate_id',
            'voice_file', 'model', 'accuracy', 'need_noise_reduction',
            'need_volume_normalization',  # existing
            'voice_id', 'preview'         # <-- NEW
        ]


class MinimaxSpeechGenerateSerializer(serializers.Serializer):
    """
    Serializer for generating speech with Minimax models
    """
    text = serializers.CharField(required=True, help_text="Text to be spoken. Maximum 5000 characters.")
    voice_id = serializers.CharField(
        required=False, 
        default="Wise_Woman", 
        help_text="Desired voice ID (e.g., 'Wise_Woman', 'Friendly_Person', etc.)"
    )
    language = serializers.CharField(
        required=False, 
        default="en", 
        help_text="Language code (e.g., 'en', 'es', 'fr')"
    )
    speed = serializers.FloatField(
        required=False, 
        default=1.0, 
        help_text="Speech speed multiplier (0.5-2.0)"
    )
    pitch = serializers.IntegerField(
        required=False,
        default=0,
        help_text="Speech pitch (-12 to 12)"
    )
    volume = serializers.FloatField(
        required=False,
        default=1.0,
        help_text="Speech volume (0-10)"
    )
    bitrate = serializers.IntegerField(
        required=False,
        default=128000,
        help_text="Bitrate for the generated speech"
    )
    channel = serializers.ChoiceField(
        required=False,
        default="mono",
        choices=["mono", "stereo"],
        help_text="Number of audio channels (mono or stereo)"
    )
    emotion = serializers.CharField(
        required=False,
        default="auto",
        help_text="Speech emotion (auto, happy, sad, angry, fear, disgust, neutral)"
    )
    sample_rate = serializers.IntegerField(
        required=False,
        default=32000,
        help_text="Sample rate for the generated speech (e.g., 16000, 24000, 32000, 44100)"
    )
    language_boost = serializers.CharField(
        required=False,
        default="English",
        help_text="Enhance recognition of specific languages and dialects"
    )
    english_normalization = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Enable English text normalization for better number reading"
    )
    client_webhook_url = serializers.URLField(required=False, allow_null=True, help_text="URL to send webhook updates to")
    
    def validate_text(self, value):
        """Validate that text is not too long"""
        if len(value) > 5000:
            raise serializers.ValidationError("Text must be 5000 characters or less")
        return value

    def validate_speed(self, value):
        """Validate that speed is between 0.5 and 2.0"""
        if value < 0.5 or value > 2.0:
            raise serializers.ValidationError("Speed must be between 0.5 and 2.0")
        return value
    
    def validate_pitch(self, value):
        """Validate that pitch is between -12 and 12"""
        if value < -12 or value > 12:
            raise serializers.ValidationError("Pitch must be between -12 and 12")
        return value
    
    def validate_volume(self, value):
        """Validate that volume is between 0 and 10"""
        if value < 0 or value > 10:
            raise serializers.ValidationError("Volume must be between 0 and 10")
        return value

    def validate_sample_rate(self, value):
        """Validate sample rate is one of the supported values"""
        valid_rates = [16000, 24000, 32000, 44100]
        if value not in valid_rates:
            raise serializers.ValidationError(f"Sample rate must be one of {valid_rates}")
        return value


class MinimaxSpeechStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for the status of a Minimax speech job
    """
    class Meta:
        model = MinimaxSpeechJob
        fields = [
            'id', 'status', 'created_at', 'completed_at', 'error_message',
            'text', 'voice_id', 'language', 'speed', 'pitch', 'volume',
            'bitrate', 'channel', 'emotion', 'sample_rate', 'language_boost',
            'english_normalization', 'model_version', 'output_url', 'audio_url', 'replicate_url'
        ]
