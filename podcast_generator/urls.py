from django.urls import path

from . import views

app_name = 'podcast_generator'

urlpatterns = [
    # API endpoints
    path('create/', views.create_podcast_generation_job, name='create_podcast_generation'),
    path('status/<uuid:job_id>/', views.get_podcast_generation_status, name='get_podcast_generation_status'),
    path('jobs/', views.list_podcast_jobs, name='list_podcast_jobs'),
    path('jobs/<uuid:job_id>/cancel/', views.cancel_podcast_job, name='cancel_podcast_job'),
    path('generate-script/', views.generate_script, name='generate_script'),  # New endpoint for script generation
    
    # --- New Endpoints per 2025 README ---
    # Script generation
    path('create/script/monologue/', views.generate_script_monologue, name='generate_script_monologue'),
    path('create/script/dialogue/', views.generate_script_dialogue, name='generate_script_dialogue'),

    # Full podcast creation
    path('create/monologue/', views.create_podcast_monologue, name='create_podcast_monologue'),
    path('create/dialogue/', views.create_podcast_dialogue, name='create_podcast_dialogue'),

    # Webhook endpoints
    path('webhooks/voice-clone/<uuid:job_id>/<int:speaker_num>/', 
         views.voice_clone_webhook, 
         name='voice_clone_webhook'),
         
    path('webhooks/dialogue-audio/<uuid:job_id>/<uuid:dialogue_id>/', 
         views.dialogue_audio_webhook, 
         name='dialogue_audio_webhook'),
         
    path('webhooks/speaker-video/<uuid:job_id>/<int:speaker_num>/', 
         views.speaker_video_webhook, 
         name='speaker_video_webhook'),
         
    path('webhooks/lipsync/<uuid:job_id>/<uuid:dialogue_id>/', 
         views.lipsync_webhook, 
         name='lipsync_webhook'),
         
    path('webhooks/final-video/<uuid:job_id>/', 
         views.final_video_webhook, 
         name='final_video_webhook'),
]