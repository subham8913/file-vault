"""
File management models for the Abnormal File Vault application.

This module defines the data models for file storage and management,
including the File model which stores metadata about uploaded files
while the actual files are stored in the filesystem.

Author: Abnormal Security
Date: 2025-11-14
"""

import logging
import os
import uuid
from typing import Optional

from django.db import models
from django.core.exceptions import ValidationError

from .validators import sanitize_filename, get_file_extension
from .constants import UPLOAD_SUBDIRECTORY, MAX_FILENAME_LENGTH, MAX_FILE_TYPE_LENGTH

logger = logging.getLogger(__name__)


def file_upload_path(instance: 'File', filename: str) -> str:
    """
    Generate a secure file path for uploaded files.
    
    This function creates a unique file path using UUID to prevent:
    - Filename collisions
    - Path traversal attacks
    - Filename enumeration
    
    The original filename is preserved in the database but not used
    in the actual file path for security reasons.
    
    Args:
        instance: The File model instance being saved
        filename: The original filename from the upload
        
    Returns:
        str: A secure file path in the format 'uploads/{uuid}.{ext}'
        
    Example:
        >>> file_upload_path(file_instance, 'report.pdf')
        'uploads/550e8400-e29b-41d4-a716-446655440000.pdf'
        
    Note:
        The extension is preserved from the original filename to maintain
        file type associations at the OS level.
    """
    # Sanitize the original filename to extract extension safely
    clean_filename = sanitize_filename(filename)
    ext = get_file_extension(clean_filename)
    
    # Generate UUID-based filename
    unique_filename = f"{uuid.uuid4()}{ext}"
    
    # Return path within uploads directory
    return os.path.join(UPLOAD_SUBDIRECTORY, unique_filename)


class File(models.Model):
    """
    Model representing an uploaded file with its metadata.
    
    This model stores metadata about uploaded files including the original
    filename, file type (MIME type), size, content hash for deduplication,
    and upload timestamp. The actual file is stored in the filesystem using
    Django's FileField with a UUID-based naming scheme for security.
    
    Attributes:
        id (UUID): Primary key, auto-generated UUID for unique identification
        file (FileField): Reference to the actual file in the filesystem
        original_filename (str): The original name of the uploaded file
        file_type (str): The MIME type of the file (e.g., 'application/pdf')
        size (int): File size in bytes
        content_hash (str): SHA256 hash of file content for deduplication
        uploaded_at (datetime): Timestamp when the file was uploaded
        
    Meta:
        ordering: Files are ordered by upload date, newest first
        
    Example:
        >>> file = File.objects.create(
        ...     file=uploaded_file,
        ...     original_filename='report.pdf',
        ...     file_type='application/pdf',
        ...     size=2048576
        ... )
        >>> print(file.id)
        UUID('550e8400-e29b-41d4-a716-446655440000')
        >>> print(file.uploaded_at)
        2025-11-14 10:30:00+00:00
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the file (UUID format)"
    )
    
    file = models.FileField(
        upload_to=file_upload_path,
        null=True,
        blank=True,
        help_text="The actual file stored in the filesystem (null for references)"
    )
    
    original_filename = models.CharField(
        max_length=MAX_FILENAME_LENGTH,
        help_text="Original filename as provided during upload"
    )
    
    file_type = models.CharField(
        max_length=MAX_FILE_TYPE_LENGTH,
        db_index=True,  # Index for filtering by file type
        help_text="MIME type of the file (e.g., application/pdf)"
    )
    
    size = models.BigIntegerField(
        help_text="File size in bytes"
    )
    
    user_id = models.CharField(
        max_length=255,
        db_index=True,
        default='unknown',  # Temporary default for migration
        help_text="User ID who uploaded this file (from UserId header)"
    )
    
    file_hash = models.CharField(
        max_length=64,
        db_index=True,
        default='0' * 64,  # Temporary default for migration
        help_text="SHA256 hash of file content for deduplication"
    )
    
    reference_count = models.IntegerField(
        default=1,
        help_text="Number of times this file is referenced (for deduplication)"
    )
    
    is_reference = models.BooleanField(
        default=False,
        help_text="True if this is a reference to another file (duplicate)"
    )
    
    original_file = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='references',
        help_text="Reference to original file if this is a duplicate"
    )
    
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the file was uploaded"
    )
    
    class Meta:
        """Model metadata."""
        ordering = ['-uploaded_at']
        verbose_name = "File"
        verbose_name_plural = "Files"
        indexes = [
            models.Index(fields=['-uploaded_at'], name='files_uploaded_idx'),
            models.Index(fields=['file_hash'], name='files_hash_idx'),
            models.Index(fields=['user_id'], name='files_user_idx'),
            models.Index(fields=['user_id', '-uploaded_at'], name='files_user_date_idx'),
            # Composite index for deduplication queries
            models.Index(fields=['file_hash', 'is_reference'], name='files_hash_ref_idx'),
        ]
        constraints = [
            # Ensure reference_count is never negative
            models.CheckConstraint(
                check=models.Q(reference_count__gte=0),
                name='reference_count_non_negative'
            ),
            # Ensure file size is never negative
            models.CheckConstraint(
                check=models.Q(size__gte=0),
                name='size_non_negative'
            ),
            # Ensure references always have an original_file set
            models.CheckConstraint(
                check=models.Q(is_reference=False) | models.Q(original_file__isnull=False),
                name='reference_has_original'
            ),
            # Ensure original files don't have original_file set
            models.CheckConstraint(
                check=models.Q(is_reference=True) | models.Q(original_file__isnull=True),
                name='original_no_reference'
            ),
            # Ensure only one original file exists per hash (prevents race condition)
            models.UniqueConstraint(
                fields=['file_hash'],
                condition=models.Q(is_reference=False),
                name='unique_original_file_hash'
            ),
        ]
    
    def __str__(self) -> str:
        """
        Return string representation of the File instance.
        
        Returns:
            str: The original filename
            
        Example:
            >>> file = File(original_filename='report.pdf')
            >>> str(file)
            'report.pdf'
        """
        return self.original_filename
    
    def __repr__(self) -> str:
        """
        Return detailed string representation for debugging.
        
        Returns:
            str: Detailed representation including ID and filename
            
        Example:
            >>> file = File(id=uuid.uuid4(), original_filename='report.pdf')
            >>> repr(file)
            '<File: 550e8400-e29b-41d4-a716-446655440000 - report.pdf>'
        """
        return f'<File: {self.id} - {self.original_filename}>'
    
    def get_size_display(self) -> str:
        """
        Get human-readable file size.
        
        Returns:
            str: File size formatted as KB, MB, or GB
            
        Example:
            >>> file = File(size=2048576)
            >>> file.get_size_display()
            '2.0 MB'
        """
        size = self.size
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def delete(self, *args, **kwargs) -> tuple:
        """
        Delete the File instance and its associated physical file.
        
        This method overrides the default delete to ensure that the
        physical file is removed from the filesystem when the database
        record is deleted. Only attempts to delete physical files for
        original files (not references).
        
        Args:
            *args: Positional arguments passed to parent delete
            **kwargs: Keyword arguments passed to parent delete
            
        Returns:
            tuple: Result from parent delete method
            
        Raises:
            Exception: If database deletion fails, the exception is re-raised
                      after attempting file cleanup
            
        Note:
            If the physical file doesn't exist or deletion fails, a warning
            is logged but the database deletion proceeds. This handles cases
            of orphaned database records or filesystem issues gracefully.
        """
        # Only delete physical files for original files, not references
        if not self.is_reference:
            try:
                # Delete the physical file if it exists
                if self.file and hasattr(self.file, 'path') and os.path.isfile(self.file.path):
                    file_path = self.file.path
                    os.remove(file_path)
                    logger.info(f"Deleted physical file: {file_path}")
                else:
                    logger.warning(
                        f"Physical file not found for deletion: {self.id}. "
                        f"Proceeding with database cleanup."
                    )
            except Exception as e:
                logger.error(
                    f"Error deleting physical file for {self.id}: {str(e)}",
                    exc_info=True
                )
                # Continue with database deletion even if file deletion fails
                # This prevents orphaned database records
        
        # Delete the database record
        try:
            result = super().delete(*args, **kwargs)
            logger.info(f"Deleted file record: {self.id} - {self.original_filename}")
            return result
        except Exception as e:
            logger.error(
                f"Error deleting database record for {self.id}: {str(e)}",
                exc_info=True
            )
            raise  # Re-raise database errors
    
    def clean(self) -> None:
        """
        Validate model fields before saving.
        
        This method is called by Django's validation system and can be
        used to add custom validation logic.
        
        Raises:
            ValidationError: If validation fails
        """
        super().clean()
        
        # Validate filename length
        if self.original_filename and len(self.original_filename) > MAX_FILENAME_LENGTH:
            raise ValidationError({
                'original_filename': f'Filename too long (max {MAX_FILENAME_LENGTH} characters)'
            })
        
        # Validate size is positive
        if self.size is not None and self.size < 0:
            raise ValidationError({
                'size': 'File size cannot be negative'
            })
    
    def save(self, *args, **kwargs) -> None:
        """
        Save the File instance with validation.
        
        This method overrides the default save to add logging and
        ensure validation is performed.
        
        Args:
            *args: Positional arguments passed to parent save
            **kwargs: Keyword arguments passed to parent save
        """
        # Run validation
        self.full_clean()
        
        # Log the save operation
        is_new = self.pk is None
        if is_new:
            logger.info(
                f"Creating new file: {self.original_filename} "
                f"({self.get_size_display()})"
            )
        else:
            logger.info(f"Updating file: {self.id} - {self.original_filename}")
        
        # Save to database
        super().save(*args, **kwargs)


class UserStorageQuota(models.Model):
    """
    Track storage usage and quotas for each user.
    
    This model maintains per-user storage statistics including:
    - Total storage used (after deduplication)
    - Storage limit (configurable per user)
    - Timestamps for tracking
    
    Attributes:
        user_id: Unique identifier for the user
        total_storage_used: Actual bytes stored after deduplication
        storage_limit: Maximum allowed storage in bytes
        created_at: When the quota record was created
        updated_at: When the quota was last updated
    """
    
    user_id = models.CharField(
        max_length=255,
        unique=True,
        primary_key=True,
        help_text="Unique user identifier"
    )
    
    total_storage_used = models.BigIntegerField(
        default=0,
        help_text="Total bytes used by this user (after deduplication)"
    )
    
    storage_limit = models.BigIntegerField(
        default=10 * 1024 * 1024,  # 10MB default
        help_text="Maximum storage allowed for this user in bytes"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this quota record was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this quota was last updated"
    )
    
    class Meta:
        """Model metadata."""
        verbose_name = "User Storage Quota"
        verbose_name_plural = "User Storage Quotas"
        indexes = [
            models.Index(fields=['user_id'], name='quota_user_idx'),
        ]
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.user_id}: {self.total_storage_used}/{self.storage_limit} bytes"
    
    def has_space_for(self, file_size: int) -> bool:
        """
        Check if user has enough storage space for a file.
        
        Args:
            file_size: Size of file in bytes
            
        Returns:
            bool: True if enough space available
        """
        return (self.total_storage_used + file_size) <= self.storage_limit
    
    def get_storage_stats(self) -> dict:
        """
        Get storage statistics for this user.
        
        Returns:
            dict: Storage statistics including savings from deduplication
        """
        from django.db.models import Sum, Q
        
        # Get total size of all files user uploaded (before deduplication)
        original_storage = File.objects.filter(
            user_id=self.user_id
        ).aggregate(total=Sum('size'))['total'] or 0
        
        # Calculate savings
        savings = original_storage - self.total_storage_used
        savings_percentage = (savings / original_storage * 100) if original_storage > 0 else 0
        
        # Calculate available storage and usage percentage
        available_storage = max(0, self.storage_limit - self.total_storage_used)
        usage_percentage = (self.total_storage_used / self.storage_limit * 100) if self.storage_limit > 0 else 0
        
        return {
            'user_id': self.user_id,
            'total_storage_used': self.total_storage_used,
            'storage_limit': self.storage_limit,
            'available_storage': available_storage,
            'usage_percentage': round(usage_percentage, 2),
            'original_storage': original_storage,
            'storage_saved': savings,
            'savings_percentage': round(savings_percentage, 2)
        }

