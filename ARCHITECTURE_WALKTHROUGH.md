# 🏛️ Architecture Walkthrough Script

This document serves as a guided explanation of the **Abnormal File Vault** architecture. It is designed to help you understand (or explain to others) exactly how the system handles files, manages storage, and ensures performance.

---

## 1. High-Level Architecture
**"The Big Picture"**

At its core, this is a **Django-based REST API** wrapped in a **Docker** container.
*   **Framework**: Django + Django REST Framework (DRF).
*   **Database**: SQLite (for simplicity/portability, but designed to be swappable for PostgreSQL).
*   **Storage**: Local filesystem (mapped via Docker volumes), but abstracted so it could be S3.

---

## 2. The Core Concept: Content-Addressable Storage (CAS)
**"Why we don't just save files directly"**

Most simple file systems save a file as `user1/my_file.txt`. We did something smarter called **Normalization**.

We split the concept of a "File" into two parts:
1.  **`FileBlob` (The Body)**: This is the actual physical data on the disk. It is identified by the **SHA-256 hash** of its content. If two users upload the exact same image, we only store **one** `FileBlob`.
2.  **`File` (The Metadata)**: This is what the user sees. It contains the filename, upload date, file type, and the owner's User ID. It points to a `FileBlob`.

**Benefit**: This gives us **Deduplication** for free. If 100 users upload the same 10MB PDF, we store 10MB total, not 1000MB.

---

## 3. The Upload Architecture (The "Write" Path)
**"What happens when you POST a file?"**

When a user sends a `POST /api/files/` request, here is the exact journey:

### Step 1: The Gatekeepers (Middleware)
*   **Rate Limiting**: Before the code even runs, we check if this specific `UserId` has made more than 2 requests in the last second. If yes -> `429 Too Many Requests`.
*   **Authentication**: We extract the `UserId` from the header.

### Step 2: Validation (Serializer)
*   **Size Check**: Is the file > 10MB? -> Reject.
*   **Type Check**: Is it a malicious executable? -> Reject.
*   **Empty Check**: Is the file 0 bytes? -> Reject.

### Step 3: The Hashing
*   We calculate the **SHA-256 hash** of the incoming file stream. This is the file's unique "fingerprint".

### Step 4: The Quota Check (Atomic Transaction)
*   We lock the user's quota record.
*   We check: `Current Usage + New File Size <= 10MB`.
*   If they don't have space -> `429 Storage Quota Exceeded`.

### Step 5: Deduplication Logic
*   We check the database: *Does a `FileBlob` with this hash already exist?*
    *   **YES**: We skip writing to disk! We just link the new `File` entry to the existing `FileBlob`. (Instant upload!)
    *   **NO**: We write the file to the `media/uploads/` directory and create a new `FileBlob` record.

### Step 6: Finalization
*   We create the `File` record linking the User to the Blob.
*   We update the user's storage usage stats.
*   We return `201 Created`.

---

## 4. The Download Architecture (The "Read" Path)
**"What happens when you GET a file?"**

When a user sends a `GET /api/files/<id>/download/` request:

### Step 1: Lookup & Permission
*   We look up the `File` record by ID.
*   **Security Check**: Does the `UserId` in the header match the `user_id` on the file? (Users can't download each other's files).

### Step 2: Blob Resolution
*   The `File` record gives us the ID of the `FileBlob`.
*   The `FileBlob` gives us the actual path on the disk (e.g., `/app/media/uploads/uuid.pdf`).

### Step 3: Streaming Response
*   We don't load the whole file into RAM (which would crash the server with large files).
*   We use Django's `FileResponse` to **stream** the file back to the client in chunks.
*   We set the correct `Content-Type` (e.g., `application/pdf`) so the browser knows how to handle it.

---

## 5. The Delete Architecture (Cleanup)
**"What happens when you DELETE a file?"**

This is tricky because of deduplication.

1.  **User deletes File A**: We delete the `File` record (metadata).
2.  **Reference Counting**: We check the `FileBlob`.
    *   If **other users** still have files pointing to this Blob -> We keep the Blob.
    *   If **no one else** points to this Blob (Ref Count == 0) -> We delete the actual physical file from the disk to free up space.
3.  **Quota Update**: We give the user their storage space back.

---

## Summary of Key Technologies
*   **Django REST Framework**: Handles the API routing and JSON serialization.
*   **SQLite**: Stores the relational data (`File` tables, `FileBlob` tables).
*   **Docker Volumes**: Persists the `media/` folder so files survive container restarts.
*   **Pytest**: Verifies all these flows work correctly.
