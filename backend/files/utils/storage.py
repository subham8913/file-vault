"""
Storage management utilities.

This module provides functions for managing user storage quotas,
checking available space, and updating storage usage statistics.

Author: Abnormal Security
Date: 2025-11-14
"""

import logging
from django.core.exceptions import ValidationError
from ..models import UserStorageQuota
from ..constants import (
    USER_STORAGE_QUOTA,
    ERROR_STORAGE_QUOTA_EXCEEDED,
)

logger = logging.getLogger(__name__)


def check_storage_quota(user_id: str, file_size: int) -> tuple[bool, str]:
    """
    Check if a user has sufficient storage quota for a file upload.
    
    This function retrieves or creates a UserStorageQuota record for the user
    and checks if they have enough space to upload a file of the given size.
    
    Args:
        user_id: The unique identifier for the user
        file_size: The size of the file to upload in bytes
        
    Returns:
        tuple[bool, str]: A tuple containing:
            - bool: True if user has space, False otherwise
            - str: Error message if no space, empty string if ok
            
    Example:
        >>> has_space, error = check_storage_quota('user123', 5000000)
        >>> if has_space:
        ...     # Proceed with upload
        ...     pass
        ... else:
        ...     # Return error to user
        ...     return JsonResponse({'error': error}, status=429)
    """
    # Get or create storage quota for user
    quota, created = UserStorageQuota.objects.get_or_create(
        user_id=user_id,
        defaults={'storage_limit': USER_STORAGE_QUOTA}
    )
    
    # Check if user has space for this file
    if not quota.has_space_for(file_size):
        current_mb = round(quota.total_storage_used / (1024 * 1024), 2)
        limit_mb = round(quota.storage_limit / (1024 * 1024), 2)
        file_mb = round(file_size / (1024 * 1024), 2)
        
        error_message = (
            f"{ERROR_STORAGE_QUOTA_EXCEEDED}. "
            f"Current usage: {current_mb}MB / {limit_mb}MB. "
            f"File size: {file_mb}MB."
        )
        return False, error_message
    
    return True, ""


def update_storage_usage(user_id: str, size_delta: int) -> None:
    """
    Update a user's storage usage by adding or subtracting bytes.
    
    This function updates the total_storage_used field for a user's quota.
    Use positive values to add storage (after upload) and negative values
    to subtract storage (after deletion).
    
    Includes bounds checking to prevent overflow and negative values.
    
    Args:
        user_id: The unique identifier for the user
        size_delta: The change in storage usage (positive to add, negative to subtract)
        
    Raises:
        ValueError: If the size_delta would cause storage to exceed safe limits
        
    Example:
        >>> # After successful file upload
        >>> update_storage_usage('user123', 5000000)  # Add 5MB
        
        >>> # After file deletion
        >>> update_storage_usage('user123', -5000000)  # Subtract 5MB
        
    Note:
        This function will create a UserStorageQuota record if one doesn't exist.
        Storage usage cannot go below zero or exceed safe integer limits.
    """
    # Get or create storage quota for user
    quota, created = UserStorageQuota.objects.get_or_create(
        user_id=user_id,
        defaults={'storage_limit': USER_STORAGE_QUOTA}
    )
    
    # Calculate new storage value
    new_storage = quota.total_storage_used + size_delta
    
    # Bounds checking to prevent overflow and negative values
    MAX_SAFE_STORAGE = 2**62  # Well below BigInteger limit for safety
    
    if new_storage < 0:
        logger.warning(
            f"Storage usage would be negative for user {user_id}. "
            f"Current: {quota.total_storage_used}, Delta: {size_delta}. "
            f"Setting to 0."
        )
        quota.total_storage_used = 0
    elif new_storage > MAX_SAFE_STORAGE:
        logger.error(
            f"Storage usage would exceed safe limits for user {user_id}. "
            f"Current: {quota.total_storage_used}, Delta: {size_delta}"
        )
        raise ValueError(
            f"Storage operation would exceed safe storage limits. "
            f"Please contact support."
        )
    else:
        quota.total_storage_used = new_storage
    
    quota.save()


def get_storage_stats(user_id: str) -> dict:
    """
    Get storage statistics for a user.
    
    This function retrieves detailed storage statistics including total usage,
    storage limit, original storage, and savings from deduplication.
    
    Args:
        user_id: The unique identifier for the user
        
    Returns:
        dict: A dictionary containing:
            - total_storage_used: Current storage usage in bytes
            - storage_limit: Maximum storage allowed in bytes
            - available_storage: Remaining storage in bytes
            - usage_percentage: Percentage of quota used
            - original_storage: Total size without deduplication
            - storage_saved: Bytes saved from deduplication
            - savings_percentage: Percentage saved from deduplication
            
    Example:
        >>> stats = get_storage_stats('user123')
        >>> print(f"Used {stats['usage_percentage']}% of quota")
        >>> print(f"Saved {stats['savings_percentage']}% through deduplication")
    """
    # Get or create storage quota for user
    quota, created = UserStorageQuota.objects.get_or_create(
        user_id=user_id,
        defaults={'storage_limit': USER_STORAGE_QUOTA}
    )
    
    # Get storage statistics from model
    return quota.get_storage_stats()


def validate_storage_quota(user_id: str, file_size: int) -> None:
    """
    Validate that a user has storage quota for a file, raising ValidationError if not.
    
    This is a convenience wrapper around check_storage_quota that raises
    a ValidationError instead of returning a boolean. Useful for use in
    serializer validation.
    
    Args:
        user_id: The unique identifier for the user
        file_size: The size of the file to upload in bytes
        
    Raises:
        ValidationError: If the user does not have sufficient storage quota
        
    Example:
        >>> # In a serializer validate method:
        >>> def validate(self, data):
        ...     user_id = self.context['request'].user_id
        ...     file_size = data['file'].size
        ...     validate_storage_quota(user_id, file_size)
        ...     return data
    """
    has_space, error = check_storage_quota(user_id, file_size)
    if not has_space:
        # Raise as a field error for 'file' so it appears in response.data['file']
        raise ValidationError({'file': error})
