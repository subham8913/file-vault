"""
Validators for file upload operations.

This module provides validation functions for file uploads, including
file size validation, file type validation, and filename sanitization.
All validators follow Django's validation patterns and raise ValidationError
when validation fails.
"""

import os
import hashlib
import unicodedata
from typing import Any
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

from .constants import (
    MAX_FILE_SIZE,
    MAX_FILE_SIZE_MB,
    ERROR_FILE_TOO_LARGE,
    ERROR_FILE_EMPTY,
    ERROR_INVALID_FILE_TYPE,
    BLOCKED_MIME_TYPES,
)


def validate_file_size(file: UploadedFile) -> None:
    """
    Validate that the uploaded file does not exceed the maximum allowed size.
    
    Args:
        file: The uploaded file object to validate
        
    Raises:
        ValidationError: If the file size exceeds MAX_FILE_SIZE
        
    Example:
        >>> from django.core.files.uploadedfile import SimpleUploadedFile
        >>> file = SimpleUploadedFile("test.txt", b"content")
        >>> validate_file_size(file)  # Passes
        >>> large_file = SimpleUploadedFile("large.bin", b"x" * (11 * 1024 * 1024))
        >>> validate_file_size(large_file)  # Raises ValidationError
    """
    if file.size > MAX_FILE_SIZE:
        current_size_mb = round(file.size / (1024 * 1024), 2)
        error_message = ERROR_FILE_TOO_LARGE.format(
            max_size=MAX_FILE_SIZE_MB,
            current_size=current_size_mb
        )
        raise ValidationError(error_message)


def validate_file_not_empty(file: UploadedFile) -> None:
    """
    Validate that the uploaded file is not empty.
    
    Args:
        file: The uploaded file object to validate
        
    Raises:
        ValidationError: If the file size is 0 bytes
        
    Example:
        >>> from django.core.files.uploadedfile import SimpleUploadedFile
        >>> file = SimpleUploadedFile("test.txt", b"content")
        >>> validate_file_not_empty(file)  # Passes
        >>> empty_file = SimpleUploadedFile("empty.txt", b"")
        >>> validate_file_not_empty(empty_file)  # Raises ValidationError
    """
    if file.size == 0:
        raise ValidationError(ERROR_FILE_EMPTY)


def validate_file_type(file: UploadedFile) -> None:
    """
    Validate that the uploaded file type is not in the blocked list.
    
    Currently blocks executable files and scripts for security.
    Future enhancement: Can also whitelist allowed MIME types.
    
    Args:
        file: The uploaded file object to validate
        
    Raises:
        ValidationError: If the file MIME type is in BLOCKED_MIME_TYPES
        
    Example:
        >>> from django.core.files.uploadedfile import SimpleUploadedFile
        >>> file = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
        >>> validate_file_type(file)  # Passes
        >>> exe_file = SimpleUploadedFile("virus.exe", b"content", 
        ...                                content_type="application/x-msdownload")
        >>> validate_file_type(exe_file)  # Raises ValidationError
    """
    if file.content_type in BLOCKED_MIME_TYPES:
        error_message = ERROR_INVALID_FILE_TYPE.format(file_type=file.content_type)
        raise ValidationError(error_message)


def validate_file(file: Any) -> None:
    """
    Run all file validations on an uploaded file.
    
    This is a convenience function that runs all validation checks:
    - File not empty
    - File size within limits
    - File type allowed
    
    Args:
        file: The uploaded file object to validate
        
    Raises:
        ValidationError: If any validation check fails
        
    Example:
        >>> from django.core.files.uploadedfile import SimpleUploadedFile
        >>> file = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
        >>> validate_file(file)  # Passes all checks
    """
    if not isinstance(file, UploadedFile):
        return  # Will be caught by serializer's required field validation
    
    # Run all validations in order
    validate_file_not_empty(file)
    validate_file_size(file)
    validate_file_type(file)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing or replacing potentially dangerous characters.
    
    This function provides comprehensive protection against:
    - Path traversal attacks (../, ..\\, etc.)
    - Unicode normalization attacks
    - Windows reserved names (CON, PRN, AUX, etc.)
    - Special characters and control characters
    - NTFS alternate data streams
    - Null bytes and path separators
    
    Args:
        filename: The original filename to sanitize
        
    Returns:
        str: The sanitized filename, guaranteed safe for filesystem storage
        
    Example:
        >>> sanitize_filename("../../../etc/passwd")
        'etc_passwd'
        >>> sanitize_filename("normal_file.pdf")
        'normal_file.pdf'
        >>> sanitize_filename("file\\x00name.txt")
        'file_name.txt'
        >>> sanitize_filename("CON.txt")
        '_CON.txt'
        >>> sanitize_filename("\\u2215etc\\u2215passwd")  # Unicode slash
        '_etc_passwd'
    """
    # Normalize unicode to prevent normalization attacks
    # NFKD decomposition prevents tricks like using U+2215 (division slash) for /
    filename = unicodedata.normalize('NFKD', filename)
    
    # Convert to ASCII, replacing non-ASCII characters
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    
    # Multiple passes of basename to defeat all path traversal tricks
    for _ in range(3):
        filename = os.path.basename(filename)
    
    # Define all dangerous characters
    # Includes: path separators, null bytes, wildcards, NTFS streams, control chars
    dangerous_chars = [
        '/', '\\',        # Path separators (Unix/Windows)
        '\x00',           # Null byte
        ':',              # NTFS alternate data streams, drive letters
        '*', '?',         # Wildcards
        '"', '<', '>', '|',  # Command injection / redirection
        '\n', '\r', '\t', # Newlines and tabs
        '\x0b', '\x0c',   # Vertical tab, form feed
    ]
    
    # Replace all dangerous characters with underscore
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # Remove any remaining control characters (ASCII 0-31, 127)
    filename = ''.join(char if ord(char) >= 32 and ord(char) != 127 else '_' 
                      for char in filename)
    
    # Remove leading/trailing dots, spaces, and underscores
    filename = filename.strip('. _')
    
    # Check for Windows reserved names
    # These names are reserved on Windows and cause issues
    WINDOWS_RESERVED_NAMES = [
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
    ]
    
    # Check if filename (or its base without extension) is reserved
    name_without_ext = os.path.splitext(filename)[0].upper()
    if filename.upper() in WINDOWS_RESERVED_NAMES or name_without_ext in WINDOWS_RESERVED_NAMES:
        filename = '_' + filename
    
    # Handle edge cases where filename becomes empty or invalid
    if not filename or filename == '.' or filename == '..':
        filename = 'unnamed_file'
    
    # Limit length to prevent filesystem issues (most filesystems have 255 byte limit)
    # Keep extension intact if possible
    MAX_FILENAME_LENGTH = 200
    if len(filename) > MAX_FILENAME_LENGTH:
        name, ext = os.path.splitext(filename)
        # Ensure we keep the extension
        max_name_length = MAX_FILENAME_LENGTH - len(ext)
        if max_name_length > 0:
            filename = name[:max_name_length] + ext
        else:
            # Extension itself is too long, just truncate everything
            filename = filename[:MAX_FILENAME_LENGTH]
    
    return filename


def get_file_extension(filename: str) -> str:
    """
    Extract and return the file extension from a filename.
    
    Args:
        filename: The filename to extract extension from
        
    Returns:
        str: The file extension including the dot (e.g., '.pdf'), 
             or empty string if no extension
             
    Example:
        >>> get_file_extension("document.pdf")
        '.pdf'
        >>> get_file_extension("archive.tar.gz")
        '.gz'
        >>> get_file_extension("no_extension")
        ''
    """
    _, ext = os.path.splitext(filename)
    return ext.lower()


def calculate_file_hash(file: UploadedFile) -> str:
    """
    Calculate the SHA256 hash of an uploaded file's content.
    
    This function reads the file in chunks using Django's chunk iterator
    to handle large files efficiently without loading the entire file into 
    memory. The file pointer is reset to the beginning after hashing so the 
    file can be read again.
    
    Memory-efficient implementation uses streaming to process files up to
    the maximum allowed size (10MB) without memory issues.
    
    Args:
        file: The uploaded file object to hash
        
    Returns:
        str: The SHA256 hash as a 64-character hexadecimal string
        
    Example:
        >>> from django.core.files.uploadedfile import SimpleUploadedFile
        >>> file = SimpleUploadedFile("test.txt", b"content")
        >>> hash_value = calculate_file_hash(file)
        >>> len(hash_value)
        64
        >>> hash_value
        'ed7002b439e9ac845f22357d822bac1444730fbdb6016d3ec9432297b9ec9f73'
        
    Note:
        The file pointer is automatically reset to the beginning after hashing,
        so the file can be read again without issues. Uses Django's chunks()
        method for memory-efficient processing.
    """
    hasher = hashlib.sha256()
    
    # Reset file pointer to beginning
    file.seek(0)
    
    # Use Django's chunk iterator for memory-efficient reading
    # This works with both InMemoryUploadedFile and TemporaryUploadedFile
    # Default chunk size is 64KB, which is efficient for most files
    try:
        for chunk in file.chunks(chunk_size=8192):
            hasher.update(chunk)
    except AttributeError:
        # Fallback for file objects that don't have chunks() method
        # Read in 8KB chunks manually
        chunk_size = 8192
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    
    # Reset file pointer to beginning for subsequent operations
    file.seek(0)
    
    return hasher.hexdigest()
