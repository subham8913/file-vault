"""
API views for file management operations.

This module provides ViewSets for handling file CRUD operations through
REST API endpoints with rate limiting, deduplication, and storage quotas.
Updated to use Normalized (CAS) architecture.

Endpoints:
    GET    /api/files/              - List all files (with filtering & search)
    POST   /api/files/              - Upload a new file (with deduplication)
    GET    /api/files/{id}/         - Get file details
    DELETE /api/files/{id}/         - Delete a file (with reference counting)
    GET    /api/files/{id}/download/ - Download a file
    GET    /api/files/storage_stats/ - Get storage statistics
    GET    /api/files/file_types/   - Get list of file types
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
    """
    
    queryset = File.objects.all()
    serializer_class = FileSerializer
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['original_filename']
    filterset_fields = ['file_type']
    
    def get_queryset(self):
        """
        Get the queryset filtered by user_id and custom filters.
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
                queryset = queryset.filter(blob__size__gte=int(min_size))
            except ValueError:
                pass
        
        max_size = self.request.query_params.get('max_size')
        if max_size:
            try:
                queryset = queryset.filter(blob__size__lte=int(max_size))
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
        """
        user_id = getattr(request, 'user_id', 'unknown')
        
        try:
            logger.info(f"File upload requested by user: {user_id}")
            
            # Standard DRF create flow - serializer handles the complex logic
            return super().create(request, *args, **kwargs)
            
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
        Delete a file.
        The File model's delete() method handles the Blob reference counting and cleanup.
        """
        file_id = kwargs.get('pk')
        user_id = getattr(request, 'user_id', 'unknown')
        
        try:
            instance = self.get_object()
            file_size = instance.size
            filename = instance.original_filename
            
            logger.info(f"File delete requested: {file_id} - {filename} by user {user_id}")
            
            # Delete the file record
            # This triggers the model's delete() method which handles blob cleanup
            instance.delete()
            
            # Update storage usage for this user
            update_storage_usage(user_id, -file_size)
            
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Http404:
            logger.warning(f"Delete attempted on non-existent file: {file_id}")
            raise Http404("File not found")
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {str(e)}", exc_info=True)
            raise
    
    @action(detail=True, methods=['get'])
    @rate_limit_method()
    def download(self, request: Request, pk: str = None) -> FileResponse:
        """
        Download the physical file.
        """
        user_id = getattr(request, 'user_id', 'unknown')
        logger.info(f"File download requested: {pk} by user {user_id}")
        
        try:
            # Get file instance - may raise Http404
            file_instance = self.get_object()
            
            # Check if physical file exists
            if not file_instance.blob or not file_instance.blob.file:
                logger.error(f"Physical file missing for {pk}")
                raise Http404("Physical file not found")
            
            # Open the file from the blob
            try:
                file_handle = file_instance.blob.file.open()
                response = FileResponse(file_handle, content_type=file_instance.file_type)
                response['Content-Disposition'] = f'attachment; filename="{quote(file_instance.original_filename)}"'
                return response
            except FileNotFoundError:
                logger.error(f"Physical file not found on disk for {pk}")
                raise Http404("Physical file not found")
                
        except Http404:
            raise
        except Exception as e:
            logger.error(f"Error downloading file {pk}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Error processing download request'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    @rate_limit_method()
    def storage_stats(self, request: Request) -> Response:
        """Get storage usage statistics for the current user."""
        user_id = getattr(request, 'user_id', 'unknown')
        stats = get_storage_stats(user_id)
        return Response(stats)

    @action(detail=False, methods=['get'])
    @rate_limit_method()
    def file_types(self, request: Request) -> Response:
        """Get list of file types uploaded by the user."""
        user_id = getattr(request, 'user_id', 'unknown')
        types = File.objects.filter(user_id=user_id).values_list('file_type', flat=True).distinct()
        return Response(list(types))
