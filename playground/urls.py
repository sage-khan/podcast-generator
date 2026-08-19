from django.urls import path, include

urlpatterns = [
    path('google/', include('playground.google.urls')),
]
