"""
URL configuration for the AI image generation and fine-tuning project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
"""
import os

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from rest_framework.authtoken.views import obtain_auth_token

# Swagger/OpenAPI documentation imports
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger schema configuration
schema_view = get_schema_view(
   openapi.Info(
      title="AI Media Generation Service API",
      default_version='v1',
      description="Comprehensive API for AI-powered media generation including images, audio, video, and podcasts",
      terms_of_service=os.environ.get('API_TERMS_URL', 'https://example.com/terms/'),
      contact=openapi.Contact(email=os.environ.get('API_CONTACT_EMAIL', 'api-support@example.com')),
      license=openapi.License(name="Proprietary License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

# Legacy redirect views
#from shared.views.legacy_redirects import (
#    LegacyModelTrainingView, 
#    LegacyFeedbackView, 
#    LegacyImageGenerationView
#)

# Main URL patterns
urlpatterns = [
    # Admin site
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/schema/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    
    # API endpoints
    path('api/images/', include('image_generation.urls', namespace='image_generation')),
    path('api/video/', include('video_generation.urls', namespace='video_generation')),
    path('api/audio/', include('audio_generation.urls', namespace='audio_generation')),
    path('api/models/', include('model_training.urls', namespace='model_training')),
    # path('api/feedback/', include('feedback.urls')),  # Module doesn't exist yet
    path('api/token/', obtain_auth_token, name='api_token_auth'),  # Use obtain_auth_token view directly
    path('api/podcast/', include('podcast_generator.urls')),
    
    # Legacy redirects - commented out since the views are not imported
    # path('api/models/<path:path>', LegacyModelTrainingView.as_view(), name='legacy_model_training'),
    # path('api/feedback/<path:path>', LegacyFeedbackView.as_view(), name='legacy_feedback'),
    # path('api/images/<path:path>', LegacyImageGenerationView.as_view(), name='legacy_image_generation'),
    
    # Playground UI pages
    path('playground/', include('playground.urls')),
    
    # Documentation
    # path('docs/', include('docs.urls')),  # Module doesn't exist yet
    
    # Home / landing page
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
