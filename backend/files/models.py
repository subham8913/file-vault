"""
File management models for the Abnormal File Vault application.

This module defines the data models for file storage and management,
implementing a Content-Addressable Storage (CAS) pattern (Normalization).
- FileBlob: Stores the actual physical file and its hash.
- File: Stores the user's metadata and points to a FileBlob.
"""

import logging
import os
import uuid
from typing import Optional

from django.db import models
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import F

from .validators import sanitize_filename, get_file_extension
from .constants import UPLOAD_SUBDIRECTORY, MAX_FILENAME_LENGTH, MAX_FILE_TYPE_LENGTH

logger = logging.getLogger(__name__)


def file_upload_path(instance, filename: str) -> str:
    """
    Generate a secure file path for uploaded files.
    """
    # Sanitize the original filename to extract extension safely
    clean_filename = sanitize_filename(filename)
    ext = get_file_extension(clean_filename)
    
    # Generate UUID-based filename
    unique_filename = f"{uuid.uuid4()}{ext}"
    
    # Return path within uploads directory
    return os.path.join(UPLOAD_SUBDIRECTORY, unique_filename)


class FileBlob(models.Model):
    """
    Represents the physical file content (Content-Addressable Storage).
    Unique by file_hash.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    file = models.FileField(
        upload_to=file_upload_path,
        help_text="The actual file stored in the filesystem"
    )
    
    file_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="SHA256 hash of file content for deduplication"
    )
    
    size = models.BigIntegerField(
        help_text="File size in bytes"
    )
    
    reference_count = models.IntegerField(
        default=0,
        help_text="Number of User Files referencing this blob"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Blob {self.file_hash[:8]} ({self.reference_count} refs)"


class File(models.Model):
    """
    Model representing a User's view of a file.
    Points to a FileBlob for the actual content.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the file (UUID format)"
    )
    
    user_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="User ID who uploaded this file"
    )
    
    blob = models.ForeignKey(
        FileBlob,
        on_delete=models.PROTECT, # Prevent deleting blob if users still reference it
        related_name='files',
        help_text="Reference to the physical file blob"
    )
    
    original_filename = models.CharField(
        max_length=MAX_FILENAME_LENGTH,
        help_text="Original filename as provided during upload"
    )
    
    file_type = models.CharField(
        max_length=MAX_FILE_TYPE_LENGTH,
        help_text="MIME type of the file (e.g., application/pdf)"
    )
    
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the file was uploaded"
    )
    
    @property
    def size(self):
        return self.blob.size

    class Meta:
        """Model metadata."""
        ordering = ['-uploaded_at']
        verbose_name = "File"
        verbose_name_plural = "Files"
        indexes = [
            models.Index(fields=['-uploaded_at'], name='files_uploaded_idx'),
            models.Index(fields=['user_id'], name='files_user_idx'),
            models.Index(fields=['user_id', '-uploaded_at'], name='files_user_date_idx'),
        ]

    def __str__(self) -> str:
        return self.original_filename
    
    def __repr__(self) -> str:
        return f'<File: {self.id} - {self.original_filename}>'
    
    def get_size_display(self) -> str:
        size = self.size
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def delete(self, *args, **kwargs) -> tuple:
        """
        Delete the File instance and update the Blob reference count.
        If count drops to 0, delete the Blob.
        """
        blob_id = self.blob_id
        
        # Delete the user record first
        try:
            result = super().delete(*args, **kwargs)
            logger.info(f"Deleted file record: {self.id} - {self.original_filename}")
        except Exception as e:
            logger.error(f"Error deleting database record for {self.id}: {str(e)}", exc_info=True)
            raise

        # Now handle the blob cleanup
        try:
            with transaction.atomic():
                # Lock the blob to prevent race conditions
                blob = FileBlob.objects.select_for_update().get(pk=blob_id)
                blob.reference_count = F('reference_count') - 1
                blob.save()
                
                # Refresh to get the actual value after F() update
                blob.refresh_from_db()
                
                if blob.reference_count <= 0:
                    # Delete physical file
                    if blob.file and hasattr(blob.file, 'path') and os.path.isfile(blob.file.path):
                        try:
                            os.remove(blob.file.path)
                            logger.info(f"Deleted physical file: {blob.file.path}")
                        except Exception as e:
                            logger.error(f"Error deleting physical file for blob {blob.id}: {str(e)}")
                    
                    blob.delete()
                    logger.info(f"Deleted blob: {blob.id}")
                else:
                    logger.info(f"Decremented blob {blob.id} ref count to {blob.reference_count}")
                    
        except Exception as e:
            # If blob cleanup fails, we log it but don't fail the request 
            # because the user's file is already gone.
            # In a real system, this would go to a dead-letter queue or cleanup job.
            logger.error(f"Error cleaning up blob {blob_id}: {str(e)}", exc_info=True)
            
        return result

    def clean(self) -> None:
        super().clean()
        if self.original_filename and len(self.original_filename) > MAX_FILENAME_LENGTH:
            raise ValidationError({
                'original_filename': f'Filename too long (max {MAX_FILENAME_LENGTH} characters)'
            })

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        is_new = self.pk is None
        if is_new:
            logger.info(f"Creating new file: {self.original_filename}")
        else:
            logger.info(f"Updating file: {self.id} - {self.original_filename}")
        super().save(*args, **kwargs)


class UserStorageQuota(models.Model):
    """
    Track storage usage and quotas for each user.
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
        return f"{self.user_id}: {self.total_storage_used}/{self.storage_limit} bytes"
    
    def has_space_for(self, file_size: int) -> bool:
        return (self.total_storage_used + file_size) <= self.storage_limit
    
    def get_storage_stats(self) -> dict:
        from django.db.models import Sum
        
        # Get total size of all files user uploaded (before deduplication)
        # Note: We use blob__size because size is now a property on File
        original_storage = File.objects.filter(
            user_id=self.user_id
        ).aggregate(total=Sum('blob__size'))['total'] or 0
        
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
