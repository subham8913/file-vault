# Testing Instructions

## Prerequisites
Ensure Docker and Docker Compose are installed and running.

## 1. Start the Application
To build and start the application:
```bash
docker-compose up --build
```
The API will be available at `http://localhost:8000`.

## 2. Run Integration Tests
Integration tests run from your local machine and test the running API container.
**Note:** The container must be running (`docker-compose up`) for these tests to pass.

The integration suite covers all functional endpoints:
- **Core**: Root API check
- **Files**: Upload, List, Retrieve, Download, Delete
- **Metadata**: Update Filename (PATCH), File Types
- **Business Logic**: Deduplication, Quotas, Rate Limiting

```bash
# Install test dependencies (if not already installed)
pip install pytest requests

# Run the tests
pytest backend/test_integration_api.py
```

## 3. Run Unit Tests
Unit tests run inside the Docker container to test internal logic.

```bash
# Run unit tests for the 'files' app
docker-compose exec backend python manage.py test files
```

## Troubleshooting
- **Port 8000 already in use**: Stop existing containers or processes using port 8000.
  To find and kill the process on macOS/Linux:
  ```bash
  lsof -i :8000
  kill -9 <PID>
  ```
- **Database errors**: If you see "no such table" errors, try removing the volume and restarting:
  ```bash
  docker-compose down -v
  docker-compose up --build
  ```

## 4. Running Locally (Without Docker)
If you prefer to run the application directly on your machine:

1.  **Navigate to the backend directory**:
    ```bash
    cd backend
    ```

2.  **Set up a virtual environment** (recommended):
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Apply database migrations**:
    ```bash
    python manage.py migrate
    ```

5.  **Run the server**:
    ```bash
    python manage.py runserver
    ```
    The API will be available at `http://localhost:8000`.

6.  **Run Tests Locally**:
    *   **Unit Tests**: `python manage.py test files`
    *   **Integration Tests**:
        Ensure the server is running in another terminal, then:
        ```bash
        pip install pytest requests
        cd ..  # Go back to project root
        pytest backend/test_integration_api.py
        ```

## 5. API Reference (cURL Commands)
Here are example cURL commands to interact with all available endpoints.
**Note**: Replace `<file_id>` with an actual UUID from your system.

### Core
**Check API Status**
```bash
curl -X GET http://localhost:8000/
```

### File Operations
**List Files**
```bash
curl -X GET http://localhost:8000/api/files/ \
  -H "UserId: test_user"
```

**Upload File**
```bash
curl -X POST http://localhost:8000/api/files/ \
  -H "UserId: test_user" \
  -F "file=@/path/to/your/file.txt"
```

**Retrieve File Details**
```bash
curl -X GET http://localhost:8000/api/files/<file_id>/ \
  -H "UserId: test_user"
```

**Download File**
```bash
curl -X GET http://localhost:8000/api/files/<file_id>/download/ \
  -H "UserId: test_user" \
  --output downloaded_file.ext
```

**Delete File**
```bash
curl -X DELETE http://localhost:8000/api/files/<file_id>/ \
  -H "UserId: test_user"
```

### Metadata & Stats
**Update File Metadata (Rename)**
```bash
curl -X PATCH http://localhost:8000/api/files/<file_id>/ \
  -H "UserId: test_user" \
  -H "Content-Type: application/json" \
  -d '{"original_filename": "new_name.txt"}'
```

**Get Storage Stats**
```bash
curl -X GET http://localhost:8000/api/files/storage_stats/ \
  -H "UserId: test_user"
```

**List File Types**
```bash
curl -X GET http://localhost:8000/api/files/file_types/ \
  -H "UserId: test_user"
```
