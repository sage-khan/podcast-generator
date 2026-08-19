from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def google_veo3_playground(request):
    """
    Render the Google Veo-3 video generation playground.
    
    This is a front-end interface for the API endpoint at:
    /api/video/generate/google/veo/3/
    
    Note: The actual video processing is handled by the video_generation app.
    This view only provides the UI for interacting with that API.
    """
    return render(request, 'google_veo3_playground.html')
