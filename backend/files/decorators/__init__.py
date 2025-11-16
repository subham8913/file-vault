"""
Decorators package for the files application.

This package contains custom decorators for views and API endpoints,
including rate limiting functionality.
"""

from .rate_limit import rate_limit, rate_limit_method

__all__ = ['rate_limit', 'rate_limit_method']
