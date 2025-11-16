"""
Middleware package for the files application.

This package contains custom middleware for request processing,
including user authentication and rate limiting.
"""

from .authentication import UserIdAuthenticationMiddleware

__all__ = ['UserIdAuthenticationMiddleware']
