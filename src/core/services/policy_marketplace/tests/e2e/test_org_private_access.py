"""
End-to-End Test: Organization-Private Templates Access Control

This script verifies the organization-private templates access control:
1. Create private template for org A
2. Query as org A user - verify visible
3. Query as org B user - verify returns 404
4. Query as unauthenticated - verify returns 404

Run with: pytest tests/e2e/test_org_private_access.py -v
Or standalone: python tests/e2e/test_org_private_access.py
"""

import io
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.main import app  # noqa: E402, I001

# Test constants
ORG_A_ID = "org-alpha-001"
ORG_B_ID = "org-beta-002"
ORG_A_USER = "user-alice-001"
ORG_B_USER = "user-bob-001"

PRIVATE_TEMPLATE_CONTENT = {
    "policy": {
        "name": "Org A Private Policy",
        "version": "1.0.0",
        "organization": ORG_A_ID,
        "rules": [
            {
                "id": "private-rule-001",
                "action": "allow",
                "condition": {"scope": "internal", "resource": "org-data"},
            }
        ],
    }
}

PRIVATE_TEMPLATE_NAME = "Org Alpha Private Template"
PRIVATE_TEMPLATE_DESCRIPTION = (
    "Private template for testing organization access control. "
    "This template should only be visible to Org Alpha members."
)
PRIVATE_TEMPLATE_CATEGORY = "access_control"


def get_org_a_headers():
    """Get headers for an Org A user."""
    return {
        "X-User-Id": ORG_A_USER,
        "X-Organization-Id": ORG_A_ID,
    }


def get_org_b_headers():
    """Get headers for an Org B user."""
    return {
        "X-User-Id": ORG_B_USER,
        "X-Organization-Id": ORG_B_ID,
    }


def get_admin_headers():
    """Get headers for an admin user."""
    return {
        "X-User-Id": "admin-001",
        "X-Organization-Id": ORG_A_ID,
        "X-User-Role": "admin",
    }


def get_no_auth_headers():
    """Get headers for an unauthenticated request."""
    return {}


@pytest.fixture(scope="module")
def client():
    """Create test client for API requests."""
    return TestClient(app)


class TestPrivateTemplateCreation:
    """Test creating private templates for an organization."""

    def test_01_health_check(self, client: TestClient):
        """Verify API is healthy before running tests."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_02_create_private_template_for_org_a(self, client: TestClient):
        """Create a private template for Org A."""
        file_content = json.dumps(PRIVATE_TEMPLATE_CONTENT, indent=2)
        file_bytes = file_content.encode("utf-8")

        files = {"file": ("org_a_private.json", io.BytesIO(file_bytes), "application/json")}
        data = {
            "name": PRIVATE_TEMPLATE_NAME,
            "description": PRIVATE_TEMPLATE_DESCRIPTION,
            "category": PRIVATE_TEMPLATE_CATEGORY,
            "is_public": "false",  # Form field as string
            "organization_id": ORG_A_ID,
        }

        response = client.post(
            "/api/v1/templates/upload",
            files=files,
            data=data,
            headers=get_org_a_headers(),
        )

        assert response.status_code == 201, f"Upload failed: {response.text}"
        result = response.json()

        # Verify template is private
        assert result["is_public"] is False, "Template should be private"
        assert result["organization_id"] == ORG_A_ID, "Organization ID should match Org A"
        assert result["name"] == PRIVATE_TEMPLATE_NAME

        # Store template ID for later tests
        self.__class__.private_template_id = result["id"]

    def test_03_verify_template_is_private(self, client: TestClient):
        """Verify the created template has correct access settings."""
        response = client.get(
            f"/api/v1/templates/{self.__class__.private_template_id}",
            headers=get_org_a_headers(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_public"] is False
        assert data["organization_id"] == ORG_A_ID


class TestOrgAUserAccess:
    """Test that Org A users can access their private templates."""

    @pytest.fixture(autouse=True)
    def setup(self, client: TestClient):
        """Ensure private template exists."""
        # Create the template if not already created
        if not hasattr(TestPrivateTemplateCreation, "private_template_id"):
            file_content = json.dumps(PRIVATE_TEMPLATE_CONTENT)
            files = {
                "file": (
                    "org_a_test.json",
                    io.BytesIO(file_content.encode()),
                    "application/json",
                )
            }
            data = {
                "name": PRIVATE_TEMPLATE_NAME,
                "description": PRIVATE_TEMPLATE_DESCRIPTION,
                "category": PRIVATE_TEMPLATE_CATEGORY,
                "is_public": "false",
                "organization_id": ORG_A_ID,
            }
            response = client.post(
                "/api/v1/templates/upload",
                files=files,
                data=data,
                headers=get_org_a_headers(),
            )
            TestPrivateTemplateCreation.private_template_id = response.json()["id"]

    def test_01_org_a_user_can_get_template(self, client: TestClient):
        """Org A user can GET the private template by ID."""
        response = client.get(
            f"/api/v1/templates/{TestPrivateTemplateCreation.private_template_id}",
            headers=get_org_a_headers(),
        )

        assert response.status_code == 200, f"Org A user should access template: {response.text}"
        data = response.json()
        assert data["id"] == TestPrivateTemplateCreation.private_template_id
        assert data["name"] == PRIVATE_TEMPLATE_NAME

    def test_02_org_a_user_can_see_template_in_list(self, client: TestClient):
        """Org A user can see the private template in listing."""
        response = client.get("/api/v1/templates", headers=get_org_a_headers())

        assert response.status_code == 200
        data = response.json()
        template_ids = [item["id"] for item in data["items"]]
        assert TestPrivateTemplateCreation.private_template_id in template_ids, (
            f"Org A user should see template in list. Found IDs: {template_ids}"
        )

    def test_03_org_a_user_can_download_template(self, client: TestClient):
        """Org A user can download the private template."""
        response = client.get(
            f"/api/v1/templates/{TestPrivateTemplateCreation.private_template_id}/download",
            headers=get_org_a_headers(),
        )

        assert response.status_code == 200, f"Org A user should download: {response.text}"
        data = response.json()
        assert data["id"] == TestPrivateTemplateCreation.private_template_id


class TestOrgBUserAccess:
    """Test that Org B users CANNOT access Org A's private templates."""

    @pytest.fixture(autouse=True)
    def setup(self, client: TestClient):
        """Ensure private template exists."""
        if not hasattr(TestPrivateTemplateCreation, "private_template_id"):
            file_content = json.dumps(PRIVATE_TEMPLATE_CONTENT)
            files = {
                "file": (
                    "org_a_test2.json",
                    io.BytesIO(file_content.encode()),
                    "application/json",
                )
            }
            data = {
                "name": PRIVATE_TEMPLATE_NAME,
                "description": PRIVATE_TEMPLATE_DESCRIPTION,
                "category": PRIVATE_TEMPLATE_CATEGORY,
                "is_public": "false",
                "organization_id": ORG_A_ID,
            }
            response = client.post(
                "/api/v1/templates/upload",
                files=files,
                data=data,
                headers=get_org_a_headers(),
            )
            TestPrivateTemplateCreation.private_template_id = response.json()["id"]

    def test_01_org_b_user_gets_404_on_get(self, client: TestClient):
        """Org B user gets 404 when trying to GET the private template."""
        response = client.get(
            f"/api/v1/templates/{TestPrivateTemplateCreation.private_template_id}",
            headers=get_org_b_headers(),
        )

        # Should return 404 (not 403) to avoid info disclosure
        assert response.status_code == 404, (
            f"Org B user should get 404, not {response.status_code}. "
            "Expected 404 to avoid information disclosure."
        )
        assert response.json()["detail"] == "Template not found"

    def test_02_org_b_user_cannot_see_template_in_list(self, client: TestClient):
        """Org B user cannot see the private template in listing."""
        response = client.get("/api/v1/templates", headers=get_org_b_headers())

        assert response.status_code == 200
        data = response.json()
        template_ids = [item["id"] for item in data["items"]]
        assert TestPrivateTemplateCreation.private_template_id not in template_ids, (
            f"Org B user should NOT see template in list. Template ID "
            f"{TestPrivateTemplateCreation.private_template_id} should not be in {template_ids}"
        )

    def test_03_org_b_user_gets_404_on_download(self, client: TestClient):
        """Org B user gets 404 when trying to download the private template."""
        response = client.get(
            f"/api/v1/templates/{TestPrivateTemplateCreation.private_template_id}/download",
            headers=get_org_b_headers(),
        )

        # Should return 404 (not 403) to avoid info disclosure
        assert response.status_code == 404, (
            f"Org B user should get 404 on download, not {response.status_code}"
        )


class TestUnauthenticatedAccess:
    """Test that unauthenticated users CANNOT access private templates."""

    @pytest.fixture(autouse=True)
    def setup(self, client: TestClient):
        """Ensure private template exists."""
        if not hasattr(TestPrivateTemplateCreation, "private_template_id"):
            file_content = json.dumps(PRIVATE_TEMPLATE_CONTENT)
            files = {
                "file": (
                    "org_a_test3.json",
                    io.BytesIO(file_content.encode()),
                    "application/json",
                )
            }
            data = {
                "name": PRIVATE_TEMPLATE_NAME,
                "description": PRIVATE_TEMPLATE_DESCRIPTION,
                "category": PRIVATE_TEMPLATE_CATEGORY,
                "is_public": "false",
                "organization_id": ORG_A_ID,
            }
            response = client.post(
                "/api/v1/templates/upload",
                files=files,
                data=data,
                headers=get_org_a_headers(),
            )
            TestPrivateTemplateCreation.private_template_id = response.json()["id"]

    def test_01_unauthenticated_gets_404_on_get(self, client: TestClient):
        """Unauthenticated user gets 404 when trying to GET the private template."""
        response = client.get(
            f"/api/v1/templates/{TestPrivateTemplateCreation.private_template_id}",
            headers=get_no_auth_headers(),
        )

        # Should return 404 (not 403) to avoid info disclosure
        assert response.status_code == 404, (
            f"Unauthenticated user should get 404, not {response.status_code}"
        )

    def test_02_unauthenticated_cannot_see_template_in_list(self, client: TestClient):
        """Unauthenticated user cannot see the private template in listing."""
        response = client.get("/api/v1/templates", headers=get_no_auth_headers())

        assert response.status_code == 200
        data = response.json()
        template_ids = [item["id"] for item in data["items"]]
        assert TestPrivateTemplateCreation.private_template_id not in template_ids, (
            "Unauthenticated user should NOT see private template in list"
        )

    def test_03_unauthenticated_gets_404_on_download(self, client: TestClient):
        """Unauthenticated user gets 404 when trying to download the private template."""
        response = client.get(
            f"/api/v1/templates/{TestPrivateTemplateCreation.private_template_id}/download",
            headers=get_no_auth_headers(),
        )

        # Should return 404 (not 403) to avoid info disclosure
        assert response.status_code == 404, (
            f"Unauthenticated user should get 404 on download, not {response.status_code}"
        )


class TestAdminAccess:
    """Test that admin users can access all private templates."""

    @pytest.fixture(autouse=True)
    def setup(self, client: TestClient):
        """Ensure private template exists."""
        if not hasattr(TestPrivateTemplateCreation, "private_template_id"):
            file_content = json.dumps(PRIVATE_TEMPLATE_CONTENT)
            files = {
                "file": (
                    "org_a_test4.json",
                    io.BytesIO(file_content.encode()),
                    "application/json",
                )
            }
            data = {
                "name": PRIVATE_TEMPLATE_NAME,
                "description": PRIVATE_TEMPLATE_DESCRIPTION,
                "category": PRIVATE_TEMPLATE_CATEGORY,
                "is_public": "false",
                "organization_id": ORG_A_ID,
            }
            response = client.post(
                "/api/v1/templates/upload",
                files=files,
                data=data,
                headers=get_org_a_headers(),
            )
            TestPrivateTemplateCreation.private_template_id = response.json()["id"]

    def test_01_admin_can_access_private_template(self, client: TestClient):
        """Admin user can access any private template."""
        response = client.get(
            f"/api/v1/templates/{TestPrivateTemplateCreation.private_template_id}",
            headers=get_admin_headers(),
        )

        assert response.status_code == 200, f"Admin should access template: {response.text}"
        data = response.json()
        assert data["id"] == TestPrivateTemplateCreation.private_template_id


class TestPublicTemplateAccess:
    """Test that public templates remain accessible to all users."""

    def test_01_create_public_template(self, client: TestClient):
        """Create a public template."""
        file_content = json.dumps({"policy": "public_test"})
        files = {
            "file": ("public_test.json", io.BytesIO(file_content.encode()), "application/json")
        }
        data = {
            "name": "Public Test Template",
            "description": "A public template accessible to everyone",
            "category": "compliance",
            "is_public": "true",
        }

        response = client.post(
            "/api/v1/templates/upload",
            files=files,
            data=data,
            headers=get_org_a_headers(),
        )

        assert response.status_code == 201
        result = response.json()
        assert result["is_public"] is True
        self.__class__.public_template_id = result["id"]

    def test_02_org_b_can_access_public_template(self, client: TestClient):
        """Org B user can access public template from Org A."""
        response = client.get(
            f"/api/v1/templates/{self.__class__.public_template_id}",
            headers=get_org_b_headers(),
        )

        assert response.status_code == 200, "Org B should access public template"

    def test_03_unauthenticated_can_access_public_template(self, client: TestClient):
        """Unauthenticated user can access public template."""
        response = client.get(
            f"/api/v1/templates/{self.__class__.public_template_id}",
            headers=get_no_auth_headers(),
        )

        assert response.status_code == 200, "Unauthenticated should access public template"


def run_standalone_tests():
    """Run tests standalone without pytest for quick verification."""
    client = TestClient(app)

    # Test 1: Health check
    resp = client.get("/health/ready")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"

    # Test 2: Create private template for Org A
    file_content = json.dumps(PRIVATE_TEMPLATE_CONTENT, indent=2)
    files = {"file": ("org_a_private.json", io.BytesIO(file_content.encode()), "application/json")}
    data = {
        "name": PRIVATE_TEMPLATE_NAME,
        "description": PRIVATE_TEMPLATE_DESCRIPTION,
        "category": PRIVATE_TEMPLATE_CATEGORY,
        "is_public": "false",
        "organization_id": ORG_A_ID,
    }
    resp = client.post(
        "/api/v1/templates/upload", files=files, data=data, headers=get_org_a_headers()
    )
    assert resp.status_code == 201, f"Upload failed: {resp.text}"
    template_id = resp.json()["id"]
    assert resp.json()["is_public"] is False
    assert resp.json()["organization_id"] == ORG_A_ID

    # Test 3: Org A user can GET template
    resp = client.get(f"/api/v1/templates/{template_id}", headers=get_org_a_headers())
    assert resp.status_code == 200, f"Org A should access template: {resp.text}"

    # Test 4: Org A user can see template in list
    resp = client.get("/api/v1/templates", headers=get_org_a_headers())
    assert resp.status_code == 200
    template_ids = [item["id"] for item in resp.json()["items"]]
    assert template_id in template_ids, f"Template not in list: {template_ids}"

    # Test 5: Org B user gets 404 on GET
    resp = client.get(f"/api/v1/templates/{template_id}", headers=get_org_b_headers())
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
    assert resp.json()["detail"] == "Template not found"

    # Test 6: Org B user cannot see template in list
    resp = client.get("/api/v1/templates", headers=get_org_b_headers())
    assert resp.status_code == 200
    template_ids = [item["id"] for item in resp.json()["items"]]
    assert template_id not in template_ids, "Template should NOT be in list"

    # Test 7: Unauthenticated gets 404 on GET
    resp = client.get(f"/api/v1/templates/{template_id}", headers=get_no_auth_headers())
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    # Test 8: Unauthenticated cannot see template in list
    resp = client.get("/api/v1/templates", headers=get_no_auth_headers())
    assert resp.status_code == 200
    template_ids = [item["id"] for item in resp.json()["items"]]
    assert template_id not in template_ids

    # Test 9: Org B gets 404 on download
    resp = client.get(f"/api/v1/templates/{template_id}/download", headers=get_org_b_headers())
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    # Test 10: Admin can access all templates
    resp = client.get(f"/api/v1/templates/{template_id}", headers=get_admin_headers())
    assert resp.status_code == 200, f"Admin should access template: {resp.text}"

    return True


if __name__ == "__main__":
    try:
        success = run_standalone_tests()
        sys.exit(0 if success else 1)
    except AssertionError as e:
        sys.exit(1)
    except Exception as e:
        import traceback

        traceback.print_exc()
        sys.exit(1)
