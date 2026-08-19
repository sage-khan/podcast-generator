from django.urls import path, re_path
from shared.utils.acme_utils import acme_challenge_view

urlpatterns = [
    re_path(r'^\.well-known/acme-challenge/(?P<challenge>.+)$', acme_challenge_view, name='acme-challenge'),
]
