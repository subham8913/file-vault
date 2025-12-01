"""
Constants and configuration values for the files application.

This module contains all configuration constants used throughout the files app,
following the principle of avoiding magic numbers and centralized configuration.
"""

# File Upload Constraints
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB in bytes
MAX_FILE_SIZE_MB = 10  # For human-readable error messages

# User Storage & Rate Limiting
USER_STORAGE_QUOTA = 10 * 1024 * 1024  # 10 MB per user default
RATE_LIMIT_CALLS = 2  # Maximum calls per time window
RATE_LIMIT_SECONDS = 1  # Time window in seconds
RATE_LIMIT_CACHE_KEY_PREFIX = 'rate_limit'  # Cache key prefix for rate limiting

# File name constraints
MAX_FILENAME_LENGTH = 255
MAX_FILE_TYPE_LENGTH = 100
MAX_USER_ID_LENGTH = 255

# Storage paths
UPLOAD_SUBDIRECTORY = 'uploads'

# Allowed MIME types (future use - currently all types allowed)
# When enabled, only these MIME types will be accepted
ALLOWED_MIME_TYPES = [
    # Documents
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain',
    'text/csv',
    
    # Images
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/bmp',
    'image/webp',
    'image/svg+xml',
    
    # Archives
    'application/zip',
    'application/x-rar-compressed',
    'application/x-7z-compressed',
    'application/x-tar',
    'application/gzip',
    
    # Other
    'application/json',
    'application/xml',
]

# Blocked MIME types (security - executable files)
# These will always be rejected regardless of ALLOWED_MIME_TYPES
BLOCKED_MIME_TYPES = [
    'application/x-msdownload',  # .exe
    'application/x-msdos-program',
    'application/x-executable',
    'application/x-sharedlib',
    'application/x-sh',
    'application/x-shellscript',
    'text/x-python',
    'text/x-php',
    'application/javascript',
]

# Error messages
ERROR_NO_FILE = 'No file provided'
ERROR_FILE_TOO_LARGE = 'File size must not exceed {max_size}MB. Current size: {current_size}MB'
ERROR_FILE_EMPTY = 'The submitted file is empty'
ERROR_INVALID_FILE_TYPE = 'File type "{file_type}" is not allowed'
ERROR_FILE_NOT_FOUND = 'File not found'
ERROR_FILE_NOT_FOUND_STORAGE = 'File not found on storage'
ERROR_FILE_UPLOAD_FAILED = 'File upload failed. Please try again.'
ERROR_FILE_DOWNLOAD_FAILED = 'File download failed'
ERROR_FILE_DELETE_FAILED = 'File deletion failed'
ERROR_NO_USER_ID = 'UserId header is required'
ERROR_RATE_LIMIT_EXCEEDED = 'Call Limit Reached'
ERROR_STORAGE_QUOTA_EXCEEDED = 'Storage Quota Exceeded'

# Success messages
SUCCESS_FILE_UPLOADED = 'File uploaded successfully'
SUCCESS_FILE_DELETED = 'File deleted successfully'
SUCCESS_FILE_DEDUPLICATED = 'File already exists, returning reference'

# HTTP Status codes (for reference and consistency)
HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_204_NO_CONTENT = 204
HTTP_400_BAD_REQUEST = 400
HTTP_404_NOT_FOUND = 404
HTTP_429_TOO_MANY_REQUESTS = 429
HTTP_500_INTERNAL_SERVER_ERROR = 500

# Logging
LOG_FILE_UPLOAD = 'File upload: {filename} ({size} bytes) by {user}'
LOG_FILE_DOWNLOAD = 'File download: {file_id} ({filename}) by {user}'
LOG_FILE_DELETE = 'File delete: {file_id} ({filename}) by {user}'
LOG_ERROR_UPLOAD = 'File upload failed: {error}'
LOG_ERROR_DOWNLOAD = 'File download failed: {error}'
LOG_ERROR_DELETE = 'File delete failed: {error}'
