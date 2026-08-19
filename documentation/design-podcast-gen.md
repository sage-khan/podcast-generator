# AI Podcast Generator – Technical Design

## Overview

This document describes the technical design and implementation plan for an AI-powered podcast generator. The system ingests audio, video, or text inputs, generates podcast scripts using AI, and produces final podcast audio/video outputs. The workflow includes dialogue generation, voice synthesis, and user review/approval.

The podcast generator will be implemented as a Django application and integrated with the existing AI image generation project.

## 1. System Components

### 1.1 Input Handlers

- **Audio Input**: Accepts audio files (e.g., mp3, wav)
- **Video Input**: Accepts video files (e.g., mp4, mov)
- **Text Input**: Accepts plain text or structured text (e.g., docx, txt)
- **API Endpoints**: Django REST Framework endpoints for uploading files and text

### 1.2 Dialogue Generation

- **AI Model**: Use OpenAI GPT-4 or similar LLM for script/dialogue generation
- **Prompt Engineering**: Custom prompts to generate dialogue for each speaker
- **Speaker Profiles**: Define profiles for each speaker (name, tone, style)

### 1.3 Speaker Assignment

- Assign generated dialogue to virtual speakers
- Store speaker metadata (voice style, language, etc.)

### 1.4 Voice Synthesis

- **TTS Engine**: Use services like ElevenLabs, Google TTS, or Azure TTS
- **API Integration**: REST API calls to synthesize audio from generated scripts
- **Voice Cloning**: Optionally support custom/celebrity voices

### 1.5 Video Generation (Optional)

- **Avatar/Stock Video**: Use avatar generation or stock footage for video podcasts
- **Lip Sync**: Sync TTS audio with avatar/video (e.g., D-ID, Synthesia APIs)

### 1.6 Review & Approval

- **Web UI**: Django templates with React components for reviewing generated scripts and audio/video
- **User Feedback**: Approve, edit, or regenerate content

### 1.7 Final Output

- **Export**: Downloadable podcast files (audio/video)
- **Distribution**: Optional integration with podcast platforms (RSS, Spotify API)

## 2. Architecture

```
[Client (Django Templates + React)]
      |
      v
[Django Views/API]
      |
      v
[Processing Pipeline]
      |
      +--> [Input Handler]
      +--> [Dialogue Generation (GPT-4 API)]
      +--> [Speaker Assignment]
      +--> [Voice Synthesis (TTS API)]
      +--> [Video Generation (Optional)]
      +--> [Review & Approval]
      +--> [Export/Distribution]
```

## 3. Django Implementation

### 3.1 Models

```python
# podcast_generator/models.py

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class PodcastProject(models.Model):
    """Main podcast project container"""
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='podcast_projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=50, choices=[
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('review', 'Ready for Review'),
        ('completed', 'Completed')
    ], default='draft')

class InputSource(models.Model):
    """Source material for podcast generation"""
    project = models.ForeignKey(PodcastProject, on_delete=models.CASCADE, related_name='input_sources')
    source_type = models.CharField(max_length=50, choices=[
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('text', 'Text'),
    ])
    file = models.FileField(upload_to='podcast_inputs/', null=True, blank=True)
    text_content = models.TextField(null=True, blank=True)
    transcript = models.TextField(null=True, blank=True)  # For audio/video transcription

class Speaker(models.Model):
    """Speaker profile for voice synthesis"""
    name = models.CharField(max_length=100)
    voice_id = models.CharField(max_length=100)  # ID from TTS provider
    provider = models.CharField(max_length=50, choices=[
        ('elevenlabs', 'ElevenLabs'),
        ('google', 'Google TTS'),
        ('azure', 'Azure TTS'),
    ])
    style = models.CharField(max_length=100, blank=True)  # Voice style parameters
    language = models.CharField(max_length=50, default='en-US')
    
class DialogueSegment(models.Model):
    """Individual dialogue segments"""
    project = models.ForeignKey(PodcastProject, on_delete=models.CASCADE, related_name='dialogue_segments')
    speaker = models.ForeignKey(Speaker, on_delete=models.SET_NULL, null=True, related_name='dialogue_segments')
    text = models.TextField()
    order = models.IntegerField()
    audio_file = models.FileField(upload_to='podcast_audio_segments/', null=True, blank=True)
    
class PodcastOutput(models.Model):
    """Final podcast output files"""
    project = models.ForeignKey(PodcastProject, on_delete=models.CASCADE, related_name='outputs')
    output_type = models.CharField(max_length=50, choices=[
        ('audio', 'Audio'),
        ('video', 'Video'),
    ])
    file = models.FileField(upload_to='podcast_outputs/')
    duration = models.FloatField(null=True, blank=True)  # Duration in seconds
    created_at = models.DateTimeField(auto_now_add=True)
```

### 3.2 Views and API Endpoints

```python
# podcast_generator/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import PodcastProject, InputSource, Speaker, DialogueSegment, PodcastOutput
from .serializers import (
    PodcastProjectSerializer, InputSourceSerializer, 
    SpeakerSerializer, DialogueSegmentSerializer, PodcastOutputSerializer
)
from .tasks import generate_dialogue, synthesize_voice, generate_podcast

class PodcastProjectViewSet(viewsets.ModelViewSet):
    serializer_class = PodcastProjectSerializer
    
    def get_queryset(self):
        return PodcastProject.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def generate_dialogue(self, request, pk=None):
        project = self.get_object()
        task = generate_dialogue.delay(project.id)
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=True, methods=['post'])
    def synthesize_voice(self, request, pk=None):
        project = self.get_object()
        task = synthesize_voice.delay(project.id)
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=True, methods=['post'])
    def generate_podcast(self, request, pk=None):
        project = self.get_object()
        task = generate_podcast.delay(project.id)
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)

# Additional ViewSets for InputSource, Speaker, DialogueSegment, PodcastOutput
```

### 3.3 URL Configuration

```python
# podcast_generator/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'projects', views.PodcastProjectViewSet, basename='podcast-project')
# Register other viewsets

urlpatterns = [
    path('api/', include(router.urls)),
    path('', views.podcast_home, name='podcast_home'),
    path('project/<int:project_id>/', views.project_detail, name='project_detail'),
    path('project/<int:project_id>/review/', views.project_review, name='project_review'),
]
```

### 3.4 Celery Tasks

```python
# podcast_generator/tasks.py

from celery import shared_task
from .models import PodcastProject, DialogueSegment
import openai
import requests
import os
from django.conf import settings

@shared_task
def generate_dialogue(project_id):
    """Generate dialogue using GPT-4"""
    project = PodcastProject.objects.get(id=project_id)
    project.status = 'processing'
    project.save()
    
    # Get input sources
    input_sources = project.input_sources.all()
    
    # Prepare content for GPT
    content = ""
    for source in input_sources:
        if source.source_type == 'text':
            content += source.text_content + "\n\n"
        else:  # audio or video
            content += source.transcript + "\n\n"
    
    # Call GPT-4 API
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a podcast script writer."},
                {"role": "user", "content": f"Generate a podcast dialogue based on this content: {content}"}
            ]
        )
        
        # Process and save dialogue segments
        # ... (dialogue parsing and saving logic)
        
        project.status = 'review'
        project.save()
        return True
    except Exception as e:
        project.status = 'draft'
        project.save()
        raise e

@shared_task
def synthesize_voice(project_id):
    """Synthesize voice for dialogue segments"""
    project = PodcastProject.objects.get(id=project_id)
    segments = project.dialogue_segments.all().order_by('order')
    
    for segment in segments:
        if segment.speaker and not segment.audio_file:
            # Call appropriate TTS API based on speaker.provider
            # ... (TTS API call logic)
            pass
    
    return True

@shared_task
def generate_podcast(project_id):
    """Combine audio segments into final podcast"""
    # ... (audio processing logic)
    return True
```

## 4. Integration with AI Image Generation Project

The podcast generator will be integrated with the existing AI image generation project as follows:

1. **Shared Authentication**: Use the existing authentication system from the AI image generation project
2. **Unified UI**: Extend the existing UI to include podcast generation features
3. **Shared Storage**: Use the same storage backend for media files
4. **Database Integration**: Add podcast-related models to the existing database

### 4.1 Project Settings Update

```python
# settings.py additions

INSTALLED_APPS += [
    'podcast_generator',
]

# TTS API configurations
TTS_PROVIDERS = {
    'elevenlabs': {
        'api_key': os.environ.get('ELEVENLABS_API_KEY'),
        'base_url': 'https://api.elevenlabs.io/v1',
    },
    'google': {
        'api_key': os.environ.get('GOOGLE_TTS_API_KEY'),
    },
    'azure': {
        'api_key': os.environ.get('AZURE_TTS_API_KEY'),
        'region': os.environ.get('AZURE_TTS_REGION'),
    }
}

# OpenAI configuration for dialogue generation
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
```

### 4.2 Main URLs Update

```python
# Main urls.py additions

urlpatterns += [
    path('podcast/', include('podcast_generator.urls')),
]
```

## 5. User Interface Design

### 5.1 Podcast Creation Flow

1. **Project Creation**: User creates a new podcast project with title and description
2. **Input Upload**: User uploads audio, video, or text inputs
3. **Speaker Selection**: User selects or creates speaker profiles
4. **Dialogue Generation**: System generates dialogue script
5. **Review & Edit**: User reviews and edits the generated script
6. **Voice Synthesis**: System synthesizes voices for each dialogue segment
7. **Final Review**: User reviews the complete podcast
8. **Export**: User exports the final podcast in desired format

### 5.2 UI Components

- Project dashboard with list of podcast projects
- Input upload form with drag-and-drop functionality
- Speaker profile management interface
- Script editor with speaker assignment
- Audio preview player
- Export options panel

## 6. Security & Scalability

- Use Django's built-in security features for authentication and authorization
- Rate-limit API endpoints using Django REST Framework throttling
- Use Celery for asynchronous processing of long-running tasks
- Containerize with Docker; deploy on Kubernetes for scaling
- Implement caching for frequently accessed data

## 7. Future Enhancements

- Multi-language support
- Speaker emotion/style tuning
- Automated show notes and summaries
- Integration with podcast distribution platforms
- Background music and sound effects library
- AI-generated podcast artwork integration with the image generation system
- Analytics dashboard for podcast performance

## 8. Implementation Timeline

1. **Phase 1 (2 weeks)**: Core models and API endpoints
2. **Phase 2 (2 weeks)**: Dialogue generation and TTS integration
3. **Phase 3 (1 week)**: UI implementation
4. **Phase 4 (1 week)**: Testing and refinement
5. **Phase 5 (1 week)**: Integration with AI image generation project
6. **Phase 6 (1 week)**: Deployment and documentation


## Naming Convention
======================

Media File Directory Structure
-----------------------------

*   `/media/podcast-generation/`
    *   `tmp/`
        +   `voice_clones/`
        +   `scripts/`
        +   `audio/`
        +   `videos/`
        +   `lipsync/`
    *   `output/`

Naming Conventions
-----------------

### Job ID Directory

Each podcast job should have its own directory: `job_<job_id>/`

### Temporary Files

*   Voice clone: `<speaker_name>_voice_clone.json`
*   Script: `script_<job_id>.json`
*   Audio segments: `dialogue_<number>_<speaker_name>.wav`
*   Speaker videos: `<speaker_name>_video.mp4`
*   Lipsync segments: `lipsync_dialogue_<number>_<speaker_name>.mp4`

### Final Output

*   Following your suggestion: `<speaker1>-<speaker2>-<date>-podcast.mp4`
*   Example: `Austin-Dan-06-06-25-podcast.mp4`
*   For single speaker: `<speaker1>-monologue-<date>-podcast.mp4`