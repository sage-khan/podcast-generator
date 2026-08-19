from django.urls import path
from .views import google_veo3_playground

urlpatterns = [
    path('', google_veo3_playground, name='google_veo3_playground'),
]
