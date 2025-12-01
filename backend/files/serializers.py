"""
Serializers for file management API endpoints.

This module provides DRF serializers for the File model, including
comprehensive validation for file uploads, size limits, type checking,
and deduplication support using the Normalized (CAS) architecture.
"""

import logging
from typing import Any, Dict

from rest_framework import serializers
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction, IntegrityError
from django.db.models import F

from .models import File, FileBlob, UserStorageQuota
from .exceptions import StorageQuotaExceeded
from .validators import (
    validate_file_size,
    validate_file_not_empty,
    validate_file_type,
    sanitize_filename,
    calculate_file_hash,
)
from .utils import validate_storage_quota, update_storage_usage
from .constants import (
    ERROR_FILE_EMPTY,
    USER_STORAGE_QUOTA,
    ERROR_FILE_TOO_LARGE,
    ERROR_INVALID_FILE_TYPE,
    MAX_FILE_SIZE_MB,
    SUCCESS_FILE_DEDUPLICATED,
)

logger = logging.getLogger(__name__)


class FileSerializer(serializers.ModelSerializer):
    """
    Serializer for File model with comprehensive validation.
    Handles the creation of FileBlob (physical storage) and File (user metadata).
    """
    
    file = serializers.FileField(write_only=True, required=True)
    url = serializers.SerializerMethodField()
    size = serializers.IntegerField(read_only=True)
    file_hash = serializers.CharField(source='blob.file_hash', read_only=True)
    
    class Meta:
        """Serializer metadata configuration."""
        model = File
        fields = [
            'id',
            'file',
            'url',
            'original_filename',
            'file_type',
            'size',
            'user_id',
            'file_hash',
            'uploaded_at'
        ]
        read_only_fields = ['id', 'user_id', 'file_hash', 'uploaded_at', 'original_filename', 'file_type']
        
    def get_url(self, obj) -> str:
        if obj.blob and obj.blob.file:
            return obj.blob.file.url
        return None
    
    def validate_file(self, file: UploadedFile) -> UploadedFile:
        """
        Validate the uploaded file.
        """
        if not file:
            logger.warning("File upload attempted with no file")
            raise serializers.ValidationError("No file provided")
        
        # Validate file is not empty
        try:
            validate_file_not_empty(file)
        except Exception as e:
            logger.warning(f"Empty file upload attempted: {file.name}")
            raise serializers.ValidationError(str(e))
        
        # Validate file size
        try:
            validate_file_size(file)
        except Exception as e:
            logger.warning(
                f"File too large: {file.name} ({file.size} bytes > "
                f"{MAX_FILE_SIZE_MB}MB)"
            )
            raise serializers.ValidationError(str(e))
        
        # Validate file type
        try:
            validate_file_type(file)
        except Exception as e:
            logger.warning(
                f"Blocked file type upload attempted: {file.name} "
                f"({file.content_type})"
            )
            raise serializers.ValidationError(str(e))
        
        logger.info(
            f"File validation passed: {file.name} "
            f"({file.size} bytes, {file.content_type})"
        )
        return file
    
    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and enrich the data with file metadata.
        """
        file = attrs.get('file')
        request = self.context.get('request')
        
        if file and request:
            # Get user_id from request (set by middleware)
            user_id = getattr(request, 'user_id', None)
            if not user_id:
                raise serializers.ValidationError("UserId is required")
            
            # Auto-populate original_filename if not provided
            if not attrs.get('original_filename'):
                attrs['original_filename'] = sanitize_filename(file.name)
            
            # Auto-populate file_type if not provided
            if not attrs.get('file_type'):
                attrs['file_type'] = file.content_type or 'application/octet-stream'
            
            # Auto-populate size if not provided
            if not attrs.get('size'):
                attrs['size'] = file.size
            
            # Calculate file hash for deduplication
            file_hash = calculate_file_hash(file)
            attrs['file_hash'] = file_hash
            
            # Set user_id
            attrs['user_id'] = user_id
            
        return attrs
    
    def create(self, validated_data: Dict[str, Any]) -> File:
        """
        Create a new File instance using Content-Addressable Storage.
        """
        user_id = validated_data['user_id']
        file_obj = validated_data.pop('file')
        file_hash = validated_data.pop('file_hash')
        file_size = validated_data.pop('size')
        
        with transaction.atomic():
            # 1. Check Quota
            # Lock the user's storage quota for atomic check and update
            quota, _ = UserStorageQuota.objects.select_for_update().get_or_create(
                user_id=user_id,
                defaults={'storage_limit': USER_STORAGE_QUOTA}
            )
            
            if not quota.has_space_for(file_size):
                raise StorageQuotaExceeded(
                    f'Storage Quota Exceeded. '
                    f'Current usage: {quota.total_storage_used / (1024*1024):.1f}MB / '
                    f'{quota.storage_limit / (1024*1024):.1f}MB. '
                    f'File size: {file_size / (1024*1024):.1f}MB.'
                )
            
            # 2. Get or Create Blob
            # If blob exists, we use it (deduplication). If not, we create it.
            blob, created = FileBlob.objects.get_or_create(
                file_hash=file_hash,
                defaults={
                    'file': file_obj,
                    'size': file_size,
                    'reference_count': 0
                }
            )
            
            if created:
                logger.info(f"Created new blob: {blob.id} (hash: {file_hash[:8]})")
            else:
                logger.info(f"Found existing blob: {blob.id} (hash: {file_hash[:8]}) - Deduplicating")
            
            # 3. Create User File
            file_instance = File.objects.create(
                blob=blob,
                **validated_data
            )
            
            # 4. Update Blob Ref Count
            FileBlob.objects.filter(pk=blob.pk).update(reference_count=F('reference_count') + 1)
            
            # 5. Update Quota
            UserStorageQuota.objects.filter(user_id=user_id).update(
                total_storage_used=F('total_storage_used') + file_size
            )
            
            logger.info(f"Created file record {file_instance.id} for user {user_id}")
            
            return file_instance
    
    def to_representation(self, instance: File) -> Dict[str, Any]:
        """
        Convert File instance to dictionary representation.
        """
        representation = super().to_representation(instance)
        
        # Add human-readable size
        if hasattr(instance, 'get_size_display'):
            representation['size_display'] = instance.get_size_display()
            
        # Add message if it was deduplicated (optional, but helpful for UI)
        # We can infer it if blob.reference_count > 1, but that changes over time.
        # For the immediate response, we might want to know if we just created the blob or not.
        # But 'created' variable is lost here. That's fine.
        
        return representation
