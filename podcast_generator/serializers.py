from rest_framework import serializers
from .models import PodcastGenerationJob, PodcastDialogue

# Storage helper for saving uploaded PDFs
from shared.clients.storage_client import storage_client
import uuid
import os


class PodcastGenerationInputSerializer(serializers.ModelSerializer):
    """
    Serializer for podcast generation job creation. Incoming JSON uses
    `podcast_topic`, `additional_context`, and `speaker*_audio` keys for
    historical reasons, but the `PodcastGenerationJob` model stores these
    values under different field names (`podcast_idea`, `document_content`,
    and `speaker*_audio_sample`).

    We therefore:
        • Accept the original keys from the client.
        • Internally map them to the correct model field names in `create()`.
    """

    # Declare fields that map to differently-named model attributes
    podcast_topic = serializers.CharField(write_only=True)
    additional_context = serializers.CharField(
        write_only=True, required=False, allow_blank=True, allow_null=True
    )
    speaker1_audio = serializers.URLField(write_only=True, source='speaker1_audio_sample')
    speaker1_voice_clone_ID = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True, source='speaker1_voice_id')
    speaker1_video = serializers.URLField(write_only=True, required=False, allow_blank=True, allow_null=True, source='speaker1_video_url')
    speaker2_audio = serializers.URLField(
        write_only=True, required=False, allow_blank=True, allow_null=True,
        source='speaker2_audio_sample'
    )
    speaker2_voice_clone_ID = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True, source='speaker2_voice_id')
    speaker2_video = serializers.URLField(write_only=True, required=False, allow_blank=True, allow_null=True, source='speaker2_video_url')
    background_image_reference = serializers.URLField(write_only=True, required=False, allow_blank=True, allow_null=True)
    pdf_url = serializers.URLField(
        write_only=True,
        required=False,
        allow_blank=True,
        allow_null=True,
        source="document_source_url",
        help_text="Remote PDF/document URL to ingest and use as additional context",
    )
    pdf_file = serializers.FileField(
        write_only=True,
        required=False,
        allow_null=True,
        help_text="PDF file to ingest and use as additional context. Mutually exclusive with pdf_url.",
    )

    class Meta:
        model = PodcastGenerationJob
        # Keep outward-facing field names to preserve API contract
        fields = [
            'podcast_topic',          # → podcast_idea
            'additional_context',     # → document_content
            'speaker_count',
            'speaker1_name',
            'speaker1_image',
            'speaker1_audio',         # → speaker1_audio_sample
            'speaker1_voice_clone_ID',
            'speaker1_video',         # → speaker1_video_url
            'speaker2_name',
            'speaker2_image',
            'speaker2_audio',         # → speaker2_audio_sample
            'speaker2_voice_clone_ID',
            'speaker2_video',         # → speaker2_video_url
            'background_image_reference',
            'pdf_url',
            'pdf_file',
            'client_webhook_url',
        ]

    def validate(self, data):
        """Ensure all required speaker fields are present in the *incoming* payload.

        We CANNOT rely on the keys in ``data`` here for fields that use
        ``source=...`` because DRF has already translated those keys to their
        target model‐field names (e.g. ``speaker1_audio`` →
        ``speaker1_audio_sample``).  Instead, we inspect ``self.initial_data`` –
        the untouched JSON payload sent by the client – so that we reference
        precisely the keys the user supplied and that our public API specifies.
        """

        # Use validated ``speaker_count`` value but fall back to raw input.
        speaker_count = data.get('speaker_count', self.initial_data.get('speaker_count', 1))

        if speaker_count not in (1, 2):
            raise serializers.ValidationError("speaker_count must be either 1 or 2")

        payload = self.initial_data  # raw JSON as dict-like object

        # Enforce mutual exclusivity between pdf_url and pdf_file
        if payload.get('pdf_url') and payload.get('pdf_file'):
            raise serializers.ValidationError({'non_field_errors': 'Provide either pdf_url or pdf_file, not both.'})

        # Either audio OR voice clone ID must be provided
        if not payload.get('speaker1_audio') and not payload.get('speaker1_voice_clone_ID'):
            raise serializers.ValidationError({'speaker1_audio | speaker1_voice_clone_ID': 'Either audio sample or voice clone ID is required for speaker 1'})

        # Either image OR video must be provided
        if not payload.get('speaker1_image') and not payload.get('speaker1_video'):
            raise serializers.ValidationError({'speaker1_image | speaker1_video': 'Either image or video must be provided for speaker 1'})

        # Required name
        if not payload.get('speaker1_name'):
            raise serializers.ValidationError({'speaker1_name': 'This field is required'})

        # Required fields for speaker 2 (only if dual-speaker)
        if speaker_count == 2:
            if not payload.get('speaker2_audio') and not payload.get('speaker2_voice_clone_ID'):
                raise serializers.ValidationError({'speaker2_audio | speaker2_voice_clone_ID': 'Either audio sample or voice clone ID is required for speaker 2'})

            if not payload.get('speaker2_image') and not payload.get('speaker2_video'):
                raise serializers.ValidationError({'speaker2_image | speaker2_video': 'Either image or video must be provided for speaker 2'})

            if not payload.get('speaker2_name'):
                raise serializers.ValidationError({'speaker2_name': 'This field is required for dual-speaker podcasts'})

        return data

    def create(self, validated_data, **extra_fields):
        """Translate incoming keys to model field names and handle extras.

        The view passes additional fields (``user``, ``status``, webhook secrets,
        etc.) via ``serializer.save(...)``.  DRF forwards those keyword
        arguments directly to this method, *without* adding them to
        ``validated_data``.  We therefore accept ``**extra_fields`` so that we
        can merge them before creating the model instance.
        """
        # Pop the alias keys and translate
        podcast_topic = validated_data.pop('podcast_topic')
        additional_context = validated_data.pop('additional_context', '')

        alias_map = {
            'speaker1_audio': 'speaker1_audio_sample',
            'speaker1_voice_clone_ID': 'speaker1_voice_id',
            'speaker1_video': 'speaker1_video_url',
            'speaker2_audio': 'speaker2_audio_sample',
            'speaker2_voice_clone_ID': 'speaker2_voice_id',
            'speaker2_video': 'speaker2_video_url',
        }

        # Ensure any alias fields are renamed (redundant if DRF source= handled, but safe)
        for alias_key, model_key in alias_map.items():
            if alias_key in validated_data and alias_key != model_key:
                validated_data[model_key] = validated_data.pop(alias_key)

        validated_data['podcast_idea'] = podcast_topic
        validated_data['document_content'] = additional_context

        # Handle PDF upload – prioritized over remote URL
        pdf_upload = validated_data.pop('pdf_file', None)
        if pdf_upload:
            # Ensure in-memory files (e.g. io.BytesIO from tests) have a `.name`
            if not hasattr(pdf_upload, "name") or not pdf_upload.name:
                pdf_upload.name = f"{uuid.uuid4()}.pdf"

            filename = os.path.basename(pdf_upload.name)
            upload_result = storage_client.upload_file(
                pdf_upload,
                endpoint_type='pdf_ingestion',
                filename=filename,
                include_presigned=False,
            )
            # Store public URL so that downstream ingestion task sees it as remote URL
            validated_data['document_source_url'] = upload_result

        # Merge any extra keyword arguments supplied by the view
        validated_data.update(extra_fields)

        return PodcastGenerationJob.objects.create(**validated_data)


class PodcastDialogueSerializer(serializers.ModelSerializer):
    """
    Serializer for podcast dialogue information
    """
    # Map API-facing names to actual model fields
    job = serializers.PrimaryKeyRelatedField(read_only=True, source='podcast_job')
    text = serializers.CharField(source='dialogue_text')
    # lipsync_status is an alias for the model's ``status`` field to expose
    # more granular state (e.g. ``lipsync_processing``).  We derive it directly.
    lipsync_status = serializers.CharField(source='status', read_only=True)
    audio_presigned_url = serializers.URLField(read_only=True, default=None)
    video_presigned_url = serializers.URLField(read_only=True, default=None)
    lipsync_presigned_url = serializers.URLField(read_only=True, default=None)

    class Meta:
        model = PodcastDialogue
        fields = [
            'id',
            'job',            # podcast_job FK (read-only)
            'speaker_name',
            'text',           # dialogue_text
            'emotion',
            'status',
            'audio_url',
            'audio_presigned_url',
            'video_url',
            'video_presigned_url',
            'lipsync_status',
            'lipsync_url',
            'lipsync_presigned_url',
        ]


class PodcastGenerationStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for podcast generation job status
    """
    dialogues = PodcastDialogueSerializer(source='podcastdialogue_set', many=True, read_only=True)
    podcast_topic = serializers.CharField(source='podcast_idea', read_only=True)
    speaker1_video_url = serializers.URLField(read_only=True, default=None)
    speaker1_video_presigned_url = serializers.URLField(read_only=True, default=None)
    speaker2_video_url = serializers.URLField(read_only=True, default=None)
    speaker2_video_presigned_url = serializers.URLField(read_only=True, default=None)
    video_status = serializers.CharField(read_only=True, default='pending')
    final_video_status = serializers.CharField(read_only=True, default='pending')
    final_video_url = serializers.URLField(read_only=True, default=None)
    final_video_presigned_url = serializers.URLField(read_only=True, default=None)
    document_presigned_url = serializers.URLField(read_only=True, default=None)

    # ---------------- Progress helpers --------------------------------------
    script_completed = serializers.SerializerMethodField()
    audio_completed = serializers.SerializerMethodField()
    video_completed = serializers.SerializerMethodField()
    lipsync_completed = serializers.SerializerMethodField()

    audio_percent = serializers.SerializerMethodField()
    lipsync_percent = serializers.SerializerMethodField()

    def get_script_completed(self, obj):
        return bool(obj.script)

    def get_audio_completed(self, obj):
        total = obj.dialogues.count()
        if total == 0:
            return False
        return not obj.dialogues.filter(audio_url__isnull=True).exists()

    def get_video_completed(self, obj):
        if obj.skip_video:
            return True
        if obj.speaker_count == 1:
            return bool(obj.speaker1_video_url)
        else:
            return bool(obj.speaker1_video_url and obj.speaker2_video_url)

    def get_lipsync_completed(self, obj):
        if obj.skip_lipsync:
            return True
        total = obj.dialogues.count()
        if total == 0:
            return False
        return not obj.dialogues.filter(lipsync_url__isnull=True).exists()

    def get_audio_percent(self, obj):
        total = obj.dialogues.count()
        if total == 0:
            return 0
        done = total - obj.dialogues.filter(audio_url__isnull=True).count()
        return round((done / total) * 100, 1)

    def get_lipsync_percent(self, obj):
        if obj.skip_lipsync:
            return 100
        total = obj.dialogues.count()
        if total == 0:
            return 0
        done = total - obj.dialogues.filter(lipsync_url__isnull=True).count()
        return round((done / total) * 100, 1)

    class Meta:
        model = PodcastGenerationJob
        fields = [
            'id',
            'status',
            'created_at',
            'updated_at',
            'podcast_topic',
            'speaker_count',
            'speaker1_name',
            'speaker1_voice_id',
            'speaker1_video_url',
            'speaker1_video_presigned_url',
            'speaker2_name',
            'speaker2_voice_id',
            'speaker2_video_url',
            'speaker2_video_presigned_url',
            'video_status',
            'final_video_status',
            'final_video_url',
            'final_video_presigned_url',
            'document_presigned_url',
            'error_message',
            # Progress helpers
            'script_completed',
            'audio_completed',
            'video_completed',
            'lipsync_completed',
            'audio_percent',
            'lipsync_percent',
            'dialogues'
        ]
        read_only_fields = fields


# -----------------------------------------------------------------------------
# Summary / list serializer
# -----------------------------------------------------------------------------
class PodcastGenerationJobListSerializer(PodcastGenerationStatusSerializer):
    """Lightweight serializer for job listings (excludes dialogues)."""

    class Meta(PodcastGenerationStatusSerializer.Meta):
        fields = [
            'id',
            'status',
            'created_at',
            'updated_at',
            'podcast_topic',
            'script_completed',
            'audio_percent',
            'video_completed',
            'lipsync_percent',
            'final_video_url',
            'final_video_presigned_url',
            'error_message',
        ]
        read_only_fields = fields