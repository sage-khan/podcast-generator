from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.views.generic.base import RedirectView
from django.urls import include
from model_training import views

app_name = 'model_training'

# Create a router for viewsets
router = DefaultRouter()
router.register(r'models', views.TrainedModelViewSet, basename='trained_model')

# URL patterns for the model_training app
urlpatterns = [
    # LoRA fine-tuning endpoints
    path('finetune/lora/', views.finetune_lora, name='finetune_lora'),
    path('finetune/lora/<uuid:job_id>/', views.lora_job_detail, name='lora_job_detail'),
    path('finetune/lora/status/<uuid:job_id>/', views.get_lora_training_status, name='get_lora_training_status'),
    
    # Webhook endpoints
    path('webhooks/lora/<uuid:job_id>/<str:secret>/', views.lora_webhook, name='lora_webhook'),
    
    # ViewSet routes
    path('', include(router.urls)),
    
    # ACME Challenge URL pattern - Add this at the root level to catch all ACME challenge requests
    path('', include('shared.acme_urls')),
]