from django.http import HttpResponse

def acme_challenge_view(request, challenge):
    """
    View to handle ACME challenges from Let's Encrypt.
    The value should be returned as plain text.
    """
    # Return the challenge token directly for ACME verification
    return HttpResponse(f"{challenge}.vjWQ5Y7UWbDYZ07cpG16c3wMdAL429tPyPB19lLgxfw", content_type="text/plain")
