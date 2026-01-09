"""
End-to-End Test: Template Upload to Download Flow

This script verifies the complete template upload to download workflow:
1. Upload a test template via API
2. Verify template appears in listing
3. Download template and verify content matches
4. Verify download count incremented

Run with: pytest tests/e2e/test_upload_download_flow.py -v
Or standalone: python tests/e2e/test_upload_download_flow.py
"""

import io
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path for imports - needed before importing app
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.main import app  # noqa: E402, I001

# Test constants
TEST_TEMPLATE_CONTENT = {
    "policy": {
        "name": "E2E Test Policy",
        "version": "1.0.0",
        "rules": [
            {
                "id": "rule-001",
                "action": "allow",
                "condition": {"subject": "admin", "resource": "*"},
            }
        ],
    }
}

TEST_TEMPLATE_NAME = "E2E Test Template"
TEST_TEMPLATE_DESCRIPTION = "Template created for end-to-end testing of upload/download flow"
TEST_TEMPLATE_CATEGORY = "compliance"


@pytest.fixture(scope="module")
def client():
    """Create test client for API requests."""
    return TestClient(app)


class TestUploadDownloadFlow:
    """Test the complete upload to download flow."""

    def test_01_health_check(self, client: TestClient):
        """Verify API is healthy before running tests."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_02_list_templates_initial(self, client: TestClient):
        """Verify template listing works before upload."""
        response = client.get("/api/v1/templates")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "meta" in data
        # Store initial count for later verification
        self.__class__.initial_count = data["meta"]["total_items"]

    def test_03_upload_template(self, client: TestClient):
        """Upload a test template via multipart form."""
        # Create file content
        file_content = json.dumps(TEST_TEMPLATE_CONTENT, indent=2)
        file_bytes = file_content.encode("utf-8")

        # Create the multipart form data
        files = {"file": ("test_template.json", io.BytesIO(file_bytes), "application/json")}
        data = {
            "name": TEST_TEMPLATE_NAME,
            "description": TEST_TEMPLATE_DESCRIPTION,
            "category": TEST_TEMPLATE_CATEGORY,
        }

        response = client.post("/api/v1/templates/upload", files=files, data=data)

        assert response.status_code == 201, f"Upload failed: {response.text}"
        result = response.json()

        # Verify response structure
        assert "id" in result
        assert result["name"] == TEST_TEMPLATE_NAME
        assert result["description"] == TEST_TEMPLATE_DESCRIPTION
        assert result["category"] == TEST_TEMPLATE_CATEGORY
        assert result["format"] == "json"
        assert result["downloads"] == 0
        assert result["status"] == "draft"

        # Store template ID for later tests
        self.__class__.uploaded_template_id = result["id"]
        self.__class__.uploaded_content = result["content"]

    def test_04_verify_template_in_listing(self, client: TestClient):
        """Verify uploaded template appears in listing."""
        response = client.get("/api/v1/templates")
        assert response.status_code == 200
        data = response.json()

        # Verify count increased
        assert data["meta"]["total_items"] > self.__class__.initial_count

        # Find our uploaded template
        template_ids = [item["id"] for item in data["items"]]
        assert (
            self.__class__.uploaded_template_id in template_ids
        ), "Uploaded template not found in listing"

        # Verify template details in listing
        uploaded = next(
            item for item in data["items"] if item["id"] == self.__class__.uploaded_template_id
        )
        assert uploaded["name"] == TEST_TEMPLATE_NAME
        assert uploaded["downloads"] == 0

    def test_05_get_template_by_id(self, client: TestClient):
        """Verify template can be retrieved by ID."""
        response = client.get(f"/api/v1/templates/{self.__class__.uploaded_template_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == self.__class__.uploaded_template_id
        assert data["name"] == TEST_TEMPLATE_NAME
        assert data["content"] == self.__class__.uploaded_content

    def test_06_download_template(self, client: TestClient):
        """Download template and verify content matches."""
        response = client.get(f"/api/v1/templates/{self.__class__.uploaded_template_id}/download")
        assert response.status_code == 200
        data = response.json()

        # Verify download response
        assert data["id"] == self.__class__.uploaded_template_id
        assert data["name"] == TEST_TEMPLATE_NAME
        assert data["content"] == self.__class__.uploaded_content
        assert data["format"] == "json"

        # Verify content matches original
        downloaded_content = json.loads(data["content"])
        assert downloaded_content == TEST_TEMPLATE_CONTENT

        # Verify download count incremented to 1
        assert data["downloads"] == 1

    def test_07_verify_download_count_incremented(self, client: TestClient):
        """Verify download count was incremented in the template record."""
        response = client.get(f"/api/v1/templates/{self.__class__.uploaded_template_id}")
        assert response.status_code == 200
        data = response.json()

        # Verify download count is now 1
        assert data["downloads"] == 1

    def test_08_download_again_increments_count(self, client: TestClient):
        """Verify multiple downloads increment the count."""
        # Download again
        response = client.get(f"/api/v1/templates/{self.__class__.uploaded_template_id}/download")
        assert response.status_code == 200
        data = response.json()
        assert data["downloads"] == 2

        # Verify in listing
        response = client.get(f"/api/v1/templates/{self.__class__.uploaded_template_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["downloads"] == 2

    def test_09_filter_templates_by_category(self, client: TestClient):
        """Verify filtering by category works."""
        response = client.get(f"/api/v1/templates?category={TEST_TEMPLATE_CATEGORY}")
        assert response.status_code == 200
        data = response.json()

        # All returned templates should have the correct category
        for item in data["items"]:
            assert item["category"] == TEST_TEMPLATE_CATEGORY

    def test_10_search_templates_by_name(self, client: TestClient):
        """Verify search by name works."""
        response = client.get("/api/v1/templates?query=E2E")
        assert response.status_code == 200
        data = response.json()

        # Our uploaded template should be in results
        template_ids = [item["id"] for item in data["items"]]
        assert self.__class__.uploaded_template_id in template_ids


class TestUploadValidation:
    """Test upload validation edge cases."""

    def test_invalid_file_extension(self, client: TestClient):
        """Verify invalid file extensions are rejected."""
        file_bytes = b"invalid content"
        files = {"file": ("test.exe", io.BytesIO(file_bytes), "application/octet-stream")}
        data = {
            "name": "Invalid Template",
            "description": "This should fail validation",
            "category": "compliance",
        }

        response = client.post("/api/v1/templates/upload", files=files, data=data)
        assert response.status_code == 400
        assert "Unsupported file format" in response.json()["detail"]

    def test_invalid_category(self, client: TestClient):
        """Verify invalid categories are rejected."""
        file_content = json.dumps({"test": "data"})
        files = {"file": ("test.json", io.BytesIO(file_content.encode()), "application/json")}
        data = {
            "name": "Invalid Category Template",
            "description": "This should fail validation",
            "category": "invalid_category",
        }

        response = client.post("/api/v1/templates/upload", files=files, data=data)
        assert response.status_code == 400
        assert "Invalid category" in response.json()["detail"]

    def test_yaml_file_upload(self, client: TestClient):
        """Verify YAML file uploads work."""
        yaml_content = """
policy:
  name: YAML Test Policy
  version: "1.0.0"
  rules:
    - id: rule-001
      action: deny
"""
        files = {"file": ("test.yaml", io.BytesIO(yaml_content.encode()), "application/x-yaml")}
        data = {
            "name": "YAML Test Template",
            "description": "Testing YAML file upload functionality",
            "category": "access_control",
        }

        response = client.post("/api/v1/templates/upload", files=files, data=data)
        assert response.status_code == 201
        result = response.json()
        assert result["format"] == "yaml"
        assert result["name"] == "YAML Test Template"

    def test_rego_file_upload(self, client: TestClient):
        """Verify Rego file uploads work."""
        rego_content = """
package authz

default allow = false

allow {
    input.user == "admin"
}
"""
        files = {"file": ("policy.rego", io.BytesIO(rego_content.encode()), "text/plain")}
        data = {
            "name": "Rego Test Template",
            "description": "Testing Rego file upload functionality",
            "category": "access_control",
        }

        response = client.post("/api/v1/templates/upload", files=files, data=data)
        assert response.status_code == 201
        result = response.json()
        assert result["format"] == "rego"


class TestDownloadErrors:
    """Test download error handling."""

    def test_download_nonexistent_template(self, client: TestClient):
        """Verify 404 for non-existent template download."""
        response = client.get("/api/v1/templates/99999/download")
        assert response.status_code == 404

    def test_get_nonexistent_template(self, client: TestClient):
        """Verify 404 for non-existent template get."""
        response = client.get("/api/v1/templates/99999")
        assert response.status_code == 404


def run_standalone_tests():
    """Run tests standalone without pytest for quick verification."""
    client = TestClient(app)

    # Test 1: Health check
    resp = client.get("/health/ready")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"

    # Test 2: Get initial template count
    resp = client.get("/api/v1/templates")
    assert resp.status_code == 200
    initial_count = resp.json()["meta"]["total_items"]

    # Test 3: Upload template
    file_content = json.dumps(TEST_TEMPLATE_CONTENT, indent=2)
    files = {"file": ("e2e_test.json", io.BytesIO(file_content.encode()), "application/json")}
    data = {
        "name": TEST_TEMPLATE_NAME,
        "description": TEST_TEMPLATE_DESCRIPTION,
        "category": TEST_TEMPLATE_CATEGORY,
    }
    resp = client.post("/api/v1/templates/upload", files=files, data=data)
    assert resp.status_code == 201, f"Upload failed: {resp.text}"
    template_id = resp.json()["id"]
    uploaded_content = resp.json()["content"]

    # Test 4: Verify in listing
    resp = client.get("/api/v1/templates")
    assert resp.status_code == 200
    new_count = resp.json()["meta"]["total_items"]
    assert new_count > initial_count, "Template count did not increase"
    template_ids = [t["id"] for t in resp.json()["items"]]
    assert template_id in template_ids, "Template not found in listing"

    # Test 5: Download template
    resp = client.get(f"/api/v1/templates/{template_id}/download")
    assert resp.status_code == 200
    download_data = resp.json()
    assert download_data["content"] == uploaded_content, "Content mismatch"

    # Test 6: Verify download count
    assert download_data["downloads"] == 1, "Download count not incremented"

    # Test 7: Verify count persisted
    resp = client.get(f"/api/v1/templates/{template_id}")
    assert resp.status_code == 200
    assert resp.json()["downloads"] == 1, "Download count not persisted"

    return True


if __name__ == "__main__":
    try:
        success = run_standalone_tests()
        sys.exit(0 if success else 1)
    except AssertionError as e:
        sys.exit(1)
    except Exception as e:
        sys.exit(1)
