"""
Serializers for file management API endpoints.

This module provides DRF serializers for the File model, including
comprehensive validation for file uploads, size limits, type checking,
and deduplication support.

Author: Abnormal Security
Date: 2025-11-14
"""

import logging
from typing import Any, Dict

from rest_framework import serializers
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction, IntegrityError
from django.db.models import F

from .models import File, UserStorageQuota
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
    
    This serializer handles the serialization and deserialization of File
    instances, including validation of file uploads (size, type, content).
    It automatically extracts metadata from uploaded files and ensures
    all data meets security and business requirements.
    
    Fields:
        id (UUID): Unique identifier (read-only)
        file (File): The uploaded file with URL in response
        original_filename (str): Original name of the file
        file_type (str): MIME type (e.g., 'application/pdf')
        size (int): File size in bytes
        uploaded_at (datetime): Upload timestamp (read-only)
        
    Validation:
        - File must be present
        - File must not be empty
        - File size must not exceed 10MB
        - File type must not be in blocked list
        
    Example:
        Serialization (model to JSON):
        >>> file = File.objects.get(id=some_uuid)
        >>> serializer = FileSerializer(file)
        >>> serializer.data
        {
            'id': '550e8400-e29b-41d4-a716-446655440000',
            'file': 'http://localhost:8000/media/uploads/550e8400...pdf',
            'original_filename': 'report.pdf',
            'file_type': 'application/pdf',
            'size': 2048576,
            'uploaded_at': '2025-11-14T10:30:00Z'
        }
        
        Deserialization (JSON to model):
        >>> data = {'file': uploaded_file}
        >>> serializer = FileSerializer(data=data)
        >>> serializer.is_valid()
        True
        >>> file = serializer.save()
    """
    
    class Meta:
        """Serializer metadata configuration."""
        model = File
        fields = [
            'id',
            'file',
            'original_filename',
            'file_type',
            'size',
            'user_id',
            'file_hash',
            'is_reference',
            'uploaded_at'
        ]
        read_only_fields = ['id', 'user_id', 'file_hash', 'is_reference', 'uploaded_at']
        extra_kwargs = {
            'file': {
                'required': True,
                'allow_null': False,
                'help_text': 'The file to upload (max 10MB)'
            },
            'original_filename': {
                'required': False,  # Auto-extracted from file
                'help_text': 'Original filename (auto-detected if not provided)'
            },
            'file_type': {
                'required': False,  # Auto-extracted from file
                'help_text': 'MIME type (auto-detected if not provided)'
            },
            'size': {
                'required': False,  # Auto-extracted from file
                'help_text': 'File size in bytes (auto-detected if not provided)'
            },
        }
    
    def validate_file(self, file: UploadedFile) -> UploadedFile:
        """
        Validate the uploaded file.
        
        Runs comprehensive validation checks including:
        - File is not empty
        - File size within limits (10MB)
        - File type not blocked
        
        Args:
            file: The uploaded file object
            
        Returns:
            UploadedFile: The validated file object
            
        Raises:
            serializers.ValidationError: If validation fails
            
        Example:
            >>> serializer = FileSerializer(data={'file': uploaded_file})
            >>> serializer.is_valid()  # Calls validate_file internally
            True
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
        Validate and enrich the data with file metadata and deduplication.
        
        This method is called after field-level validation and is used to:
        1. Extract metadata from the uploaded file
        2. Auto-populate fields if not provided
        3. Sanitize filenames for security
        4. Calculate file hash for deduplication
        5. Check storage quota
        
        Args:
            attrs: Dictionary of field values
            
        Returns:
            dict: Validated and enriched attributes
            
        Raises:
            serializers.ValidationError: If validation fails
            
        Example:
            >>> data = {'file': uploaded_file}
            >>> serializer = FileSerializer(data=data, context={'request': request})
            >>> serializer.is_valid()
            True
            >>> serializer.validated_data
            {
                'file': <UploadedFile>,
                'original_filename': 'report.pdf',
                'file_type': 'application/pdf',
                'size': 2048576,
                'file_hash': 'a1b2c3...',
                'user_id': 'user123'
            }
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
                logger.debug(f"Auto-set filename: {attrs['original_filename']}")
            
            # Auto-populate file_type if not provided
            if not attrs.get('file_type'):
                attrs['file_type'] = file.content_type or 'application/octet-stream'
                logger.debug(f"Auto-set file type: {attrs['file_type']}")
            
            # Auto-populate size if not provided
            if not attrs.get('size'):
                attrs['size'] = file.size
                logger.debug(f"Auto-set size: {attrs['size']} bytes")
            
            # Calculate file hash for deduplication
            file_hash = calculate_file_hash(file)
            attrs['file_hash'] = file_hash
            logger.debug(f"Calculated file hash: {file_hash}")
            
            # Set user_id
            attrs['user_id'] = user_id
            
            # Check for existing file with same hash (deduplication)
            existing_file = File.objects.filter(
                file_hash=file_hash,
                is_reference=False  # Only look for original files
            ).first()
            
            if existing_file:
                # File is a duplicate - will create reference
                # References still count towards user quota for fairness
                validate_storage_quota(user_id, attrs['size'])
                logger.debug(f"Storage quota check passed for user {user_id}")
                
                attrs['is_reference'] = True
                attrs['original_file'] = existing_file
                attrs['_is_duplicate'] = True  # Flag for create method
                logger.info(
                    f"Duplicate file detected: {file_hash}. "
                    f"Will create reference to {existing_file.id}"
                )
            else:
                # New unique file - check storage quota
                validate_storage_quota(user_id, attrs['size'])
                logger.debug(f"Storage quota check passed for user {user_id}")
                
                attrs['is_reference'] = False
                attrs['_is_duplicate'] = False
        
        return attrs
    
    def create(self, validated_data: Dict[str, Any]) -> File:
        """
        Create a new File instance from validated data with deduplication support.
        
        This method handles both new file uploads and duplicate file references.
        For duplicates, it creates a reference record pointing to the original file
        and updates reference counts. For new files, it stores the physical file
        and updates storage usage.
        
        Uses database transactions and row-level locking to prevent race conditions
        in reference counting.
        
        Args:
            validated_data: Dictionary of validated field values
            
        Returns:
            File: The created File instance (either original or reference)
            
        Example:
            >>> serializer = FileSerializer(data={'file': uploaded_file}, context={'request': request})
            >>> serializer.is_valid()
            True
            >>> file = serializer.save()
            >>> print(f"Is reference: {file.is_reference}")
        """
        is_duplicate = validated_data.pop('_is_duplicate', False)
        user_id = validated_data['user_id']
        file_size = validated_data['size']
        
        if is_duplicate:
            # Create a reference to existing file with transaction protection
            with transaction.atomic():
                original_file = validated_data['original_file']
                
                # Lock the original file row to prevent concurrent modifications
                original_file = File.objects.select_for_update().get(pk=original_file.pk)
                
                # Lock the user's storage quota for atomic check and update
                quota, _ = UserStorageQuota.objects.select_for_update().get_or_create(
                    user_id=user_id,
                    defaults={'storage_limit': USER_STORAGE_QUOTA}
                )
                
                # Double-check quota with locked value (prevent race condition)
                if not quota.has_space_for(file_size):
                    raise serializers.ValidationError({
                        'file': f'Storage Quota Exceeded. '
                                f'Current usage: {quota.total_storage_used / (1024*1024):.1f}MB / '
                                f'{quota.storage_limit / (1024*1024):.1f}MB. '
                                f'File size: {file_size / (1024*1024):.1f}MB.'
                    })
                
                # Don't store the physical file for references
                validated_data.pop('file', None)
                
                # Create reference record
                file_instance = File.objects.create(**validated_data)
                
                # Use F() expression for atomic increment - prevents race conditions
                File.objects.filter(pk=original_file.pk).update(
                    reference_count=F('reference_count') + 1
                )
                
                # Refresh to get updated count for logging
                original_file.refresh_from_db()
                
                # Update storage usage atomically with F() expression
                UserStorageQuota.objects.filter(user_id=user_id).update(
                    total_storage_used=F('total_storage_used') + file_size
                )
                
                logger.info(
                    f"Created file reference: {file_instance.id} -> {original_file.id}. "
                    f"Reference count: {original_file.reference_count}. "
                    f"User: {user_id}"
                )
            
        else:
            # Create new file with physical storage (with retry for race condition)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    with transaction.atomic():
                        logger.info(
                            f"Creating new file: {validated_data['original_filename']} "
                            f"({file_size} bytes) for user {user_id} (attempt {attempt + 1})"
                        )
                        
                        # Lock the user's storage quota for atomic check and update
                        quota, _ = UserStorageQuota.objects.select_for_update().get_or_create(
                            user_id=user_id,
                            defaults={'storage_limit': USER_STORAGE_QUOTA}
                        )
                        
                        # Double-check quota with locked value (prevent race condition)
                        if not quota.has_space_for(file_size):
                            raise serializers.ValidationError({
                                'file': f'Storage Quota Exceeded. '
                                        f'Current usage: {quota.total_storage_used / (1024*1024):.1f}MB / '
                                        f'{quota.storage_limit / (1024*1024):.1f}MB. '
                                        f'File size: {file_size / (1024*1024):.1f}MB.'
                            })
                        
                        # Try to create the original file
                        file_instance = File.objects.create(**validated_data)
                        
                        # Update storage usage atomically with F() expression
                        UserStorageQuota.objects.filter(user_id=user_id).update(
                            total_storage_used=F('total_storage_used') + file_size
                        )
                        
                        logger.info(
                            f"File created successfully: {file_instance.id} - "
                            f"{file_instance.original_filename}. "
                            f"Updated storage for user {user_id}"
                        )
                        
                        return file_instance
                        
                except IntegrityError as e:
                    # Race condition: Another request created the same file hash
                    if 'unique_original_file_hash' in str(e).lower():
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"Race condition detected for hash {validated_data.get('file_hash')}, "
                                f"retrying as reference (attempt {attempt + 1})"
                            )
                            # Another transaction created this file, create reference instead
                            try:
                                with transaction.atomic():
                                    existing_file = File.objects.select_for_update().get(
                                        file_hash=validated_data['file_hash'],
                                        is_reference=False
                                    )
                                    
                                    # Lock quota for atomic update
                                    quota, _ = UserStorageQuota.objects.select_for_update().get_or_create(
                                        user_id=user_id,
                                        defaults={'storage_limit': USER_STORAGE_QUOTA}
                                    )
                                    
                                    # Check quota again
                                    if not quota.has_space_for(file_size):
                                        raise serializers.ValidationError({
                                            'file': f'Storage Quota Exceeded. '
                                                    f'Current usage: {quota.total_storage_used / (1024*1024):.1f}MB / '
                                                    f'{quota.storage_limit / (1024*1024):.1f}MB. '
                                                    f'File size: {file_size / (1024*1024):.1f}MB.'
                                        })
                                    
                                    # Create reference
                                    validated_data.pop('file', None)
                                    validated_data['is_reference'] = True
                                    validated_data['original_file'] = existing_file
                                    
                                    file_instance = File.objects.create(**validated_data)
                                    
                                    # Increment reference count
                                    File.objects.filter(pk=existing_file.pk).update(
                                        reference_count=F('reference_count') + 1
                                    )
                                    
                                    # Update storage
                                    UserStorageQuota.objects.filter(user_id=user_id).update(
                                        total_storage_used=F('total_storage_used') + file_size
                                    )
                                    
                                    logger.info(
                                        f"Converted to reference after race: {file_instance.id} -> "
                                        f"{existing_file.id} for user {user_id}"
                                    )
                                    
                                    return file_instance
                            except File.DoesNotExist:
                                # Original file was deleted, retry creation
                                continue
                        else:
                            logger.error(f"Max retries exceeded for deduplication race condition")
                            raise
                    else:
                        # Different integrity error, re-raise
                        raise
        
        return file_instance
    
    def to_representation(self, instance: File) -> Dict[str, Any]:
        """
        Convert File instance to dictionary representation.
        
        This method is called when serializing a File instance to JSON.
        It can be used to customize the output format.
        
        Args:
            instance: The File instance to serialize
            
        Returns:
            dict: Dictionary representation of the file
            
        Example:
            >>> file = File.objects.get(id=some_uuid)
            >>> serializer = FileSerializer(file)
            >>> serializer.data
            {
                'id': '550e8400-...',
                'file': 'http://localhost:8000/media/uploads/...',
                ...
            }
        """
        representation = super().to_representation(instance)
        
        # Add human-readable size (optional enhancement)
        if instance.size:
            representation['size_display'] = instance.get_size_display()
        
        return representation
 