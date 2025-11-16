"""
API views for file management operations.

This module provides ViewSets for handling file CRUD operations through
REST API endpoints with rate limiting, deduplication, and storage quotas.

Endpoints:
    GET    /api/files/              - List all files (with filtering & search)
    POST   /api/files/              - Upload a new file (with deduplication)
    GET    /api/files/{id}/         - Get file details
    DELETE /api/files/{id}/         - Delete a file (with reference counting)
    GET    /api/files/{id}/download/ - Download a file
    GET    /api/files/storage_stats/ - Get storage statistics
    GET    /api/files/file_types/   - Get list of file types

Author: Abnormal Security
Date: 2025-11-14
"""

import logging
import os
from typing import Any, Dict
from urllib.parse import quote

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import F
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import File, UserStorageQuota
from .serializers import FileSerializer
from .decorators import rate_limit_method
from .utils import update_storage_usage, get_storage_stats
from .constants import (
    ERROR_FILE_NOT_FOUND,
    ERROR_FILE_NOT_FOUND_STORAGE,
)

logger = logging.getLogger(__name__)


class FileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing file upload, retrieval, and deletion operations.
    
    Features:
    - Rate limiting: 2 calls per second per user
    - File deduplication with reference counting
    - Storage quotas: 10MB per user
    - Search by filename
    - Filter by file_type, min_size, max_size, start_date, end_date
    - Pagination: 20 items per page (max 100)
    """
    
    queryset = File.objects.all()
    serializer_class = FileSerializer
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['original_filename']
    filterset_fields = ['file_type']
    
    def get_queryset(self):
        """
        Get the queryset filtered by user_id and custom filters.
        
        Query Parameters:
            search: Search in filename
            file_type: Filter by MIME type
            min_size: Minimum file size in bytes
            max_size: Maximum file size in bytes
            start_date: Filter files uploaded after this date
            end_date: Filter files uploaded before this date
        """
        queryset = super().get_queryset()
        
        # Filter by user_id from request
        user_id = getattr(self.request, 'user_id', None)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Apply custom filters
        min_size = self.request.query_params.get('min_size')
        if min_size:
            try:
                queryset = queryset.filter(size__gte=int(min_size))
            except ValueError:
                pass
        
        max_size = self.request.query_params.get('max_size')
        if max_size:
            try:
                queryset = queryset.filter(size__lte=int(max_size))
            except ValueError:
                pass
        
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(uploaded_at__gte=start_date)
        
        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(uploaded_at__lte=end_date)
        
        return queryset
    
    @rate_limit_method()
    def list(self, request: Request, *args, **kwargs) -> Response:
        """List all uploaded files for the current user."""
        user_id = getattr(request, 'user_id', 'unknown')
        logger.info(f"File list requested by user: {user_id}")
        
        try:
            response = super().list(request, *args, **kwargs)
            file_count = response.data.get('count', 0) if isinstance(response.data, dict) else len(response.data)
            logger.info(f"File list returned for user {user_id}: {file_count} files")
            return response
        except Exception as e:
            logger.error(f"Error listing files for user {user_id}: {str(e)}", exc_info=True)
            raise
    
    @rate_limit_method()
    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        Upload a new file with validation, deduplication, and storage quota check.
        
        If the file already exists (same SHA256 hash), a reference is created
        instead of storing a duplicate, saving storage space.
        """
        user_id = getattr(request, 'user_id', 'unknown')
        
        try:
            logger.info(f"File upload requested by user: {user_id}")
            
            file_obj = request.FILES.get('file')
            if not file_obj:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Use serializer for validation and creation
            data = {'file': file_obj}
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            file_instance = serializer.instance
            logger.info(
                f"File {'reference' if file_instance.is_reference else 'upload'} successful: "
                f"{file_instance.id} - {file_instance.original_filename} for user {user_id}"
            )
            
            # Add message if it's a duplicate
            response_data = serializer.data
            if file_instance.is_reference:
                response_data['message'] = 'File already exists, reference created (deduplication)'
            
            headers = self.get_success_headers(response_data)
            return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
            
        except Exception as e:
            logger.error(f"Error uploading file for user {user_id}: {str(e)}", exc_info=True)
            raise
    
    @rate_limit_method()
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        """Get details of a specific file."""
        return super().retrieve(request, *args, **kwargs)
    
    @rate_limit_method()
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """
        Delete a file with reference counting and transaction protection.
        
        If this is a reference, delete the record and decrement original's count.
        If this is an original file:
        - Decrement reference_count
        - Only delete physical file if count reaches 0
        - Update storage usage
        
        Uses database transactions and row-level locking to prevent race conditions.
        """
        file_id = kwargs.get('pk')
        user_id = getattr(request, 'user_id', 'unknown')
        
        try:
            with transaction.atomic():
                # Lock the row to prevent concurrent modifications
                instance = File.objects.select_for_update().select_related('original_file').get(pk=file_id)
                
                filename = instance.original_filename
                file_size = instance.size
                is_reference = instance.is_reference
                original_file = instance.original_file
                
                logger.info(
                    f"File delete requested: {file_id} - {filename} by user {user_id}. "
                    f"Is reference: {is_reference}"
                )
                
                if is_reference and original_file:
                    # Lock the original file to prevent race conditions
                    original_file = File.objects.select_for_update().get(pk=original_file.pk)
                    
                    # Use F() expression for atomic decrement
                    updated_count = File.objects.filter(pk=original_file.pk).update(
                        reference_count=F('reference_count') - 1
                    )
                    
                    if updated_count == 0:
                        logger.error(
                            f"Failed to update reference count for {original_file.id}. "
                            f"File may have been deleted."
                        )
                        raise Http404("Original file not found")
                    
                    # Delete the reference record
                    instance.delete()
                    
                    # Refresh to get updated count for logging
                    original_file.refresh_from_db()
                    logger.info(
                        f"Decremented reference count for original {original_file.id}. "
                        f"New count: {original_file.reference_count}"
                    )
                    
                    # Update storage usage for this user (references counted towards quota)
                    update_storage_usage(user_id, -file_size)
                else:
                    # This is an original file - handle reference counting
                    if instance.reference_count > 1:
                        # Other users still reference this file
                        # Use F() for atomic decrement
                        File.objects.filter(pk=instance.pk).update(
                            reference_count=F('reference_count') - 1
                        )
                        instance.refresh_from_db()
                        logger.info(
                            f"Decremented reference count for {file_id}. "
                            f"New count: {instance.reference_count}"
                        )
                    else:
                        # No more references - safe to delete physical file
                        instance.delete()
                        logger.info(f"File and physical storage deleted: {file_id}")
                    
                    # Update storage usage for this user
                    update_storage_usage(user_id, -file_size)
            
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except File.DoesNotExist:
            logger.warning(f"Delete attempted on non-existent file: {file_id}")
            raise Http404("File not found")
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {str(e)}", exc_info=True)
            raise
    
    @action(detail=True, methods=['get'])
    @rate_limit_method()
    def download(self, request: Request, pk: str = None) -> FileResponse:
        """
        Download the physical file with proper resource management.
        
        For references, download from the original file.
        Uses Django's file object for proper handle management.
        """
        user_id = getattr(request, 'user_id', 'unknown')
        logger.info(f"File download requested: {pk} by user {user_id}")
        
        try:
            # Get file instance - may raise Http404
            file_instance = self.get_object()
        except Http404:
            logger.warning(f"Download attempted on non-existent file: {pk}")
            return Response(
                {'error': ERROR_FILE_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # If this is a reference, get the original file
            if file_instance.is_reference and file_instance.original_file:
                file_instance = file_instance.original_file
            
            # Check if physical file exists
            if not file_instance.file or not os.path.exists(file_instance.file.path):
                logger.error(
                    f"Physical file not found: {pk} - {file_instance.original_filename}"
                )
                return Response(
                    {'error': ERROR_FILE_NOT_FOUND_STORAGE},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Use Django's file object - it handles cleanup properly
            # FileResponse will close the file when the response is consumed
            response = FileResponse(
                file_instance.file.open('rb'),
                content_type=file_instance.file_type,
                as_attachment=True,
                filename=file_instance.original_filename
            )
            
            # Set security and metadata headers
            response['Content-Length'] = file_instance.size
            response['X-Content-Type-Options'] = 'nosniff'
            
            # Properly escape filename in Content-Disposition header
            # Use RFC 5987 encoding for international characters
            safe_filename = quote(file_instance.original_filename)
            response['Content-Disposition'] = (
                f'attachment; '
                f'filename="{file_instance.original_filename}"; '
                f"filename*=UTF-8''{safe_filename}"
            )
            
            logger.info(
                f"File download started: {pk} - {file_instance.original_filename}"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error downloading file {pk}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'File download failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    @rate_limit_method()
    def storage_stats(self, request: Request) -> Response:
        """
        Get storage statistics for the current user.
        
        Returns total storage used, limit, original storage, and savings from deduplication.
        """
        user_id = getattr(request, 'user_id', None)
        if not user_id:
            return Response(
                {'error': 'UserId is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            stats = get_storage_stats(user_id)
            logger.info(f"Storage stats retrieved for user {user_id}")
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting storage stats for user {user_id}: {str(e)}", exc_info=True)
            raise
    
    @action(detail=False, methods=['get'])
    @rate_limit_method()
    def file_types(self, request: Request) -> Response:
        """
        Get list of unique file types for the current user.
        
        Returns array of MIME types that the user has uploaded.
        """
        user_id = getattr(request, 'user_id', None)
        if not user_id:
            return Response(
                {'error': 'UserId is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get unique file types for this user
            file_types = File.objects.filter(
                user_id=user_id
            ).values_list('file_type', flat=True).distinct().order_by('file_type')
            
            logger.info(f"File types retrieved for user {user_id}: {len(file_types)} types")
            return Response(list(file_types), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting file types for user {user_id}: {str(e)}", exc_info=True)
            raise
