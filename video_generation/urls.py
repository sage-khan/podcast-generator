from django.urls import path

from . import views

app_name = 'video_generation'

urlpatterns = [
    # Kling video generation endpoints
    path('generate/kling/1-6/pro/', views.generate_kling_video, name='generate_kling_video'),
    path('generate/kling/1-6/pro/<uuid:job_id>/', views.get_kling_video_status, name='get_kling_video_status'),
    
    # Kling lipsync endpoints
    path('generate/kling/lipsync/', views.generate_kling_lipsync, name='generate_kling_lipsync'),
    path('generate/kling/lipsync/<uuid:job_id>/', views.get_kling_lipsync_status, name='get_kling_lipsync_status'),
    
    # Webhook endpoints
    path('webhooks/kling/<uuid:job_id>/<str:secret>/', views.kling_video_webhook, name='kling_video_webhook'),
    path('webhooks/lipsync/<uuid:job_id>/<str:secret>/', views.kling_lipsync_webhook, name='kling_lipsync_webhook'),
    path('webhooks/google/veo/3/<uuid:job_id>/<str:secret>/', views.google_veo3_webhook, name='google_veo3_webhook'),
    
    # Google Veo 3 endpoints
    path('generate/google/veo/3/', views.generate_google_veo3_video, name='generate_google_veo3_video'),
    path('generate/google/veo/3/<uuid:job_id>/', views.get_google_veo3_status, name='get_google_veo3_status'),
]
