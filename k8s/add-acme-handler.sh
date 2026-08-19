#!/bin/bash
# Script to add an ACME challenge handler to Django

# First, let's find the main urls.py file
echo "Locating the main urls.py file..."
MAIN_URLS=$(find /path/to/podcast-generator -name urls.py | grep -v "site-packages" | head -1)
echo "Found main urls.py at: $MAIN_URLS"

# Create a Python file with the ACME challenge handler
cat <<EOF > /path/to/podcast-generator/shared/utils/acme_utils.py
from django.http import HttpResponse

def acme_challenge_view(request, challenge):
    """
    View to handle ACME challenges from Let's Encrypt.
    The value should be returned as plain text.
    """
    # Return the challenge token directly for ACME verification
    return HttpResponse(f"{challenge}.vjWQ5Y7UWbDYZ07cpG16c3wMdAL429tPyPB19lLgxfw", content_type="text/plain")
EOF

# Now, let's add the URL pattern to the main urls.py
cat <<EOF > /path/to/podcast-generator/acme_urls.py
from django.urls import path, re_path
from shared.utils.acme_utils import acme_challenge_view

urlpatterns = [
    re_path(r'^\.well-known/acme-challenge/(?P<challenge>.+)$', acme_challenge_view, name='acme-challenge'),
]
EOF

echo "Created ACME challenge handler and URL configuration"
echo "Now you need to add this to your main urls.py file with:"
echo ""
echo "from django.urls import include"
echo "urlpatterns = ["
echo "    # ... existing paths ..."
echo "    path('', include('acme_urls')),"
echo "]"
echo ""
echo "And then rebuild and redeploy your Docker container"
echo ""
echo "This will catch all ACME challenge requests at the Django level"
