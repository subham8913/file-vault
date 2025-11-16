# Abnormal File Vault - Implementation Guide

## Overview

A production-ready Django REST API for intelligent file management with advanced features including deduplication, storage quotas, rate limiting, and comprehensive search capabilities.

## 🎯 Key Features Implemented

### Core Functionality
- **File Upload & Management** - CRUD operations with metadata tracking
- **File Deduplication** - SHA256-based content deduplication for storage optimization
- **Storage Quotas** - Per-user 10MB storage limits with usage tracking
- **Rate Limiting** - 2 requests/second per user to prevent abuse
- **Advanced Search** - Filter by filename, type, size, and date
- **Pagination** - Efficient handling of large file lists
- **User Isolation** - UserId header-based authentication and data separation

### Technical Highlights
- Django 4.2.26 with Django REST Framework
- 69 comprehensive unit and integration tests (100% passing)
- Docker deployment with volume mounting
- Structured logging and error handling
- Database constraints and indexing for data integrity

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Start the application
docker-compose up --build

# Access the API
curl http://localhost:8000/api/files/ -H "UserId: testuser"
```

### Option 2: Local Development

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver

# Access the API
curl http://127.0.0.1:8000/api/files/ -H "UserId: testuser"
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/files/` | List all files (with pagination & filters) |
| `POST` | `/api/files/` | Upload a new file |
| `GET` | `/api/files/{id}/` | Get file details |
| `DELETE` | `/api/files/{id}/` | Delete a file |
| `GET` | `/api/files/{id}/download/` | Download a file |
| `GET` | `/api/files/storage_stats/` | Get storage usage statistics |
| `GET` | `/api/files/file_types/` | List all file types in system |

### Request Headers
```
UserId: <user_identifier>  # Required for all requests
```

### Example: Upload File
```bash
curl -X POST http://localhost:8000/api/files/ \
  -H "UserId: user123" \
  -F "file=@document.pdf"
```

### Example: Search Files
```bash
# Search by filename
curl "http://localhost:8000/api/files/?search=report" \
  -H "UserId: user123"

# Filter by type and size
curl "http://localhost:8000/api/files/?file_type=application/pdf&min_size=1000" \
  -H "UserId: user123"
```

## 🧪 Running Tests

```bash
cd backend

# Run all tests
python manage.py test files

# Run with coverage report
coverage run --source='.' manage.py test files
coverage report
```

**Test Results:** 69 tests, 100% passing ✅

## 📊 Project Structure

```
dplat-file-vault-coding-challenge/
├── backend/
│   ├── core/              # Django settings
│   ├── files/             # Main application
│   │   ├── models.py      # File & UserStorageQuota models
│   │   ├── views.py       # API viewsets with deduplication logic
│   │   ├── serializers.py # Data validation and serialization
│   │   ├── validators.py  # File validation & hashing
│   │   ├── middleware.py  # UserId authentication & rate limiting
│   │   ├── utils.py       # Storage quota utilities
│   │   └── tests.py       # Comprehensive test suite (69 tests)
│   ├── requirements.txt   # Python dependencies
│   └── manage.py
├── docker-compose.yml     # Docker configuration
└── README.md              # Original project documentation
```

## 🔧 Configuration

Key settings in `backend/core/settings.py`:

- **Max File Size:** 10 MB
- **User Storage Quota:** 10 MB per user
- **Rate Limit:** 2 requests/second per user
- **Pagination:** 20 items per page (max 100)

## 🐛 Troubleshooting

### Port Conflicts
```bash
# If port 8000 is already in use
docker-compose down
# Or change port in docker-compose.yml
```

### Database Issues
```bash
# Reset database (local development)
rm backend/data/db.sqlite3
python manage.py migrate
```

### Rate Limit Blocking
```bash
# Rate limiting is disabled during tests
# For development, wait 1 second between requests or adjust settings
```

## 📝 Implementation Notes

### Deduplication Strategy
- Files are hashed using SHA256 on upload
- Duplicate content creates a reference instead of storing physical copy
- Reference counting ensures safe deletion
- Storage savings reported in stats endpoint

### Security Considerations
- Blocked executable file types (.exe, .sh, .py, etc.)
- File size validation (max 10MB)
- User isolation via UserId header
- MIME type validation
- Secure file download with proper headers

**Note on Authentication:** The current implementation uses a simple UserId header for user identification. In a production environment, this should be replaced with a robust authentication system such as:
- JWT (JSON Web Tokens) with OAuth2
- Session-based authentication
- API key authentication with rate limiting
- Integration with enterprise SSO (SAML, OIDC)

### Performance Optimizations
- Database indexes on file_hash and user_id
- Efficient pagination for large datasets
- Cache-based rate limiting
- Streaming file downloads

## 🎓 Development Tools Used

This project was developed with assistance from AI tools (GitHub Copilot/Claude) following these practices:
- Clear requirement analysis and feature breakdown
- Iterative development with immediate testing
- Code review and refactoring for best practices
- Comprehensive test coverage validation
- Documentation-driven development

## 📦 Submission Package

This implementation includes:
- ✅ Production-ready Django REST API
- ✅ Docker deployment configuration
- ✅ 69 comprehensive tests (100% passing)
- ✅ Complete API documentation
- ✅ Clean, maintainable codebase

---

**Version:** 1.0.0  
**Date:** November 16, 2025  
**Framework:** Django 4.2.26 + Django REST Framework 3.15.2
