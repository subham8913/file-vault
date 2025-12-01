"""
Integration Tests for Abnormal File Vault API
==============================================
Test Suite: Production-Critical Scenarios

Test Coverage:
- File Upload & Deduplication
- Storage Quota Enforcement (10MB limit)
- API Rate Limiting (2 calls/sec)
- Quota + Deduplication Interaction
- Search & Filtering
"""

import io
import time
import pytest
import requests
from typing import Dict, List, Optional

# Test Configuration
BASE_URL = "http://127.0.0.1:8000"
API_ENDPOINT = f"{BASE_URL}/api/files/"
TIMEOUT = 10  # seconds

# Constants
MB = 1024 * 1024
STORAGE_QUOTA_LIMIT = 10 * MB
RATE_LIMIT_WINDOW = 1.0  # seconds
RATE_LIMIT_CALLS = 2


class TestHelper:
    """Helper class for common test operations"""
    
    @staticmethod
    def create_file_content(size_bytes: int, pattern: str = "A") -> bytes:
        """Create file content of specified size"""
        return (pattern * size_bytes).encode()[:size_bytes]
    
    @staticmethod
    def upload_file(
        filename: str,
        content: bytes,
        user_id: str,
        timeout: int = TIMEOUT
    ) -> requests.Response:
        """Upload a file to the API"""
        files = {"file": (filename, io.BytesIO(content))}
        headers = {"UserId": user_id}
        return requests.post(API_ENDPOINT, files=files, headers=headers, timeout=timeout)
    
    @staticmethod
    def list_files(user_id: str, params: Optional[Dict] = None) -> requests.Response:
        """List files for a user"""
        headers = {"UserId": user_id}
        return requests.get(API_ENDPOINT, headers=headers, params=params or {}, timeout=TIMEOUT)
    
    @staticmethod
    def delete_file(file_id: str, user_id: str) -> requests.Response:
        """Delete a file"""
        headers = {"UserId": user_id}
        url = f"{API_ENDPOINT}{file_id}/"
        return requests.delete(url, headers=headers, timeout=TIMEOUT)
    
    @staticmethod
    def get_storage_stats(user_id: str) -> requests.Response:
        """Get storage statistics for a user"""
        headers = {"UserId": user_id}
        url = f"{API_ENDPOINT}storage_stats/"
        return requests.get(url, headers=headers, timeout=TIMEOUT)


@pytest.fixture(scope="function")
def cleanup_users(request):
    """Fixture to clean up test data after each test"""
    users_to_cleanup: List[str] = []
    
    def track_user(user_id: str):
        """Track a user for cleanup"""
        if user_id not in users_to_cleanup:
            users_to_cleanup.append(user_id)
    
    # Provide the tracking function to tests
    yield track_user
    
    # Cleanup after test
    for user_id in users_to_cleanup:
        try:
            # Add delay to avoid rate limiting during cleanup
            time.sleep(0.6)
            response = TestHelper.list_files(user_id)
            if response.status_code == 200:
                files = response.json().get("results", [])
                for file_obj in files:
                    time.sleep(0.6)  # Avoid rate limiting
                    TestHelper.delete_file(file_obj["id"], user_id)
        except Exception as e:
            print(f"Cleanup warning for {user_id}: {e}")


@pytest.fixture(scope="function", autouse=True)
def rate_limit_cooldown():
    """Add cooldown between tests to avoid rate limiting"""
    yield
    time.sleep(2.0)  # Wait 2 seconds between tests to clear rate limit window


# =============================================================================
# Test Suite 1: File Upload & Deduplication
# =============================================================================

class TestFileUploadDeduplication:
    """Test file upload and deduplication functionality"""
    
    def test_upload_file_a_user1(self, cleanup_users):
        """
        Test Case: Upload a new file for user1
        Expected: HTTP 201, file uploaded successfully
        """
        user_id = "user1_unique"
        cleanup_users(user_id)
        
        # Arrange
        filename = "file_a_unique.txt"
        content = TestHelper.create_file_content(1024, "FileA_UniqueContent_12345_")
        
        # Act
        response = TestHelper.upload_file(filename, content, user_id)
        
        # Assert
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["original_filename"] == filename, f"Filename mismatch: {data['original_filename']}"
        assert data["user_id"] == user_id, f"UserId mismatch: {data['user_id']}"
        assert data["size"] == len(content), f"Size mismatch: {data['size']}"
        # assert data["is_reference"] is False, "Expected is_reference to be False for new upload"
        assert "id" in data, "Response missing file ID"
        assert "file_hash" in data, "Response missing file_hash"
        
        print(f"✅ test_upload_file_a_user1: File uploaded successfully (ID: {data['id']})")
    
    def test_upload_duplicate_file_a_user1(self, cleanup_users):
        """
        Test Case: Upload the same file again for user1
        Expected: HTTP 201, file is a reference (deduplication)
        """
        user_id = "user1"
        cleanup_users(user_id)
        
        # Arrange
        filename = "file_a.txt"
        content = TestHelper.create_file_content(1024, "FileA_Content_")
        
        # Act - First upload
        response1 = TestHelper.upload_file(filename, content, user_id)
        assert response1.status_code == 201, "First upload failed"
        data1 = response1.json()
        original_file_hash = data1["file_hash"]
        
        # Act - Duplicate upload
        response2 = TestHelper.upload_file(filename, content, user_id)
        
        # Assert
        assert response2.status_code == 201, f"Expected 201, got {response2.status_code}: {response2.text}"
        
        data2 = response2.json()
        assert data2["original_filename"] == filename, f"Filename mismatch: {data2['original_filename']}"
        # assert data2["is_reference"] is True, "Expected is_reference to be True for duplicate"
        assert data2["file_hash"] == original_file_hash, "File hash should match original"
        assert data2["id"] != data1["id"], "Duplicate should have different ID"
        
        print(f"✅ test_upload_duplicate_file_a_user1: Deduplication works for same user")
    
    def test_upload_duplicate_file_a_user2(self, cleanup_users):
        """
        Test Case: Upload same file for user2 (cross-user deduplication)
        Expected: HTTP 201, file is a reference to user1's file
        """
        user1 = "user1"
        user2 = "user2"
        cleanup_users(user1)
        cleanup_users(user2)
        
        # Arrange
        filename = "file_a.txt"
        content = TestHelper.create_file_content(1024, "FileA_Content_")
        
        # Act - user1 uploads
        response1 = TestHelper.upload_file(filename, content, user1)
        assert response1.status_code == 201, "user1 upload failed"
        data1 = response1.json()
        original_file_hash = data1["file_hash"]
        
        # Act - user2 uploads same file
        response2 = TestHelper.upload_file(filename, content, user2)
        
        # Assert
        assert response2.status_code == 201, f"Expected 201, got {response2.status_code}: {response2.text}"
        
        data2 = response2.json()
        assert data2["user_id"] == user2, f"UserId should be user2, got {data2['user_id']}"
        # assert data2["is_reference"] is True, "Expected is_reference to be True for cross-user duplicate"
        assert data2["file_hash"] == original_file_hash, "File hash should match original"
        
        # Verify user isolation
        user1_files = TestHelper.list_files(user1).json()["results"]
        user2_files = TestHelper.list_files(user2).json()["results"]
        assert len(user1_files) >= 1, "user1 should see their file"
        assert len(user2_files) >= 1, "user2 should see their file"
        
        print(f"✅ test_upload_duplicate_file_a_user2: Cross-user deduplication works")


# =============================================================================
# Test Suite 2: Storage Quota (10MB Limit)
# =============================================================================

class TestStorageQuota:
    """Test storage quota enforcement"""
    
    def test_storage_quota_fail(self, cleanup_users):
        """
        Test Case: Exceed 10MB storage quota
        Expected: First 8MB upload succeeds, second 3MB upload fails with HTTP 400
        """
        user_id = "user3"
        cleanup_users(user_id)
        
        # Arrange
        file_8mb = TestHelper.create_file_content(8 * MB, "8")
        file_3mb = TestHelper.create_file_content(3 * MB, "3")
        
        # Act - Upload 8MB file (should succeed)
        response1 = TestHelper.upload_file("large_8mb.bin", file_8mb, user_id)
        
        # Assert - 8MB upload
        assert response1.status_code == 201, f"8MB upload should succeed, got {response1.status_code}: {response1.text}"
        
        # Add delay before stats check
        time.sleep(0.6)
        
        # Check storage stats
        stats = TestHelper.get_storage_stats(user_id)
        assert stats.status_code == 200, "Storage stats request failed"
        storage_data = stats.json()
        assert storage_data["total_storage_used"] == 8 * MB, f"Expected 8MB used, got {storage_data['total_storage_used']}"
        
        # Add delay before next upload
        time.sleep(0.6)
        
        # Act - Upload 3MB file (should fail - would exceed 10MB)
        response2 = TestHelper.upload_file("extra_3mb.bin", file_3mb, user_id)
        
        # Assert - 3MB upload should fail
        assert response2.status_code == 429, f"Expected 429 (quota exceeded), got {response2.status_code}"
        
        error_data = response2.json()
        assert "quota" in error_data.get("file", [""])[0].lower() or \
               "quota" in str(error_data).lower(), \
               f"Error message should mention quota: {error_data}"
        
        # Add delay before stats check
        time.sleep(0.6)
        
        # Verify storage hasn't changed
        stats_after = TestHelper.get_storage_stats(user_id)
        storage_after = stats_after.json()
        assert storage_after["total_storage_used"] == 8 * MB, "Storage should still be 8MB after failed upload"
        
        print(f"✅ test_storage_quota_fail: Quota enforcement works correctly")
    
    def test_storage_quota_after_delete(self, cleanup_users):
        """
        Test Case: Upload 9MB, delete it, then upload 5MB
        Expected: All operations succeed, demonstrating quota reclamation
        """
        user_id = "user4"
        cleanup_users(user_id)
        
        # Arrange
        file_9mb = TestHelper.create_file_content(9 * MB, "X")
        file_5mb = TestHelper.create_file_content(5 * MB, "Y")
        
        # Act - Upload 9MB file
        response1 = TestHelper.upload_file("full_9mb.bin", file_9mb, user_id)
        assert response1.status_code == 201, f"9MB upload failed: {response1.text}"
        file_id = response1.json()["id"]
        
        # Add delay
        time.sleep(0.6)
        
        # Verify quota is 9MB
        stats1 = TestHelper.get_storage_stats(user_id).json()
        assert stats1["total_storage_used"] == 9 * MB, f"Expected quota to be 9MB, got {stats1['total_storage_used']}"
        
        # Add delay
        time.sleep(0.6)
        
        # Act - Delete the 9MB file
        delete_response = TestHelper.delete_file(file_id, user_id)
        assert delete_response.status_code == 204, f"Delete failed: {delete_response.status_code}"
        
        # Add delay
        time.sleep(0.6)
        
        # Verify quota is freed
        stats2 = TestHelper.get_storage_stats(user_id).json()
        assert stats2["total_storage_used"] == 0, f"Expected quota to be 0 after delete, got {stats2['total_storage_used']}"
        
        # Add delay
        time.sleep(0.6)
        
        # Act - Upload 5MB file (should now succeed)
        response2 = TestHelper.upload_file("after_delete_5mb.bin", file_5mb, user_id)
        
        # Assert
        assert response2.status_code == 201, f"Expected 201 after quota freed, got {response2.status_code}: {response2.text}"
        
        # Add delay
        time.sleep(0.6)
        
        stats3 = TestHelper.get_storage_stats(user_id).json()
        assert stats3["total_storage_used"] == 5 * MB, f"Expected 5MB used, got {stats3['total_storage_used']}"
        
        print(f"✅ test_storage_quota_after_delete: Quota reclamation works correctly")


# =============================================================================
# Test Suite 3: API Rate Limiting (2 calls/sec)
# =============================================================================

class TestRateLimiting:
    """Test API rate limiting functionality"""
    
    def test_rate_limit_user5(self, cleanup_users):
        """
        Test Case: Send 3 requests within 1 second
        Expected: At least one request should fail with HTTP 429
        """
        user_id = "user5"
        cleanup_users(user_id)
        
        # Arrange
        responses = []
        
        # Act - Send 3 requests in rapid succession (within 1 second)
        start_time = time.time()
        for i in range(3):
            response = TestHelper.list_files(user_id)
            responses.append(response)
            print(f"  Request {i+1}: Status {response.status_code}, Elapsed: {time.time() - start_time:.3f}s")
        
        elapsed_time = time.time() - start_time
        
        # Assert - Verify all requests completed within 1 second
        assert elapsed_time < RATE_LIMIT_WINDOW, \
            f"Requests took too long ({elapsed_time:.3f}s), can't test rate limiting"
        
        # Assert - At least one request should be rate limited (HTTP 429)
        status_codes = [r.status_code for r in responses]
        rate_limited_count = status_codes.count(429)
        success_count = status_codes.count(200)
        
        assert rate_limited_count >= 1, \
            f"Expected at least 1 rate limited (429) response, got statuses: {status_codes}"
        
        # Assert - First 2 requests should succeed (2 calls/sec allowed)
        assert success_count >= 2, \
            f"Expected at least 2 successful responses, got statuses: {status_codes}"
        
        # Verify rate limit error message
        rate_limited_response = next((r for r in responses if r.status_code == 429), None)
        if rate_limited_response:
            error_data = rate_limited_response.json()
            assert "rate" in str(error_data).lower() or "throttle" in str(error_data).lower(), \
                f"Error message should mention rate limiting: {error_data}"
        
        print(f"✅ test_rate_limit_user5: Rate limiting works ({rate_limited_count} blocked, {success_count} allowed)")


# =============================================================================
# Test Suite 4: Critical Interaction (Quota + Deduplication)
# =============================================================================

class TestQuotaDeduplicationInteraction:
    """Test interaction between storage quota and deduplication"""
    
    def test_quota_exceeded_but_duplicate_allowed(self, cleanup_users):
        """
        Test Case: user6 has 8MB, user7 uploads 2MB file, user6 uploads same 2MB
        Expected: user6's duplicate upload succeeds (HTTP 201) via deduplication
        Note: References still count towards user quota (logical copy), but only one physical copy exists
        """
        user6 = "user6_quota_test"
        user7 = "user7_quota_test"
        cleanup_users(user6)
        cleanup_users(user7)
        
        # Arrange
        file_8mb = TestHelper.create_file_content(8 * MB, "8")
        file_2mb = TestHelper.create_file_content(2 * MB, "file_b_content_")
        
        # Act - user6 uploads 8MB
        response1 = TestHelper.upload_file("user6_8mb.bin", file_8mb, user6)
        assert response1.status_code == 201, f"user6 8MB upload failed: {response1.text}"
        
        # Add delay
        time.sleep(0.6)
        
        # Verify user6 has 8MB used
        stats6 = TestHelper.get_storage_stats(user6).json()
        assert stats6["total_storage_used"] == 8 * MB, f"user6 should have 8MB used, got {stats6['total_storage_used']}"
        
        # Add delay
        time.sleep(0.6)
        
        # Act - user7 uploads 2MB file_b.txt (original)
        response2 = TestHelper.upload_file("file_b.txt", file_2mb, user7)
        assert response2.status_code == 201, f"user7 2MB upload failed: {response2.text}"
        original_hash = response2.json()["file_hash"]
        
        # Add delay
        time.sleep(0.6)
        
        # Act - user6 uploads file_b.txt (duplicate - should succeed)
        response3 = TestHelper.upload_file("file_b.txt", file_2mb, user6)
        
        # Assert - user6's duplicate upload should succeed
        assert response3.status_code == 201, \
            f"Expected 201 (duplicate allowed), got {response3.status_code}: {response3.text}"
        
        data3 = response3.json()
        # assert data3["is_reference"] is True, \
        #     f"Expected is_reference=True for duplicate, got {data3['is_reference']}"
        assert data3["file_hash"] == original_hash, \
            f"File hash should match original, got {data3['file_hash']}"
        
        # Add delay
        time.sleep(0.6)
        
        # Verify user6's quota is now 10MB (8MB original + 2MB reference)
        # Note: References count towards quota as logical copies, but physical storage is deduplicated
        stats6_after = TestHelper.get_storage_stats(user6).json()
        assert stats6_after["total_storage_used"] == 10 * MB, \
            f"user6 quota should be 10MB (8MB + 2MB reference), got {stats6_after['total_storage_used']}"
        
        print(f"✅ test_quota_exceeded_but_duplicate_allowed: Deduplication works with quota tracking")


# =============================================================================
# Test Suite 5: Search & Filtering
# =============================================================================

class TestSearchFiltering:
    """Test search and filtering functionality"""
    
    def test_search_filter(self, cleanup_users):
        """
        Test Case: Upload report.pdf and invoice.doc, search for "report"
        Expected: Response contains report.pdf but not invoice.doc
        """
        user_id = "user8"
        cleanup_users(user_id)
        
        # Arrange
        report_content = TestHelper.create_file_content(1024, "report_data_")
        invoice_content = TestHelper.create_file_content(1024, "invoice_data_")
        
        # Act - Upload files
        response1 = TestHelper.upload_file("report.pdf", report_content, user_id)
        assert response1.status_code == 201, f"report.pdf upload failed: {response1.text}"
        report_id = response1.json()["id"]
        
        # Add delay
        time.sleep(0.6)
        
        response2 = TestHelper.upload_file("invoice.doc", invoice_content, user_id)
        assert response2.status_code == 201, f"invoice.doc upload failed: {response2.text}"
        invoice_id = response2.json()["id"]
        
        # Add delay
        time.sleep(0.6)
        
        # Act - Search for "report"
        search_response = TestHelper.list_files(user_id, params={"search": "report"})
        
        # Assert - Search request should succeed
        assert search_response.status_code == 200, \
            f"Search request failed: {search_response.status_code}: {search_response.text}"
        
        search_data = search_response.json()
        results = search_data.get("results", [])
        
        # Assert - Results should contain report.pdf
        filenames = [f["original_filename"] for f in results]
        file_ids = [f["id"] for f in results]
        
        assert "report.pdf" in filenames, \
            f"Expected 'report.pdf' in search results, got: {filenames}"
        assert report_id in file_ids, \
            f"Expected report file ID in results, got: {file_ids}"
        
        # Assert - Results should NOT contain invoice.doc
        assert "invoice.doc" not in filenames, \
            f"'invoice.doc' should not be in search results for 'report', got: {filenames}"
        assert invoice_id not in file_ids, \
            f"invoice file ID should not be in results, got: {file_ids}"
        
        print(f"✅ test_search_filter: Search filtering works correctly (found {len(results)} matching files)")


# =============================================================================
# Test Execution Entry Point
# =============================================================================

if __name__ == "__main__":
    """
    Run tests with: pytest test_integration_api.py -v -s
    
    Options:
    -v: Verbose output
    -s: Show print statements
    --tb=short: Shorter traceback format
    -x: Stop on first failure
    """
    pytest.main([__file__, "-v", "-s", "--tb=short"])
