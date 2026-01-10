"""
End-to-End Test: Review Workflow (Submit, Approve, Verify Badge)

This script verifies the complete review workflow:
1. Upload/create a template (starts in DRAFT status, is_verified=false)
2. Submit template for review (status changes to PENDING_REVIEW)
3. Verify template appears in review queue
4. Approve template as admin (status becomes PUBLISHED, is_verified=true)
5. Verify is_verified=true in template record
6. Verify verified badge displays correctly in list endpoint

Run with: pytest tests/e2e/test_review_workflow.py -v
Or standalone: python tests/e2e/test_review_workflow.py
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
TEST_TEMPLATE_CONTENT = {
    "policy": {
        "name": "Review Workflow Test Policy",
        "version": "1.0.0",
        "rules": [
            {
                "id": "review-rule-001",
                "action": "allow",
                "condition": {"role": "reviewer", "resource": "templates"},
            }
        ],
    }
}

TEST_TEMPLATE_NAME = "Review Workflow Test Template"
TEST_TEMPLATE_DESCRIPTION = "Template created for end-to-end testing of the review workflow"
TEST_TEMPLATE_CATEGORY = "compliance"


@pytest.fixture(scope="module")
def client():
    """Create test client for API requests."""
    return TestClient(app)


class TestReviewWorkflow:
    """Test the complete review workflow: submit, approve, verify badge."""

    def test_01_health_check(self, client: TestClient):
        """Verify API is healthy before running tests."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_02_upload_template_draft_status(self, client: TestClient):
        """Upload a template - it should start in DRAFT status with is_verified=false."""
        file_content = json.dumps(TEST_TEMPLATE_CONTENT, indent=2)
        file_bytes = file_content.encode("utf-8")

        files = {"file": ("review_test.json", io.BytesIO(file_bytes), "application/json")}
        data = {
            "name": TEST_TEMPLATE_NAME,
            "description": TEST_TEMPLATE_DESCRIPTION,
            "category": TEST_TEMPLATE_CATEGORY,
        }

        response = client.post("/api/v1/templates/upload", files=files, data=data)

        assert response.status_code == 201, f"Upload failed: {response.text}"
        result = response.json()

        # Verify initial state
        assert result["status"] == "draft", "Template should start in DRAFT status"
        assert result["is_verified"] is False, "Template should not be verified initially"

        # Store template ID for later tests
        self.__class__.template_id = result["id"]

    def test_03_verify_draft_not_verified_in_listing(self, client: TestClient):
        """Verify draft template shows is_verified=false in listing."""
        response = client.get("/api/v1/templates")
        assert response.status_code == 200
        data = response.json()

        # Find our uploaded template
        template = next(
            (item for item in data["items"] if item["id"] == self.__class__.template_id),
            None,
        )
        assert template is not None, "Template not found in listing"
        assert template["is_verified"] is False, "Draft template should not be verified"
        assert template["status"] == "draft", "Template should be in draft status"

    def test_04_submit_template_for_review(self, client: TestClient):
        """Submit template for review - status changes to PENDING_REVIEW."""
        response = client.post(f"/api/v1/reviews/submit/{self.__class__.template_id}")

        assert response.status_code == 200, f"Submit failed: {response.text}"
        result = response.json()

        assert result["template_id"] == self.__class__.template_id
        assert result["new_status"] == "pending_review"

    def test_05_verify_template_in_review_queue(self, client: TestClient):
        """Verify template appears in the pending review queue."""
        response = client.get("/api/v1/reviews/pending")

        assert response.status_code == 200, f"Failed to get pending reviews: {response.text}"
        data = response.json()

        # Find our template in the pending queue
        template_ids = [item["id"] for item in data["items"]]
        assert self.__class__.template_id in template_ids, (
            f"Template {self.__class__.template_id} not found in review queue. "
            f"Found: {template_ids}"
        )

        # Verify template status in queue
        template = next(item for item in data["items"] if item["id"] == self.__class__.template_id)
        assert template["status"] == "pending_review"
        assert template["is_verified"] is False, "Pending template should not be verified yet"

    def test_06_verify_template_status_pending_review(self, client: TestClient):
        """Verify template status is PENDING_REVIEW in template record."""
        response = client.get(f"/api/v1/templates/{self.__class__.template_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "pending_review"
        assert data["is_verified"] is False, "Template should not be verified during review"

    def test_07_approve_template_as_admin(self, client: TestClient):
        """Approve template as admin - status becomes PUBLISHED, is_verified=true."""
        review_request = {"feedback": "Approved for E2E testing"}
        response = client.post(
            f"/api/v1/reviews/{self.__class__.template_id}/approve",
            json=review_request,
        )

        assert response.status_code == 200, f"Approval failed: {response.text}"
        result = response.json()

        assert result["template_id"] == self.__class__.template_id
        assert result["action"] == "approve"
        assert result["new_status"] == "published"
        assert result["feedback"] == "Approved for E2E testing"

    def test_08_verify_is_verified_true_in_record(self, client: TestClient):
        """Verify is_verified=true in template record after approval."""
        response = client.get(f"/api/v1/templates/{self.__class__.template_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["is_verified"] is True, "Template should be verified after approval"
        assert data["status"] == "published", "Template should be published after approval"

    def test_09_verify_badge_displays_in_listing(self, client: TestClient):
        """Verify verified badge displays correctly - is_verified=true in list response."""
        response = client.get("/api/v1/templates")

        assert response.status_code == 200
        data = response.json()

        # Find our template in listing
        template = next(
            (item for item in data["items"] if item["id"] == self.__class__.template_id),
            None,
        )
        assert template is not None, "Template not found in listing"
        assert template["is_verified"] is True, (
            "Template should show is_verified=true in listing (verified badge)"
        )
        assert template["status"] == "published"

    def test_10_verify_filter_by_verified_returns_approved_template(self, client: TestClient):
        """Verify template appears when filtering by is_verified=true."""
        response = client.get("/api/v1/templates?is_verified=true")

        assert response.status_code == 200
        data = response.json()

        # Our template should be in verified results
        template_ids = [item["id"] for item in data["items"]]
        assert self.__class__.template_id in template_ids, (
            "Verified template should appear in is_verified=true filter results"
        )

    def test_11_verify_review_history(self, client: TestClient):
        """Verify review history contains the approval record."""
        response = client.get(f"/api/v1/reviews/{self.__class__.template_id}/history")

        assert response.status_code == 200
        data = response.json()

        # Should have at least 2 entries: submit and approve
        assert len(data) >= 2, f"Expected at least 2 review history entries, got {len(data)}"

        # Last entry should be the approval
        # Note: Due to how mock data works, we verify that approve action exists
        actions = [entry.get("action") for entry in data]
        assert "approve" in actions, f"Approve action not found in history. Actions: {actions}"

    def test_12_template_no_longer_in_review_queue(self, client: TestClient):
        """Verify approved template is no longer in the pending review queue."""
        response = client.get("/api/v1/reviews/pending")

        assert response.status_code == 200
        data = response.json()

        # Our template should NOT be in the pending queue anymore
        template_ids = [item["id"] for item in data["items"]]
        assert self.__class__.template_id not in template_ids, (
            "Approved template should not be in pending review queue"
        )


class TestRejectWorkflow:
    """Test the rejection workflow."""

    def test_01_upload_template_for_rejection(self, client: TestClient):
        """Upload a template to test rejection flow."""
        file_content = json.dumps({"policy": "reject_test"}, indent=2)
        files = {
            "file": ("reject_test.json", io.BytesIO(file_content.encode()), "application/json")
        }
        data = {
            "name": "Rejection Test Template",
            "description": "Testing the rejection workflow",
            "category": "audit",
        }

        response = client.post("/api/v1/templates/upload", files=files, data=data)
        assert response.status_code == 201
        self.__class__.reject_template_id = response.json()["id"]

    def test_02_submit_for_review(self, client: TestClient):
        """Submit template for review."""
        response = client.post(f"/api/v1/reviews/submit/{self.__class__.reject_template_id}")
        assert response.status_code == 200
        assert response.json()["new_status"] == "pending_review"

    def test_03_reject_template(self, client: TestClient):
        """Reject the template with feedback."""
        review_request = {"feedback": "Does not meet quality standards"}
        response = client.post(
            f"/api/v1/reviews/{self.__class__.reject_template_id}/reject",
            json=review_request,
        )

        assert response.status_code == 200
        result = response.json()
        assert result["action"] == "reject"
        assert result["new_status"] == "rejected"
        assert result["feedback"] == "Does not meet quality standards"

    def test_04_verify_rejected_not_verified(self, client: TestClient):
        """Verify rejected template is not verified."""
        response = client.get(f"/api/v1/templates/{self.__class__.reject_template_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["is_verified"] is False, "Rejected template should not be verified"
        assert data["status"] == "rejected"

    def test_05_resubmit_rejected_template(self, client: TestClient):
        """Resubmit rejected template for review."""
        response = client.post(f"/api/v1/reviews/{self.__class__.reject_template_id}/resubmit")

        assert response.status_code == 200
        result = response.json()
        assert result["new_status"] == "pending_review"

    def test_06_verify_resubmitted_in_queue(self, client: TestClient):
        """Verify resubmitted template is back in review queue."""
        response = client.get("/api/v1/reviews/pending")

        assert response.status_code == 200
        data = response.json()

        template_ids = [item["id"] for item in data["items"]]
        assert self.__class__.reject_template_id in template_ids, (
            "Resubmitted template should be in review queue"
        )


class TestReviewEdgeCases:
    """Test edge cases and error handling in review workflow."""

    def test_submit_already_published_fails(self, client: TestClient):
        """Submitting an already published template should fail."""
        # Use one of the seeded verified templates (ID 1, 2, or 3)
        response = client.post("/api/v1/reviews/submit/1")

        assert response.status_code == 400
        assert "cannot be submitted for review" in response.json()["detail"].lower()

    def test_approve_nonexistent_template(self, client: TestClient):
        """Approving a non-existent template should return 404."""
        response = client.post("/api/v1/reviews/99999/approve")
        assert response.status_code == 404

    def test_reject_nonexistent_template(self, client: TestClient):
        """Rejecting a non-existent template should return 404."""
        response = client.post("/api/v1/reviews/99999/reject")
        assert response.status_code == 404

    def test_approve_draft_template_fails(self, client: TestClient):
        """Approving a template that was never submitted should fail."""
        # Create a new draft template
        file_content = json.dumps({"policy": "draft_only"})
        files = {"file": ("draft.json", io.BytesIO(file_content.encode()), "application/json")}
        data = {
            "name": "Draft Only Template",
            "description": "This template will stay in draft",
            "category": "compliance",
        }
        upload_resp = client.post("/api/v1/templates/upload", files=files, data=data)
        assert upload_resp.status_code == 201
        draft_id = upload_resp.json()["id"]

        # Try to approve without submitting
        response = client.post(f"/api/v1/reviews/{draft_id}/approve")
        assert response.status_code == 400
        assert "not pending review" in response.json()["detail"].lower()


def run_standalone_tests():
    """Run tests standalone without pytest for quick verification."""
    client = TestClient(app)

    # Test 1: Health check
    resp = client.get("/health/ready")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"

    # Test 2: Upload template
    file_content = json.dumps(TEST_TEMPLATE_CONTENT, indent=2)
    files = {"file": ("review_e2e.json", io.BytesIO(file_content.encode()), "application/json")}
    data = {
        "name": TEST_TEMPLATE_NAME,
        "description": TEST_TEMPLATE_DESCRIPTION,
        "category": TEST_TEMPLATE_CATEGORY,
    }
    resp = client.post("/api/v1/templates/upload", files=files, data=data)
    assert resp.status_code == 201, f"Upload failed: {resp.text}"
    template_id = resp.json()["id"]
    assert resp.json()["status"] == "draft"
    assert resp.json()["is_verified"] is False

    # Test 3: Submit for review
    resp = client.post(f"/api/v1/reviews/submit/{template_id}")
    assert resp.status_code == 200, f"Submit failed: {resp.text}"
    assert resp.json()["new_status"] == "pending_review"

    # Test 4: Verify in review queue
    resp = client.get("/api/v1/reviews/pending")
    assert resp.status_code == 200
    queue_ids = [item["id"] for item in resp.json()["items"]]
    assert template_id in queue_ids, f"Template {template_id} not in queue: {queue_ids}"

    # Test 5: Verify template status
    resp = client.get(f"/api/v1/templates/{template_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending_review"
    assert resp.json()["is_verified"] is False

    # Test 6: Approve template
    resp = client.post(
        f"/api/v1/reviews/{template_id}/approve",
        json={"feedback": "E2E test approval"},
    )
    assert resp.status_code == 200, f"Approve failed: {resp.text}"
    assert resp.json()["action"] == "approve"
    assert resp.json()["new_status"] == "published"

    # Test 7: Verify is_verified=true
    resp = client.get(f"/api/v1/templates/{template_id}")
    assert resp.status_code == 200
    assert resp.json()["is_verified"] is True, "is_verified should be True after approval"
    assert resp.json()["status"] == "published"

    # Test 8: Verify badge in listing
    resp = client.get("/api/v1/templates")
    assert resp.status_code == 200
    template = next(
        (item for item in resp.json()["items"] if item["id"] == template_id),
        None,
    )
    assert template is not None
    assert template["is_verified"] is True, "is_verified should be True in listing"

    # Test 9: Verify filter works
    resp = client.get("/api/v1/templates?is_verified=true")
    assert resp.status_code == 200
    verified_ids = [item["id"] for item in resp.json()["items"]]
    assert template_id in verified_ids

    # Test 10: Verify review history
    resp = client.get(f"/api/v1/reviews/{template_id}/history")
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 2, f"Expected at least 2 history entries, got {len(history)}"

    # Test 11: Template not in pending queue
    resp = client.get("/api/v1/reviews/pending")
    assert resp.status_code == 200
    pending_ids = [item["id"] for item in resp.json()["items"]]
    assert template_id not in pending_ids

    # Test 12: Test rejection workflow
    # Upload another template
    files = {"file": ("reject_e2e.json", io.BytesIO(b'{"test": "reject"}'), "application/json")}
    data = {"name": "Reject Test", "description": "Testing rejection", "category": "audit"}
    resp = client.post("/api/v1/templates/upload", files=files, data=data)
    reject_id = resp.json()["id"]

    # Submit and reject
    client.post(f"/api/v1/reviews/submit/{reject_id}")
    resp = client.post(
        f"/api/v1/reviews/{reject_id}/reject",
        json={"feedback": "Needs improvements"},
    )
    assert resp.status_code == 200
    assert resp.json()["new_status"] == "rejected"

    # Verify still not verified
    resp = client.get(f"/api/v1/templates/{reject_id}")
    assert resp.json()["is_verified"] is False

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
