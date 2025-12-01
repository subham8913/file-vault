"""
User authentication middleware.

This module provides middleware for extracting and validating the UserId
from the request headers. The UserId is used to track which user is making
the request and enforce per-user rate limiting and storage quotas.
"""

import re
from django.http import JsonResponse
from ..constants import ERROR_NO_USER_ID, HTTP_400_BAD_REQUEST, MAX_USER_ID_LENGTH


class UserIdAuthenticationMiddleware:
    """
    Middleware to extract and validate the UserId header from incoming requests.
    
    This middleware looks for the 'UserId' header in incoming requests and
    attaches it to the request object as request.user_id. If the header is
    missing for API endpoints (starting with /api/), it returns a 400 error.
    
    Attributes:
        get_response: The next middleware or view in the chain
        
    Example:
        # In settings.py MIDDLEWARE:
        MIDDLEWARE = [
            ...
            'files.middleware.UserIdAuthenticationMiddleware',
            ...
        ]
        
        # In a view:
        def my_view(request):
            user_id = request.user_id  # Access the user ID
            ...
    """
    
    def __init__(self, get_response):
        """
        Initialize the middleware.
        
        Args:
            get_response: The next middleware or view in the chain
        """
        self.get_response = get_response
    
    def __call__(self, request):
        """
        Process the request to extract and validate the UserId header.
        
        This method is called for every request. It extracts the UserId
        from the HTTP_USERID header, validates it against security criteria,
        and attaches it to the request object. For API endpoints, if the 
        header is missing or invalid, it returns a 400 error.
        
        Validation includes:
        - Presence check
        - Length validation (max 255 characters)
        - Format validation (alphanumeric, dash, underscore only)
        - Protection against injection attacks
        
        Args:
            request: The Django request object
            
        Returns:
            HttpResponse: The response from the next middleware/view, or a
                         400 error if UserId is missing/invalid for API endpoints
        """
        # Extract UserId from header (Django converts HTTP headers to META keys)
        # Header "UserId" becomes "HTTP_USERID"
        user_id = request.META.get('HTTP_USERID', '').strip()
        
        # Check if this is an API endpoint
        is_api_endpoint = request.path.startswith('/api/')
        
        # For API endpoints, UserId is required and must be valid
        if is_api_endpoint:
            if not user_id:
                return JsonResponse(
                    {'error': ERROR_NO_USER_ID},
                    status=HTTP_400_BAD_REQUEST
                )
            
            # Validate UserId length
            if len(user_id) > MAX_USER_ID_LENGTH:
                return JsonResponse(
                    {
                        'error': f'UserId too long (maximum {MAX_USER_ID_LENGTH} characters)',
                        'detail': 'Please use a shorter user identifier'
                    },
                    status=HTTP_400_BAD_REQUEST
                )
            
            # Validate UserId format to prevent injection attacks
            # Allow: alphanumeric characters, hyphens, underscores, and dots
            # This prevents SQL injection, XSS, command injection, etc.
            if not re.match(r'^[a-zA-Z0-9._-]+$', user_id):
                return JsonResponse(
                    {
                        'error': 'Invalid UserId format',
                        'detail': 'UserId must contain only alphanumeric characters, dots, hyphens, and underscores'
                    },
                    status=HTTP_400_BAD_REQUEST
                )
            
            # Additional check: prevent UserId from being just dots or dashes
            # (could be used for path traversal or other attacks)
            if user_id in ['.', '..', '-', '--'] or user_id.startswith('.'):
                return JsonResponse(
                    {
                        'error': 'Invalid UserId format',
                        'detail': 'UserId cannot be composed only of special characters or start with a dot'
                    },
                    status=HTTP_400_BAD_REQUEST
                )
        
        # Attach user_id to request for use in views
        request.user_id = user_id if user_id else None
        
        # Continue to next middleware/view
        response = self.get_response(request)
        return response
    
    def process_exception(self, request, exception):
        """
        Handle exceptions during request processing.
        
        This method is called if an exception occurs during request processing.
        Currently, it doesn't perform any special handling but is included for
        completeness and future extensibility.
        
        Args:
            request: The Django request object
            exception: The exception that was raised
            
        Returns:
            None: Let Django handle the exception normally
        """
        # Let Django handle exceptions normally
        return None
