from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.views.generic.base import RedirectView
from django.urls import include
from image_generation import views

# Define the app namespace
app_name = 'image_generation'

# Create a router for viewsets
router = DefaultRouter()
router.register(r'characters', views.CharacterViewSet, basename='character')
router.register(r'poses', views.PoseViewSet, basename='pose')

# URL patterns for the image_generation app
urlpatterns = [
    # Function-based views
    path('generate/', views.generate_character, name='generate_character'),
    path('generate/status/<uuid:character_id>/', views.get_character_status, name='get_character_status'),
    path('generate/poses/', views.generate_poses, name='generate_poses'),
    path('generate/poses/status/<uuid:pose_id>/', views.get_pose_status, name='get_pose_status'),
    
    # New LoRA generation endpoints
    path('finetuned/lora/flux-1/', views.generate_with_lora, name='generate_with_lora'),
    path('finetuned/lora/flux-1/<uuid:job_id>/', views.get_lora_generation_status, name='get_lora_generation_status'),
    
    # Flux 1.1 UltraPro endpoints
    path('generate/flux/1-1/pro/', views.generate_flux_ultrapro, name='generate_flux_ultrapro'),
    path('generate/flux/1-1/pro/<uuid:job_id>/', views.get_flux_ultrapro_status, name='get_flux_ultrapro_status'),
    
    # Flux Kontext Pro endpoints
    path('generate/flux/kontext/pro/', views.generate_flux_kontextpro, name='generate_flux_kontextpro'),
    path('generate/flux/kontext/pro/<uuid:job_id>/', views.get_flux_kontextpro_status, name='get_flux_kontextpro_status'),
    
    # Flux Kontext Multi-image endpoints
    path('generate/flux/kontext/multi-image/', views.generate_flux_kontext_multi, name='generate_flux_kontext_multi'),
    path('generate/flux/kontext/multi-image/<uuid:job_id>/', views.get_flux_kontext_multi_status, name='get_flux_kontext_multi_status'),
    
    # Flux Kontext Multi-image-list endpoints
    path('generate/flux/kontext/multi-image-list/', views.generate_flux_kontext_multi_list, name='generate_flux_kontext_multi_list'),
    path('generate/flux/kontext/multi-image-list/<uuid:job_id>/', views.get_flux_kontext_multi_list_status, name='get_flux_kontext_multi_list_status'),
    
    # Webhook endpoints
    path('webhooks/character/<uuid:character_id>/<str:secret>/', views.character_webhook, name='character_webhook'),
    path('webhooks/pose/<uuid:pose_id>/<str:secret>/', views.pose_webhook, name='pose_webhook'),
    path('webhooks/lora/<uuid:job_id>/<str:secret>/', views.lora_generation_webhook, name='lora_generation_webhook'),
    path('webhooks/flux/ultrapro/<uuid:job_id>/<str:secret>/', views.flux_ultrapro_webhook, name='flux_ultrapro_webhook'),
    path('webhooks/flux/kontextpro/<uuid:job_id>/<str:secret>/', views.flux_kontextpro_webhook, name='flux_kontextpro_webhook'),
    path('webhooks/flux/kontext/multi/<uuid:job_id>/<str:secret>/', views.flux_kontext_multi_webhook, name='flux_kontext_multi_webhook'),
    path('webhooks/flux/kontext/multi-list/<uuid:job_id>/<str:secret>/', views.flux_kontext_multi_list_webhook, name='flux_kontext_multi_list_webhook'),
    
    # Model gallery view
    path('gallery/', views.model_gallery, name='model_gallery'),
    
    # Legacy URL redirects - use direct URLs instead of namespace references
    path('images/finetuned/lora/', 
         RedirectView.as_view(url='/api/images/finetuned/lora/flux-1/', permanent=False),
         name='legacy_generate_with_lora'),
    path('images/finetuned/lora/<uuid:job_id>/', 
         RedirectView.as_view(url='/api/images/finetuned/lora/flux-1/%(job_id)s/', permanent=False),
         name='legacy_get_lora_generation_status'),
    
    # ViewSet routes
    path('', include(router.urls)),
    
    # ACME Challenge URL pattern - Add this at the root level to catch all ACME challenge requests
    path('', include('shared.acme_urls')),
]

# Flux Kontext Portrait-Series URLs
urlpatterns += [
    # POST endpoint to start a portrait-series generation
    path('generate/flux/kontext/portrait-series/', views.generate_flux_kontext_portrait_series, name='generate_flux_kontext_portrait_series'),
    
    # GET endpoint to retrieve portrait-series job status
    path('generate/flux/kontext/portrait-series/<uuid:job_id>/', views.get_flux_kontext_portrait_series_status, name='get_flux_kontext_portrait_series_status'),
    
    # Webhook endpoint for Replicate to send status updates
    path('webhooks/flux/kontext/portrait-series/<uuid:job_id>/<str:secret>/', views.flux_kontext_portrait_series_webhook, name='flux_kontext_portrait_series_webhook'),
]