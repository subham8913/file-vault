"""
Custom exception handlers for the files application.

This module provides custom exception handling to ensure consistent
error responses across the API. All exceptions are logged and returned
with appropriate HTTP status codes and error messages.
"""

import logging
from typing import Any, Dict, Optional

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError, APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .constants import (
    ERROR_FILE_NOT_FOUND,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
    ERROR_STORAGE_QUOTA_EXCEEDED,
)

logger = logging.getLogger(__name__)


class StorageQuotaExceeded(APIException):
    """Exception raised when user storage quota is exceeded."""
    status_code = 429
    default_detail = ERROR_STORAGE_QUOTA_EXCEEDED
    default_code = 'storage_quota_exceeded'


def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Optional[Response]:
    """
    Custom exception handler that provides consistent error responses.
    
    This handler wraps Django REST Framework's default exception handler
    and adds additional handling for Django's ValidationError and other
    exceptions. It ensures all errors are logged and returned in a
    consistent format.
    
    Args:
        exc: The exception that was raised
        context: Context dictionary containing view, request, args, kwargs
        
    Returns:
        Response: A Response object with error details, or None if the
                 exception should be handled by Django's default handler
                 
    Example Response Format:
        {
            "error": "Human-readable error message",
            "detail": "Specific error details",
            "status_code": 400
        }
    """
    # Call DRF's default exception handler first
    response = drf_exception_handler(exc, context)
    
    # If DRF didn't handle it, check for Django ValidationError
    if response is None:
        if isinstance(exc, DjangoValidationError):
            # Convert Django ValidationError to DRF response
            logger.warning(f"Validation error: {str(exc)}")
            
            # Extract error messages
            if hasattr(exc, 'message_dict'):
                error_data = exc.message_dict
            elif hasattr(exc, 'messages'):
                error_data = {'error': exc.messages}
            else:
                error_data = {'error': str(exc)}
            
            return Response(
                error_data,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        elif isinstance(exc, Http404):
            # Handle Django's Http404
            logger.warning(f"Resource not found: {str(exc)}")
            return Response(
                {'detail': ERROR_FILE_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND
            )
        
        elif isinstance(exc, FileNotFoundError):
            # Handle file system FileNotFoundError
            logger.error(f"File not found on storage: {str(exc)}")
            return Response(
                {'error': ERROR_FILE_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND
            )
        
        else:
            # Log unexpected errors
            logger.error(
                f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
                exc_info=True
            )
            # Don't expose internal errors to client
            return Response(
                {'error': 'Internal server error. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # Log the error if it was handled by DRF
    if response is not None:
        log_level = logging.WARNING if response.status_code < 500 else logging.ERROR
        logger.log(
            log_level,
            f"{exc.__class__.__name__}: {str(exc)} "
            f"(Status: {response.status_code})"
        )
    
    return response


class FileOperationException(Exception):
    """
    Custom exception for file operation failures.
    
    This exception is raised when file operations (upload, download, delete)
    fail due to storage issues or other operational problems.
    
    Attributes:
        message: Human-readable error message
        status_code: HTTP status code to return
        details: Additional error details (optional)
    """
    
    def __init__(
        self,
        message: str,
        status_code: int = HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize FileOperationException.
        
        Args:
            message: Error message to display
            status_code: HTTP status code (default 500)
            details: Additional error details dictionary
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for JSON response.
        
        Returns:
            Dictionary with error, status_code, and details
        """
        return {
            'error': self.message,
            'status_code': self.status_code,
            **self.details
        }
