# 🏗️ Abnormal File Vault - Design Document

**Version:** 1.0  
**Date:** November 14, 2025  
**Status:** Design Phase  
**Classification:** Internal Development Document

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [System Architecture](#system-architecture)
4. [Data Models](#data-models)
5. [API Design](#api-design)
6. [Security Considerations](#security-considerations)
7. [Error Handling Strategy](#error-handling-strategy)
8. [Testing Strategy](#testing-strategy)
9. [Deployment Architecture](#deployment-architecture)
10. [Performance Considerations](#performance-considerations)
11. [Monitoring & Logging](#monitoring--logging)
12. [Future Enhancements](#future-enhancements)

---

## 1. Executive Summary

### 1.1 Project Overview
**Abnormal File Vault** is a secure, RESTful file management service built on Django and Django REST Framework. It provides a robust backend API for file upload, storage, retrieval, and management operations with enterprise-grade security and scalability.

### 1.2 Key Objectives
- ✅ Provide secure file upload and storage capabilities
- ✅ Implement RESTful API following industry best practices
- ✅ Ensure data integrity and file security
- ✅ Support containerized deployment
- ✅ Maintain high code quality and test coverage
- ✅ Enable easy scalability and maintenance

### 1.3 Target Users
- **Developers:** API consumers building file management features
- **System Administrators:** Deployment and maintenance personnel
- **End Users:** Indirect beneficiaries through integrated applications

---

## 2. Problem Statement

### 2.1 Core Problem
Modern applications require reliable, secure file storage with proper metadata management. Building file storage from scratch for each application is time-consuming, error-prone, and often lacks proper security measures.

### 2.2 Solution
A centralized, API-driven file management service that:
- Abstracts file storage complexity
- Provides consistent file handling across applications
- Enforces security policies (file size, type validation)
- Maintains comprehensive file metadata
- Offers easy integration through RESTful endpoints

### 2.3 Success Criteria
1. **Functionality:** All CRUD operations work correctly
2. **Security:** Files are validated and stored securely
3. **Reliability:** 99.9% uptime in production environment
4. **Performance:** File uploads < 2s for files under 10MB
5. **Maintainability:** >80% test coverage, clear documentation
6. **Scalability:** Handle 1000+ concurrent users

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                            │
│  (Web Apps, Mobile Apps, CLI Tools, Third-party Services)      │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS/REST API
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY LAYER                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Django Application (Port 8000)                          │  │
│  │  - URL Routing                                           │  │
│  │  - Authentication/Authorization (Future)                 │  │
│  │  - Rate Limiting (Future)                                │  │
│  │  - Request Validation                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐ │
│  │   ViewSets      │  │   Serializers   │  │   Validators   │ │
│  │  - FileViewSet  │  │ - FileSerializer│  │ - Size Check   │ │
│  │  - CRUD Logic   │  │ - Data Transform│  │ - Type Check   │ │
│  │  - Custom Acts  │  │ - Validation    │  │ - Security     │ │
│  └─────────────────┘  └─────────────────┘  └────────────────┘ │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA ACCESS LAYER                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Django ORM                                              │  │
│  │  - Models (File)                                         │  │
│  │  - QuerySets                                             │  │
│  │  - Database Abstraction                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┴────────────────┐
         ▼                                ▼
┌──────────────────┐            ┌──────────────────┐
│  DATABASE LAYER  │            │  STORAGE LAYER   │
│                  │            │                  │
│  SQLite (Dev)    │            │  File System     │
│  PostgreSQL      │            │  - /media/       │
│  (Production)    │            │  - uploads/      │
│                  │            │                  │
│  - File Metadata │            │  - Actual Files  │
│  - Relationships │            │  - Binary Data   │
└──────────────────┘            └──────────────────┘
```

### 3.2 Component Description

#### 3.2.1 Client Layer
- **Purpose:** Interface for consuming the API
- **Components:** Web browsers, mobile apps, CLI tools, third-party services
- **Communication:** HTTPS REST API calls with JSON payloads

#### 3.2.2 API Gateway Layer
- **Purpose:** Entry point, routing, and security enforcement
- **Components:**
  - Django URL dispatcher
  - Middleware stack (CSRF, CORS, Security)
  - Request/Response handlers
- **Responsibilities:**
  - Route incoming requests
  - Validate request format
  - Apply security policies
  - Handle CORS for frontend integration

#### 3.2.3 Application Layer
- **Purpose:** Business logic and data transformation
- **Components:**
  - **ViewSets:** Handle HTTP methods and orchestrate operations
  - **Serializers:** Transform data between JSON and Python objects
  - **Validators:** Enforce business rules and constraints
- **Responsibilities:**
  - Implement CRUD operations
  - File upload/download logic
  - Data validation
  - Error handling
  - Response formatting

#### 3.2.4 Data Access Layer
- **Purpose:** Abstract database operations
- **Components:**
  - Django ORM
  - Model definitions
  - Query optimization
- **Responsibilities:**
  - CRUD operations on database
  - Transaction management
  - Query optimization
  - Data integrity enforcement

#### 3.2.5 Storage Layer
- **Purpose:** Persist files and metadata
- **Components:**
  - **Database:** SQLite (dev), PostgreSQL (prod)
  - **File System:** Local storage (dev), S3/Cloud Storage (prod)
- **Responsibilities:**
  - Store file metadata in database
  - Store actual files in file system
  - Maintain referential integrity

### 3.3 Request Flow Diagram

```
┌──────────┐
│  Client  │
└────┬─────┘
     │ 1. POST /api/files/ (multipart/form-data)
     ▼
┌────────────────────┐
│  Django Middleware │  2. CSRF Check, CORS, Security Headers
└────────┬───────────┘
         │ 3. Route to FileViewSet
         ▼
┌────────────────────┐
│    FileViewSet     │  4. Invoke create() method
│    (views.py)      │
└────────┬───────────┘
         │ 5. Pass data to serializer
         ▼
┌────────────────────┐
│   FileSerializer   │  6. Validate file size, type
│  (serializers.py)  │  7. Transform data
└────────┬───────────┘
         │ 8. Validation passed
         ▼
┌────────────────────┐
│   File Model       │  9. Create database record
│   (models.py)      │ 10. Save file to storage
└────────┬───────────┘
         │ 11. Return File instance
         ▼
┌────────────────────┐
│   FileSerializer   │ 12. Serialize response data
└────────┬───────────┘
         │ 13. Return JSON response
         ▼
┌────────────────────┐
│    FileViewSet     │ 14. Set status code (201)
└────────┬───────────┘
         │ 15. Send HTTP response
         ▼
┌────────────────────┐
│      Client        │ 16. Receive file metadata
└────────────────────┘
```

---

## 4. Data Models

### 4.1 File Model

#### 4.1.1 Entity Relationship Diagram
```
┌─────────────────────────────────────────────────────────┐
│                     File Model                          │
├─────────────────────────────────────────────────────────┤
│ PK  id                UUID (Primary Key, Auto-generated)│
│     file              FileField (Path to actual file)   │
│     original_filename CharField(255) (Original name)    │
│     file_type         CharField(100) (MIME type)        │
│     size              BigIntegerField (Bytes)           │
│     content_hash      CharField(64) (SHA256 hash)       │
│     uploaded_at       DateTimeField (Auto timestamp)    │
├─────────────────────────────────────────────────────────┤
│ Indexes:                                                │
│   - Primary Key on id                                   │
│   - Index on uploaded_at (for sorting)                  │
│   - Unique Index on content_hash (deduplication)        │
│                                                         │
│ Constraints:                                            │
│   - id: Unique, Not Null                               │
│   - file: Not Null                                     │
│   - original_filename: Not Null, Max 255 chars         │
│   - file_type: Not Null, Max 100 chars                │
│   - size: Not Null, Positive Integer                   │
│   - content_hash: Unique, Not Null                     │
│   - uploaded_at: Not Null, Auto-set                    │
└─────────────────────────────────────────────────────────┘
```

#### 4.1.2 Field Specifications

| Field | Type | Constraints | Purpose | Example |
|-------|------|-------------|---------|---------|
| `id` | UUIDField | PK, Auto, Unique | Unique identifier, prevents enumeration attacks | `550e8400-e29b-41d4-a716-446655440000` |
| `file` | FileField | Not Null, upload_to='uploads/' | Reference to physical file | `uploads/550e8400-e29b-41d4-a716-446655440000.pdf` |
| `original_filename` | CharField(255) | Not Null | User-provided filename for display | `quarterly_report.pdf` |
| `file_type` | CharField(100) | Not Null | MIME type for content negotiation | `application/pdf` |
| `size` | BigIntegerField | Not Null, Positive | File size in bytes for validation | `2048576` (2MB) |
| `content_hash` | CharField(64) | Unique, Not Null | SHA256 hash for deduplication | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `uploaded_at` | DateTimeField | Not Null, Auto-add | Timestamp for auditing and sorting | `2025-11-14T08:45:00Z` |

#### 4.1.3 Business Rules

1. **UUID Generation:**
   - Auto-generated on object creation
   - Immutable after creation
   - Provides 128-bit unique identifier
   - Prevents sequential ID enumeration attacks

2. **File Storage:**
   - Files stored with UUID-based names
   - Original filename preserved in metadata
   - Files organized in `uploads/` directory
   - Extension preserved from original file

3. **Size Constraints:**
   - Maximum file size: 10,485,760 bytes (10MB)
   - Validated before saving to storage
   - Enforced at serializer level

4. **File Type Handling:**
   - MIME type extracted from uploaded file
   - Stored for content-type header in downloads
   - Can be used for file type restrictions (future)

5. **File Deduplication:**
   - SHA256 hash calculated during upload
   - Duplicate files (same hash) return existing file reference
   - Saves storage space and prevents redundant uploads
   - Hash stored in database for quick lookup

6. **Ordering:**
   - Default ordering: newest first (`-uploaded_at`)
   - Enables chronological file listing

### 4.2 Database Schema (SQLite/PostgreSQL)

```sql
CREATE TABLE files_file (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file            VARCHAR(100) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_type       VARCHAR(100) NOT NULL,
    size            BIGINT NOT NULL CHECK (size >= 0),
    content_hash    VARCHAR(64) NOT NULL UNIQUE,
    uploaded_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_files_uploaded_at ON files_file(uploaded_at DESC);
CREATE UNIQUE INDEX idx_files_content_hash ON files_file(content_hash);
```

### 4.3 File Storage Strategy

```
media/
└── uploads/
    ├── 550e8400-e29b-41d4-a716-446655440000.pdf
    ├── 7d8f2e9a-3c1b-4567-89ab-cdef01234567.jpg
    ├── 9a8b7c6d-5e4f-3210-fedc-ba9876543210.docx
    └── ...
```

**Storage Characteristics:**
- **Path Pattern:** `media/uploads/{UUID}.{extension}`
- **Benefits:**
  - No filename conflicts (UUID uniqueness)
  - No path traversal vulnerabilities
  - Easy to clean up orphaned files
  - Scalable to millions of files
- **Considerations:**
  - Original filename stored in database
  - Extension preserved for OS compatibility
  - Directory structure can be sharded if needed (future)

---

## 5. API Design

### 5.1 RESTful Principles

The API follows REST architectural constraints:
1. **Client-Server Separation:** Clear boundary between client and server
2. **Statelessness:** Each request contains all necessary information
3. **Cacheability:** Responses explicitly indicate cacheability
4. **Uniform Interface:** Consistent resource naming and HTTP methods
5. **Layered System:** Client unaware of intermediate layers

### 5.2 API Endpoints Specification

#### 5.2.1 List Files

**Endpoint:** `GET /api/files/`

**Purpose:** Retrieve paginated list of all uploaded files with metadata, supports search and filtering

**Request:**
```http
GET /api/files/ HTTP/1.1
Host: localhost:8000
Accept: application/json
```

**Query Parameters:**
- `?search=report` - Search by filename (case-insensitive)
- `?file_type=application/pdf` - Filter by MIME type
- `?page=2` - Pagination page number (default: 1)
- `?page_size=20` - Items per page (default: 20, max: 100)

**Example with Parameters:**
```http
GET /api/files/?search=report&page=1&page_size=10 HTTP/1.1
```

**Response (200 OK):**
```json
{
  "count": 45,
  "next": "http://localhost:8000/api/files/?page=2",
  "previous": null,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "file": "http://localhost:8000/media/uploads/550e8400-e29b-41d4-a716-446655440000.pdf",
      "original_filename": "quarterly_report.pdf",
      "file_type": "application/pdf",
      "size": 2048576,
      "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "uploaded_at": "2025-11-14T08:45:00Z"
    }
  ]
}
```

**Response Headers:**
```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: no-cache
X-Content-Type-Options: nosniff
```

**Error Responses:**
- `500 Internal Server Error` - Database connection failure

---

#### 5.2.2 Upload File

**Endpoint:** `POST /api/files/`

**Purpose:** Upload a new file with automatic metadata extraction and deduplication

**Request:**
```http
POST /api/files/ HTTP/1.1
Host: localhost:8000
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary
Accept: application/json

------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="report.pdf"
Content-Type: application/pdf

[Binary file content]
------WebKitFormBoundary--
```

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "file": "http://localhost:8000/media/uploads/550e8400-e29b-41d4-a716-446655440000.pdf",
  "original_filename": "report.pdf",
  "file_type": "application/pdf",
  "size": 2048576,
  "uploaded_at": "2025-11-14T10:15:30Z"
}
```

**Response Headers:**
```http
HTTP/1.1 201 Created
Content-Type: application/json
Location: /api/files/550e8400-e29b-41d4-a716-446655440000/
X-Content-Type-Options: nosniff
```

**Validation Rules:**
1. **File Presence:** File field is required
2. **File Size:** Maximum 10,485,760 bytes (10MB)
3. **Content Type:** Must be a valid file (not empty)
4. **Filename:** Original filename preserved

**Error Responses:**

**400 Bad Request - No File:**
```json
{
  "error": "No file provided"
}
```

**400 Bad Request - File Too Large:**
```json
{
  "file": [
    "File size must not exceed 10MB. Current size: 15.5MB"
  ]
}
```

**400 Bad Request - Invalid File:**
```json
{
  "file": [
    "The submitted file is empty."
  ]
}
```

**500 Internal Server Error - Storage Failure:**
```json
{
  "error": "File storage failed. Please try again."
}
```

---

#### 5.2.3 Get File Details

**Endpoint:** `GET /api/files/{id}/`

**Purpose:** Retrieve metadata for a specific file

**Request:**
```http
GET /api/files/550e8400-e29b-41d4-a716-446655440000/ HTTP/1.1
Host: localhost:8000
Accept: application/json
```

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "file": "http://localhost:8000/media/uploads/550e8400-e29b-41d4-a716-446655440000.pdf",
  "original_filename": "quarterly_report.pdf",
  "file_type": "application/pdf",
  "size": 2048576,
  "uploaded_at": "2025-11-14T08:45:00Z"
}
```

**Error Responses:**

**404 Not Found:**
```json
{
  "detail": "Not found."
}
```

---

#### 5.2.4 Download File

**Endpoint:** `GET /api/files/{id}/download/`

**Purpose:** Download the actual file with proper headers

**Request:**
```http
GET /api/files/550e8400-e29b-41d4-a716-446655440000/download/ HTTP/1.1
Host: localhost:8000
Accept: */*
```

**Response (200 OK):**
```http
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="quarterly_report.pdf"
Content-Length: 2048576
X-Content-Type-Options: nosniff

[Binary file content]
```

**Response Headers:**
- `Content-Type`: Original MIME type from upload
- `Content-Disposition`: attachment with original filename
- `Content-Length`: File size in bytes
- `X-Content-Type-Options`: nosniff (security)

**Error Responses:**

**404 Not Found - File Record Missing:**
```json
{
  "error": "File not found"
}
```

**404 Not Found - Physical File Missing:**
```json
{
  "error": "File not found on storage"
}
```

**500 Internal Server Error:**
```json
{
  "error": "File download failed"
}
```

---

#### 5.2.5 Delete File

**Endpoint:** `DELETE /api/files/{id}/`

**Purpose:** Delete file and its metadata

**Request:**
```http
DELETE /api/files/550e8400-e29b-41d4-a716-446655440000/ HTTP/1.1
Host: localhost:8000
```

**Response (204 No Content):**
```http
HTTP/1.1 204 No Content
```

**Behavior:**
1. Delete database record
2. Delete physical file from storage
3. Return 204 No Content on success

**Error Responses:**

**404 Not Found:**
```json
{
  "detail": "Not found."
}
```

**500 Internal Server Error:**
```json
{
  "error": "File deletion failed"
}
```

---

### 5.3 HTTP Status Code Usage

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Successful GET, file list, file details, download |
| 201 | Created | Successful file upload |
| 204 | No Content | Successful file deletion |
| 400 | Bad Request | Validation errors, missing file, file too large |
| 404 | Not Found | File ID doesn't exist |
| 500 | Internal Server Error | Database errors, storage failures |

---

## 6. Security Considerations

### 6.1 File Upload Security

#### 6.1.1 File Size Validation
**Threat:** Denial of Service (DoS) through large file uploads

**Mitigation:**
- Hard limit: 10MB per file
- Enforced at serializer level before storage
- Clear error message to user
- Configurable via settings

```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
```

#### 6.1.2 File Type Validation
**Threat:** Malicious file uploads (executables, scripts)

**Mitigation:**
- MIME type validation
- File extension whitelist (future)
- Content scanning (future, for production)
- Store files with UUID names (prevents execution)

#### 6.1.3 Filename Sanitization
**Threat:** Path traversal attacks, XSS in filenames

**Mitigation:**
- Store files with UUID-based names
- Original filename stored separately in database
- No direct user input in file paths
- Filename sanitized in Content-Disposition header

#### 6.1.4 File Storage Location
**Threat:** Direct web access to uploaded files

**Mitigation:**
- Files stored outside webroot in production
- Access only through download endpoint
- Proper file permissions (640)
- UUID prevents guessing file names

### 6.2 API Security

#### 6.2.1 CSRF Protection
**Status:** Enabled (Django default)

**Implementation:**
- CSRF token required for POST, PUT, DELETE
- Exempt for API with token authentication (future)

#### 6.2.2 CORS Configuration
**Status:** Configured via django-cors-headers (future)

**Settings:**
- Whitelist allowed origins
- Restrict methods and headers
- Handle preflight requests

#### 6.2.3 SQL Injection Prevention
**Status:** Protected (Django ORM)

**Implementation:**
- All queries use Django ORM
- Parameterized queries by default
- No raw SQL without escaping

#### 6.2.4 XSS Prevention
**Status:** Protected (JSON API)

**Implementation:**
- JSON responses (not HTML)
- Content-Type: application/json
- X-Content-Type-Options: nosniff header
- Original filenames escaped in headers

### 6.3 Authentication & Authorization (Future)

**Current State:** Open API (no authentication)

**Production Requirements:**
- JWT token authentication
- User-based file ownership
- Permission-based access control
- API rate limiting

---

## 7. Error Handling Strategy

### 7.1 Error Response Format

**Standardized Error Structure:**
```json
{
  "error": "Human-readable error message",
  "code": "ERROR_CODE",
  "details": {
    "field": ["Specific validation error"]
  }
}
```

### 7.2 Error Categories

#### 7.2.1 Validation Errors (400)
**Cause:** Client sends invalid data

**Examples:**
- Missing required file
- File too large
- Invalid file type
- Empty file

**Response:**
```json
{
  "file": [
    "File size must not exceed 10MB. Current size: 15.5MB"
  ]
}
```

#### 7.2.2 Not Found Errors (404)
**Cause:** Resource doesn't exist

**Examples:**
- Invalid file ID
- Deleted file
- Physical file missing

**Response:**
```json
{
  "detail": "Not found."
}
```

#### 7.2.3 Server Errors (500)
**Cause:** Internal server issues

**Examples:**
- Database connection failure
- File system full
- Permission errors

**Response:**
```json
{
  "error": "Internal server error. Please try again later."
}
```

**Logging:** All 500 errors logged with full stack trace

### 7.3 Error Logging

**Log Levels:**
- **ERROR:** 500 errors, critical failures
- **WARNING:** Validation failures, suspicious activity
- **INFO:** Successful operations
- **DEBUG:** Detailed flow information

**Log Format:**
```
[2025-11-14 10:15:30] ERROR [files.views] File upload failed for user anonymous: Disk full
Traceback: ...
```

---

## 8. Testing Strategy

### 8.1 Test Pyramid

```
                    ▲
                   /E\         E2E Tests (10%)
                  /───\        - Full workflow tests
                 /     \       - Browser/API testing
                /───────\      
               /  I N T  \     Integration Tests (20%)
              /───────────\    - API endpoint tests
             /             \   - Database interactions
            /───────────────\  
           /   U  N  I  T   \  Unit Tests (70%)
          /─────────────────\  - Model tests
         /                   \ - Serializer tests
        /─────────────────────\- Validator tests
```

### 8.2 Test Coverage Requirements

**Minimum Coverage:** 80% overall

**Component-Specific:**
- Models: 100%
- Serializers: 100%
- Views: 90%
- Utilities: 100%

### 8.3 Test Categories

#### 8.3.1 Unit Tests

**File Model Tests (`TestFileModel`):**
```python
class TestFileModel:
    - test_file_creation()              # Create file with all fields
    - test_uuid_generation()            # UUID auto-generated
    - test_file_upload_path()           # Correct path generation
    - test_str_representation()         # String method returns filename
    - test_ordering()                   # Files ordered by upload date
    - test_metadata_fields()            # All metadata stored correctly
```

**File Serializer Tests (`TestFileSerializer`):**
```python
class TestFileSerializer:
    - test_valid_file_serialization()   # Valid data serializes
    - test_file_size_validation()       # Rejects files > 10MB
    - test_empty_file_validation()      # Rejects empty files
    - test_missing_file_validation()    # Requires file field
    - test_read_only_fields()           # ID, uploaded_at read-only
    - test_metadata_extraction()        # Extracts name, type, size
```

**File Validator Tests (`TestFileValidators`):**
```python
class TestFileValidators:
    - test_validate_file_size_valid()   # Accepts files <= 10MB
    - test_validate_file_size_invalid() # Rejects files > 10MB
    - test_validate_file_type_valid()   # Accepts allowed types
    - test_validate_file_type_invalid() # Rejects blocked types
```

#### 8.3.2 Integration Tests

**File ViewSet Tests (`TestFileViewSet`):**
```python
class TestFileViewSet:
    - test_list_files()                 # GET /api/files/ returns list
    - test_list_files_empty()           # Returns [] when no files
    - test_create_file_valid()          # POST with valid file succeeds
    - test_create_file_missing()        # POST without file fails
    - test_create_file_too_large()      # POST with large file fails
    - test_retrieve_file()              # GET /api/files/{id}/ succeeds
    - test_retrieve_nonexistent()       # GET invalid ID returns 404
    - test_delete_file()                # DELETE removes file
    - test_delete_nonexistent()         # DELETE invalid ID returns 404
    - test_download_file()              # GET download returns file
    - test_download_missing_file()      # Download missing file fails
```

#### 8.3.3 End-to-End Tests

**Complete Workflows:**
```python
class TestFileWorkflow:
    - test_upload_list_download_delete() # Full CRUD workflow
    - test_multiple_file_uploads()       # Upload multiple files
    - test_concurrent_uploads()          # Concurrent upload handling
```

### 8.4 Test Data Management

**Test Fixtures:**
- Sample files (various sizes, types)
- Mock file objects
- Temporary test database
- Isolated test media directory

**Cleanup:**
- Delete test files after each test
- Reset database to clean state
- Clear test media directory

---

## 9. Deployment Architecture

### 9.1 Development Environment

```
┌─────────────────────────────────────────┐
│        Developer Workstation            │
│  ┌───────────────────────────────────┐  │
│  │   Python Virtual Environment      │  │
│  │   - Django 4.2.26                 │  │
│  │   - Django REST Framework         │  │
│  │   - Development dependencies      │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │   Django Dev Server               │  │
│  │   Port: 8000                      │  │
│  │   - Auto-reload enabled           │  │
│  │   - Debug mode ON                 │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │   SQLite Database                 │  │
│  │   Location: backend/data/         │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │   File Storage                    │  │
│  │   Location: backend/media/        │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### 9.2 Docker Development Environment

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Host                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │         file-vault-backend Container                  │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  Gunicorn WSGI Server (Port 8000)               │  │  │
│  │  │  Workers: 4                                      │  │  │
│  │  │  Threads: 2                                      │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  Django Application                              │  │  │
│  │  │  - REST API                                      │  │  │
│  │  │  - Static file serving (WhiteNoise)             │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  SQLite Database                                 │  │  │
│  │  │  Volume: ./data:/app/data                       │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  Media Files                                     │  │  │
│  │  │  Volume: ./media:/app/media                     │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
      │
      └─ Port Mapping: 8000:8000
      └─ Network: bridge
```

**Docker Compose Configuration:**
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend/data:/app/data
      - ./backend/media:/app/media
    environment:
      - DEBUG=False
      - SECRET_KEY=${SECRET_KEY}
    command: gunicorn core.wsgi:application --bind 0.0.0.0:8000
```

### 9.3 Production Environment (Recommended)

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    │   (HTTPS/SSL)   │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
    ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
    │ App Server 1  │ │ App Server 2  │ │ App Server N  │
    │ Gunicorn      │ │ Gunicorn      │ │ Gunicorn      │
    │ + Django      │ │ + Django      │ │ + Django      │
    └───────┬───────┘ └───────┬───────┘ └───────┬───────┘
            │                  │                  │
            └──────────────────┼──────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
    ┌─────────────────┐  ┌─────────────────┐
    │   PostgreSQL    │  │   S3/Cloud      │
    │   (Primary)     │  │   Storage       │
    │   + Replica     │  │   (Files)       │
    └─────────────────┘  └─────────────────┘
```

**Production Components:**
1. **Load Balancer:** Nginx/AWS ALB with SSL termination
2. **App Servers:** Multiple Gunicorn instances
3. **Database:** PostgreSQL with replication
4. **File Storage:** AWS S3 or similar
5. **Caching:** Redis for sessions/cache (future)
6. **Monitoring:** Prometheus + Grafana
7. **Logging:** ELK Stack or CloudWatch

---

## 10. Performance Considerations

### 10.1 Response Time Targets

| Operation | Target | Acceptable | Notes |
|-----------|--------|------------|-------|
| List Files | < 200ms | < 500ms | Depends on file count |
| Upload File (< 1MB) | < 500ms | < 1s | Network dependent |
| Upload File (10MB) | < 2s | < 5s | Network dependent |
| Get Details | < 100ms | < 300ms | Single DB query |
| Download File | Varies | Varies | Network/file size dependent |
| Delete File | < 200ms | < 500ms | DB + file deletion |

### 10.2 Optimization Strategies

#### 10.2.1 Database Optimization
- Index on `uploaded_at` for sorting
- Connection pooling (production)
- Query optimization with `select_related`
- Database query logging in development

#### 10.2.2 File Upload Optimization
- Stream large files (avoid loading in memory)
- Chunked upload support (future)
- Background processing for large files (future)
- Async uploads with Celery (future)

#### 10.2.3 Caching Strategy (Future)
- Cache file list responses
- Cache file metadata
- CDN for file downloads
- Redis for session storage

### 10.3 Scalability Considerations

**Horizontal Scaling:**
- Stateless application design
- Shared database and file storage
- Load balancer distribution
- Auto-scaling based on load

**Vertical Scaling:**
- CPU: Multi-process Gunicorn
- Memory: Appropriate worker count
- Storage: SSD for database
- Network: High bandwidth for uploads

---

## 11. Monitoring & Logging

### 11.1 Application Logging

**Log Locations:**
- Development: Console output
- Production: File + centralized logging

**Log Categories:**
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'files': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    },
}
```

### 11.2 Metrics to Monitor

**Application Metrics:**
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- Upload success rate
- Average file size

**System Metrics:**
- CPU usage
- Memory usage
- Disk usage (storage)
- Network I/O
- Database connections

**Business Metrics:**
- Total files uploaded
- Total storage used
- Files per user (future)
- Popular file types

### 11.3 Alerting Rules

**Critical Alerts:**
- Error rate > 5%
- Response time p95 > 5s
- Disk usage > 90%
- Database connection failures

**Warning Alerts:**
- Error rate > 1%
- Response time p95 > 2s
- Disk usage > 75%
- High memory usage

---

## 12. Future Enhancements

### 12.1 Short-term (Next Sprint)

1. **User Authentication**
   - JWT token authentication
   - User registration/login
   - File ownership

2. **Advanced File Management**
   - File search by name
   - Filter by file type
   - Sort options (name, size, date)
   - Pagination

3. **File Type Restrictions**
   - Whitelist/blacklist file types
   - Configurable restrictions
   - Better MIME type validation

### 12.2 Medium-term (Next Quarter)

4. **File Versioning**
   - Keep multiple versions of files
   - Version history
   - Restore previous versions

5. **File Sharing**
   - Generate shareable links
   - Expiring links
   - Access control

6. **Thumbnails & Previews**
   - Generate thumbnails for images
   - Preview for documents
   - Video thumbnails

7. **Batch Operations**
   - Bulk upload
   - Bulk download (zip)
   - Bulk delete

### 12.3 Long-term (Next Year)

8. **Cloud Storage Integration**
   - AWS S3 backend
   - Google Cloud Storage
   - Azure Blob Storage

9. **Advanced Security**
   - Virus scanning
   - Encryption at rest
   - Encryption in transit
   - Audit logging

10. **Analytics Dashboard**
    - Storage usage charts
    - Upload trends
    - User activity
    - File type distribution

11. **API Rate Limiting**
    - Per-user rate limits
    - IP-based throttling
    - Quota management

---

## Appendix A: Technology Stack Details

### Core Dependencies

```
Django==4.2.26              # Web framework
djangorestframework==3.16.1 # REST API framework
gunicorn==23.0.0            # WSGI server
whitenoise==6.11.0          # Static file serving
python-dotenv==1.2.1        # Environment variables
pathspec==0.11.2            # Path matching
requests==2.32.5            # HTTP library
```

### Development Dependencies (Future)

```
pytest==7.4.0               # Testing framework
pytest-django==4.5.2        # Django testing
pytest-cov==4.1.0           # Coverage reporting
black==23.7.0               # Code formatting
flake8==6.1.0               # Linting
mypy==1.5.0                 # Type checking
```

---

## Appendix B: Configuration Reference

### Environment Variables

```bash
# Django Settings
DEBUG=False                              # Debug mode (True in dev)
SECRET_KEY=your-secret-key-here         # Django secret key
ALLOWED_HOSTS=localhost,127.0.0.1       # Allowed hostnames

# Database
DATABASE_URL=sqlite:///db.sqlite3       # Database connection string

# File Storage
MEDIA_ROOT=/app/media                   # File storage location
MEDIA_URL=/media/                       # Media URL prefix

# File Upload
MAX_FILE_SIZE=10485760                  # 10MB in bytes

# Security
CORS_ALLOWED_ORIGINS=http://localhost:3000  # CORS origins (future)
```

---

## Appendix C: API Testing Examples

### Using cURL

```bash
# List files
curl http://localhost:8000/api/files/

# Upload file
curl -X POST http://localhost:8000/api/files/ \
  -F "file=@/path/to/file.pdf"

# Get file details
curl http://localhost:8000/api/files/{uuid}/

# Download file
curl -O http://localhost:8000/api/files/{uuid}/download/

# Delete file
curl -X DELETE http://localhost:8000/api/files/{uuid}/
```

### Using Python Requests

```python
import requests

# List files
response = requests.get('http://localhost:8000/api/files/')
files = response.json()

# Upload file
with open('document.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/api/files/', files=files)
    file_data = response.json()

# Download file
response = requests.get(f'http://localhost:8000/api/files/{file_id}/download/')
with open('downloaded.pdf', 'wb') as f:
    f.write(response.content)
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-14 | Development Team | Initial design document |

---

## Approval

**Technical Lead:** _________________ Date: _________

**Product Owner:** _________________ Date: _________

**Security Review:** _________________ Date: _________

---

*This document is confidential and intended for internal use only.*
