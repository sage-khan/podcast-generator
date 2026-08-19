from django.urls import path

from . import views

app_name = 'audio_generation'

urlpatterns = [
    # Minimax Voice Clone endpoints
    path('generate/minimax/voice-clone/', views.generate_minimax_voice_clone, name='generate_minimax_voice_clone'),
    path('generate/minimax/voice-clone/<uuid:job_id>/', views.get_minimax_voice_clone_status, name='get_minimax_voice_clone_status'),
    
    # Minimax Speech endpoints
    path('generate/minimax/speech-02-hd/', views.generate_minimax_speech, {'model_version': 'hd'}, name='generate_minimax_speech_hd'),
    path('generate/minimax/speech-02-hd/<uuid:job_id>/', views.get_minimax_speech_status, {'model_version': 'hd'}, name='get_minimax_speech_hd_status'),
    path('generate/minimax/speech-02-turbo/', views.generate_minimax_speech, {'model_version': 'turbo'}, name='generate_minimax_speech_turbo'),
    path('generate/minimax/speech-02-turbo/<uuid:job_id>/', views.get_minimax_speech_status, {'model_version': 'turbo'}, name='get_minimax_speech_turbo_status'),
    
    # Webhook endpoints
    path('webhooks/voice-clone/<uuid:job_id>/<str:secret>/', views.minimax_voice_clone_webhook, name='minimax_voice_clone_webhook'),
    path('webhooks/speech/<uuid:job_id>/<str:secret>/', views.minimax_speech_webhook, name='minimax_speech_webhook'),
]
