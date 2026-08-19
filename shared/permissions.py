from rest_framework import permissions
import logging

logger = logging.getLogger(__name__)

class IsAuthenticatedOrWebhook(permissions.BasePermission):
    """
    Custom permission to allow webhook callbacks even without authentication,
    but require authentication for all other requests.
    
    Webhook endpoints should be secured via their unique URL structure with secrets.
    """
    
    def has_permission(self, request, view):
        # Allow webhook callbacks (which should be secured with URL secrets)
        if hasattr(view, 'webhook_endpoint') and view.webhook_endpoint:
            logger.debug("Allowing webhook request without authentication")
            return True
        
        # Require authentication for all other requests
        return request.user and request.user.is_authenticated


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admin users to create or modify objects.
    Read-only permissions are allowed for any authenticated user.
    """
    
    def has_permission(self, request, view):
        # Allow GET, HEAD or OPTIONS requests for any authenticated user
        if request.method in permissions.SAFE_METHODS and request.user and request.user.is_authenticated:
            return True
        
        # Allow only staff users to modify objects
        return request.user and request.user.is_staff
