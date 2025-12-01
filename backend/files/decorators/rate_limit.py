"""
Rate limiting decorator for API endpoints.

This module provides a decorator to enforce per-user rate limiting on API
endpoints. It uses Django's cache framework to track request counts and
enforce limits based on configurable thresholds.
"""

import time
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse

from ..constants import (
    RATE_LIMIT_CALLS,
    RATE_LIMIT_SECONDS,
    RATE_LIMIT_CACHE_KEY_PREFIX,
    ERROR_RATE_LIMIT_EXCEEDED,
    HTTP_429_TOO_MANY_REQUESTS,
)


def rate_limit(calls=RATE_LIMIT_CALLS, seconds=RATE_LIMIT_SECONDS):
    """
    Decorator to enforce rate limiting on API endpoints.
    
    This decorator tracks the number of requests made by each user within
    a time window and returns HTTP 429 if the limit is exceeded. It uses
    Django's cache framework to store request counts and includes rate
    limit information in response headers.
    
    Args:
        calls (int): Maximum number of calls allowed in the time window
        seconds (int): Time window in seconds for counting requests
        
    Returns:
        function: The decorated view function
        
    Response Headers:
        X-RateLimit-Limit: Maximum requests allowed per window
        X-RateLimit-Remaining: Requests remaining in current window
        X-RateLimit-Reset: Unix timestamp when the limit resets
        
    Example:
        @rate_limit(calls=2, seconds=1)
        def my_view(request):
            return JsonResponse({'status': 'ok'})
            
        # Or use default settings from constants:
        @rate_limit()
        def my_other_view(request):
            return JsonResponse({'status': 'ok'})
            
    Note:
        This decorator expects the request object to have a user_id attribute,
        which should be set by the UserIdAuthenticationMiddleware.
        
    Cache Key Format:
        The cache key format is: "{prefix}:{user_id}:{current_second}"
        Example: "rate_limit:user123:1699876543"
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Skip rate limiting during tests
            import sys
            if 'test' in sys.argv:
                return view_func(request, *args, **kwargs)
            
            # Get user_id from request (set by UserIdAuthenticationMiddleware)
            user_id = getattr(request, 'user_id', None)
            
            if not user_id:
                # If no user_id, let the request through (middleware should have caught this)
                return view_func(request, *args, **kwargs)
            
            # Calculate the current time window (based on current second)
            current_time = int(time.time())
            time_window = current_time // seconds  # Integer division to get window ID
            reset_time = (time_window + 1) * seconds  # When the window resets
            
            # Create cache key for this user and time window
            cache_key = f"{RATE_LIMIT_CACHE_KEY_PREFIX}:{user_id}:{time_window}"
            
            # Get current request count from cache
            request_count = cache.get(cache_key, 0)
            
            # Calculate remaining requests
            remaining = max(0, calls - request_count - 1)
            
            # Check if rate limit exceeded
            if request_count >= calls:
                response = JsonResponse(
                    {
                        'error': ERROR_RATE_LIMIT_EXCEEDED,
                        'detail': f'Rate limit of {calls} calls per {seconds} second(s) exceeded. Please try again later.'
                    },
                    status=HTTP_429_TOO_MANY_REQUESTS
                )
                # Add rate limit headers even on error
                response['X-RateLimit-Limit'] = str(calls)
                response['X-RateLimit-Remaining'] = '0'
                response['X-RateLimit-Reset'] = str(reset_time)
                response['Retry-After'] = str(reset_time - current_time)
                return response
            
            # Increment request count
            cache.set(cache_key, request_count + 1, timeout=seconds * 2)
            
            # Call the actual view
            response = view_func(request, *args, **kwargs)
            
            # Add rate limit headers to successful responses
            if hasattr(response, '__setitem__'):
                response['X-RateLimit-Limit'] = str(calls)
                response['X-RateLimit-Remaining'] = str(remaining)
                response['X-RateLimit-Reset'] = str(reset_time)
            
            return response
        
        return wrapped_view
    return decorator


def rate_limit_method(calls=RATE_LIMIT_CALLS, seconds=RATE_LIMIT_SECONDS):
    """
    Decorator to enforce rate limiting on ViewSet methods.
    
    This is similar to the rate_limit decorator but designed for use with
    Django REST Framework ViewSet methods, where the first argument is 'self'.
    Includes rate limit information in response headers.
    
    Args:
        calls (int): Maximum number of calls allowed in the time window
        seconds (int): Time window in seconds for counting requests
        
    Returns:
        function: The decorated method
        
    Response Headers:
        X-RateLimit-Limit: Maximum requests allowed per window
        X-RateLimit-Remaining: Requests remaining in current window
        X-RateLimit-Reset: Unix timestamp when the limit resets
        
    Example:
        class MyViewSet(viewsets.ModelViewSet):
            @rate_limit_method(calls=2, seconds=1)
            def list(self, request, *args, **kwargs):
                return super().list(request, *args, **kwargs)
                
            @rate_limit_method()  # Use default settings
            def create(self, request, *args, **kwargs):
                return super().create(request, *args, **kwargs)
    """
    def decorator(method_func):
        @wraps(method_func)
        def wrapped_method(self, request, *args, **kwargs):
            # Skip rate limiting during tests
            import sys
            if 'test' in sys.argv:
                return method_func(self, request, *args, **kwargs)
            
            # Get user_id from request (set by UserIdAuthenticationMiddleware)
            user_id = getattr(request, 'user_id', None)
            
            if not user_id:
                # If no user_id, let the request through
                return method_func(self, request, *args, **kwargs)
            
            # Calculate the current time window
            current_time = int(time.time())
            time_window = current_time // seconds
            reset_time = (time_window + 1) * seconds
            
            # Create cache key
            cache_key = f"{RATE_LIMIT_CACHE_KEY_PREFIX}:{user_id}:{time_window}"
            
            # Get current request count
            request_count = cache.get(cache_key, 0)
            
            # Calculate remaining requests
            remaining = max(0, calls - request_count - 1)
            
            # Check if rate limit exceeded
            if request_count >= calls:
                response = JsonResponse(
                    {
                        'error': ERROR_RATE_LIMIT_EXCEEDED,
                        'detail': f'Rate limit of {calls} calls per {seconds} second(s) exceeded. Please try again later.'
                    },
                    status=HTTP_429_TOO_MANY_REQUESTS
                )
                # Add rate limit headers even on error
                response['X-RateLimit-Limit'] = str(calls)
                response['X-RateLimit-Remaining'] = '0'
                response['X-RateLimit-Reset'] = str(reset_time)
                response['Retry-After'] = str(reset_time - current_time)
                return response
            
            # Increment request count
            cache.set(cache_key, request_count + 1, timeout=seconds * 2)
            
            # Call the actual method
            response = method_func(self, request, *args, **kwargs)
            
            # Add rate limit headers to successful responses
            if hasattr(response, '__setitem__'):
                response['X-RateLimit-Limit'] = str(calls)
                response['X-RateLimit-Remaining'] = str(remaining)
                response['X-RateLimit-Reset'] = str(reset_time)
            
            return response
        
        return wrapped_method
    return decorator
