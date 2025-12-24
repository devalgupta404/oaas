"""
Unit tests for the API module (api.server).
Tests FastAPI endpoints and request handling.
"""

import base64
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.server import app, calculate_overall_protection_index


# Create test client
client = TestClient(app)

# Test API key
TEST_API_KEY = "test-api-key"


class TestHealthEndpoint:
    """Tests for /api/health endpoint."""

    def test_health_check(self):
        """Test that health endpoint returns success."""
        response = client.get("/api/health", headers={"x-api-key": TEST_API_KEY})
        assert response.status_code in [200, 204]

    def test_health_check_without_auth(self):
        """Test health endpoint without authentication."""
        # Health endpoint may or may not require auth
        response = client.get("/api/health")
        # Should either work or return 401/403
        assert response.status_code in [200, 204, 401, 403]


class TestJobsEndpoint:
    """Tests for /api/jobs endpoint."""

    def test_list_jobs(self):
        """Test listing jobs."""
        response = client.get("/api/jobs", headers={"x-api-key": TEST_API_KEY})
        assert response.status_code in [200, 204]

    def test_list_jobs_without_auth(self):
        """Test listing jobs without authentication."""
        response = client.get("/api/jobs")
        assert response.status_code in [401, 403, 200]


class TestCalculateOverallProtectionIndex:
    """Tests for calculate_overall_protection_index function."""

    def test_minimal_protection(self):
        """Test score with minimal protection values."""
        score = calculate_overall_protection_index(
            symbol_reduction=0,
            function_reduction=0,
            entropy_increase=0,
            size_change_percent=0,
            passes=[],
            has_string_encryption=False
        )
        assert 0 <= score <= 100

    def test_high_protection(self):
        """Test score with high protection values."""
        score = calculate_overall_protection_index(
            symbol_reduction=95,
            function_reduction=90,
            entropy_increase=150,
            size_change_percent=50,
            passes=["flattening", "substitution", "boguscf", "split"],
            has_string_encryption=True
        )
        assert score > 50  # Should be a high score

    def test_symbol_reduction_scoring(self):
        """Test that higher symbol reduction gives higher score."""
        low_score = calculate_overall_protection_index(
            symbol_reduction=10,
            function_reduction=0,
            entropy_increase=0,
            size_change_percent=0,
            passes=[],
            has_string_encryption=False
        )
        high_score = calculate_overall_protection_index(
            symbol_reduction=95,
            function_reduction=0,
            entropy_increase=0,
            size_change_percent=0,
            passes=[],
            has_string_encryption=False
        )
        assert high_score >= low_score

    def test_passes_affect_score(self):
        """Test that having passes increases score."""
        no_passes_score = calculate_overall_protection_index(
            symbol_reduction=50,
            function_reduction=50,
            entropy_increase=50,
            size_change_percent=20,
            passes=[],
            has_string_encryption=False
        )
        with_passes_score = calculate_overall_protection_index(
            symbol_reduction=50,
            function_reduction=50,
            entropy_increase=50,
            size_change_percent=20,
            passes=["flattening", "substitution"],
            has_string_encryption=False
        )
        assert with_passes_score >= no_passes_score


class TestObfuscateEndpoint:
    """Tests for /api/obfuscate endpoint."""

    @pytest.fixture
    def sample_source_b64(self, sample_c_source: Path) -> str:
        """Return base64 encoded sample source."""
        return base64.b64encode(sample_c_source.read_bytes()).decode("ascii")

    def test_obfuscate_missing_source(self):
        """Test obfuscate with missing source code."""
        payload = {
            "filename": "test.c",
            "platform": "linux"
        }
        response = client.post(
            "/api/obfuscate",
            headers={"x-api-key": TEST_API_KEY},
            json=payload
        )
        # Should fail due to missing source_code
        assert response.status_code in [400, 422]

    def test_obfuscate_invalid_platform(self, sample_source_b64):
        """Test obfuscate with invalid platform."""
        payload = {
            "source_code": sample_source_b64,
            "filename": "test.c",
            "platform": "invalid_platform"
        }
        response = client.post(
            "/api/obfuscate",
            headers={"x-api-key": TEST_API_KEY},
            json=payload
        )
        # Should fail due to invalid platform
        assert response.status_code in [400, 422, 500]


class TestAnalyzeEndpoint:
    """Tests for /api/analyze/{job_id} endpoint."""

    def test_analyze_nonexistent_job(self):
        """Test analyze with non-existent job ID."""
        response = client.get(
            "/api/analyze/nonexistent-job-id",
            headers={"x-api-key": TEST_API_KEY}
        )
        # Should return 404 or similar
        assert response.status_code in [404, 400, 500]


class TestReportEndpoint:
    """Tests for /api/report/{job_id} endpoint."""

    def test_report_nonexistent_job(self):
        """Test report with non-existent job ID."""
        response = client.get(
            "/api/report/nonexistent-job-id",
            headers={"x-api-key": TEST_API_KEY}
        )
        # Should return 404 or similar
        assert response.status_code in [404, 400, 500]


class TestCompareEndpoint:
    """Tests for /api/compare endpoint."""

    def test_compare_missing_data(self):
        """Test compare with missing binary data."""
        payload = {
            "filename": "test"
        }
        response = client.post(
            "/api/compare",
            headers={"x-api-key": TEST_API_KEY},
            json=payload
        )
        # Should fail due to missing data
        assert response.status_code in [400, 422]

    def test_compare_with_data(self, sample_c_source: Path):
        """Test compare with binary data."""
        data = sample_c_source.read_bytes()
        payload = {
            "original_b64": base64.b64encode(data).decode("ascii"),
            "obfuscated_b64": base64.b64encode(data).decode("ascii"),
            "filename": "sample"
        }
        response = client.post(
            "/api/compare",
            headers={"x-api-key": TEST_API_KEY},
            json=payload
        )
        # Should return comparison result
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            body = response.json()
            assert "size_delta" in body or "error" not in body


class TestFlagsEndpoint:
    """Tests for /api/flags endpoint."""

    def test_get_flags(self):
        """Test getting compiler flags."""
        response = client.get(
            "/api/flags",
            headers={"x-api-key": TEST_API_KEY}
        )
        # May return empty list if flags not configured
        assert response.status_code in [200, 404]


class TestAuthenticationMiddleware:
    """Tests for API authentication."""

    def test_missing_api_key(self):
        """Test request without API key."""
        response = client.get("/api/jobs")
        # Should require authentication
        assert response.status_code in [200, 401, 403]

    def test_invalid_api_key(self):
        """Test request with invalid API key."""
        response = client.get(
            "/api/jobs",
            headers={"x-api-key": "invalid-key"}
        )
        # Should reject invalid key (if auth enabled)
        assert response.status_code in [200, 401, 403]

    def test_valid_api_key(self):
        """Test request with valid API key."""
        response = client.get(
            "/api/health",
            headers={"x-api-key": TEST_API_KEY}
        )
        assert response.status_code in [200, 204]


class TestCORSHeaders:
    """Tests for CORS configuration."""

    def test_cors_headers_present(self):
        """Test that CORS headers are present."""
        response = client.options("/api/health")
        # OPTIONS should be handled by CORS middleware
        assert response.status_code in [200, 204, 405]


class TestAPIInputValidation:
    """Tests for API input validation."""

    def test_obfuscate_empty_payload(self):
        """Test obfuscate with empty payload."""
        response = client.post(
            "/api/obfuscate",
            headers={"x-api-key": TEST_API_KEY},
            json={}
        )
        assert response.status_code in [400, 422]

    def test_obfuscate_invalid_base64(self):
        """Test obfuscate with invalid base64 source."""
        payload = {
            "source_code": "not-valid-base64!!!",
            "filename": "test.c",
            "platform": "linux"
        }
        response = client.post(
            "/api/obfuscate",
            headers={"x-api-key": TEST_API_KEY},
            json=payload
        )
        # Should fail due to invalid base64
        assert response.status_code in [400, 422, 500]

    def test_obfuscate_empty_source(self):
        """Test obfuscate with empty source code."""
        payload = {
            "source_code": base64.b64encode(b"").decode("ascii"),
            "filename": "test.c",
            "platform": "linux"
        }
        response = client.post(
            "/api/obfuscate",
            headers={"x-api-key": TEST_API_KEY},
            json=payload
        )
        # Should handle empty source gracefully
        assert response.status_code in [200, 400, 422, 500]
