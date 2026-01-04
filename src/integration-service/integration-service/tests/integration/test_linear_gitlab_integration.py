"""
Integration Tests for Linear → GitLab Sync Flow

Tests cover the complete bidirectional synchronization flow between Linear and GitLab:
- Linear webhook → GitLab issue creation
- Linear issue update → GitLab issue update
- GitLab issue update → Linear issue update
- Comment synchronization (Linear ↔ GitLab)
- MR status synchronization (GitLab → Linear)
- Deduplication logic prevents infinite loops
- Conflict resolution with last-write-wins strategy

These are integration tests with mocked external APIs (Linear GraphQL, GitLab REST).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from src.integrations.linear.client import LinearClient
from src.integrations.linear.conflict_resolution import ConflictResolutionManager
from src.integrations.linear.deduplication import LinearDeduplicationManager
from src.integrations.linear.gitlab_sync import (
    GitLabAuthenticationError,
    GitLabNotFoundError,
    GitLabRateLimitError,
    GitLabSyncManager,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_gitlab_config():
    """Create mock GitLab configuration."""
    config = MagicMock()
    config.gitlab_token = SecretStr("glpat-test_token_12345")
    config.gitlab_url = "https://gitlab.com"
    config.gitlab_timeout_seconds = 30.0
    config.gitlab_max_retries = 3
    config.is_configured = True
    return config


@pytest.fixture
def mock_linear_config():
    """Create mock Linear configuration."""
    config = MagicMock()
    config.linear_api_key = SecretStr("lin_api_test_key_12345")
    config.linear_api_url = "https://api.linear.app/graphql"
    config.linear_team_id = "team-test-123"
    config.linear_project_id = None
    config.linear_timeout_seconds = 30.0
    config.linear_max_retries = 3
    return config


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client for state tracking."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=0)
    redis.lpush = AsyncMock(return_value=1)
    redis.lrange = AsyncMock(return_value=[])
    redis.expire = AsyncMock(return_value=True)
    redis.ping = AsyncMock(return_value=True)
    redis.close = AsyncMock()
    return redis


@pytest.fixture
async def mock_linear_client(mock_linear_config):
    """Create mock Linear client."""
    client = MagicMock(spec=LinearClient)
    client.config = mock_linear_config
    client._initialized = True
    client._client = MagicMock()

    # Mock async methods
    client.initialize = AsyncMock()
    client.close = AsyncMock()
    client.get_issue = AsyncMock()
    client.create_issue = AsyncMock()
    client.update_issue = AsyncMock()
    client.add_comment = AsyncMock()
    client.list_issues = AsyncMock()

    return client


@pytest.fixture
async def mock_dedup_manager(mock_redis_client):
    """Create mock deduplication manager."""
    manager = MagicMock(spec=LinearDeduplicationManager)
    manager._redis = mock_redis_client
    manager._initialized = True

    manager.connect = AsyncMock()
    manager.close = AsyncMock()
    manager.is_duplicate = AsyncMock(return_value=False)
    manager.mark_processed = AsyncMock()
    manager.should_process_event = AsyncMock(return_value=True)
    manager.record_sync = AsyncMock()

    return manager


@pytest.fixture
async def mock_conflict_manager(mock_redis_client):
    """Create mock conflict resolution manager."""
    manager = MagicMock(spec=ConflictResolutionManager)
    manager._state_manager = MagicMock()
    manager._state_manager._redis = mock_redis_client
    manager._initialized = True

    manager.connect = AsyncMock()
    manager.close = AsyncMock()
    manager.should_apply_update = AsyncMock(return_value=True)
    manager.record_update = AsyncMock()
    manager.resolve_conflict = AsyncMock()

    return manager


@pytest.fixture
def mock_gitlab_client():
    """Create mock GitLab client."""
    gitlab_client = MagicMock()

    # Mock authenticated user
    mock_user = MagicMock()
    mock_user.username = "test-user"
    gitlab_client.user = mock_user
    gitlab_client.auth = MagicMock()

    # Mock projects manager
    gitlab_client.projects = MagicMock()

    return gitlab_client


@pytest.fixture
def mock_gitlab_project():
    """Create mock GitLab project."""
    project = MagicMock()
    project.id = 12345
    project.path_with_namespace = "test-org/test-repo"
    project.web_url = "https://gitlab.com/test-org/test-repo"
    project.issues = MagicMock()
    return project


@pytest.fixture
def mock_gitlab_issue():
    """Create mock GitLab issue."""
    issue = MagicMock()
    issue.iid = 42
    issue.title = "Test GitLab Issue"
    issue.description = "This is a test issue from GitLab"
    issue.state = "opened"
    issue.web_url = "https://gitlab.com/test-org/test-repo/-/issues/42"
    issue.created_at = "2024-01-01T00:00:00Z"
    issue.updated_at = "2024-01-02T00:00:00Z"
    issue.author = MagicMock()
    issue.author.username = "gitlab-user"
    issue.state_event = None
    issue.save = MagicMock()
    issue.notes = MagicMock()
    return issue


@pytest.fixture
def mock_gitlab_comment():
    """Create mock GitLab note (comment)."""
    note = MagicMock()
    note.id = 123456
    note.body = "This is a test comment from GitLab"
    note.author = MagicMock()
    note.author.username = "commenter"
    note.created_at = "2024-01-01T00:00:00Z"
    note.updated_at = "2024-01-01T00:00:00Z"
    return note


@pytest.fixture
def mock_gitlab_mr():
    """Create mock GitLab merge request."""
    mr = MagicMock()
    mr.iid = 10
    mr.title = "Test MR"
    mr.state = "opened"
    mr.web_url = "https://gitlab.com/test-org/test-repo/-/merge_requests/10"
    mr.created_at = "2024-01-01T00:00:00Z"
    mr.updated_at = "2024-01-02T00:00:00Z"
    return mr


@pytest.fixture
def sample_linear_issue():
    """Create sample Linear issue data."""
    return {
        "id": "linear-issue-123",
        "identifier": "ENG-123",
        "title": "Test Linear Issue",
        "description": "This is a test issue from Linear",
        "priority": 2,
        "url": "https://linear.app/test/issue/ENG-123",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-02T00:00:00.000Z",
        "state": {
            "id": "state-123",
            "name": "In Progress",
            "type": "started",
        },
        "assignee": {
            "id": "user-123",
            "name": "Test User",
        },
        "team": {
            "id": "team-123",
            "name": "Engineering",
            "key": "ENG",
        },
        "labels": {
            "nodes": [
                {"id": "label-1", "name": "bug"},
                {"id": "label-2", "name": "priority-high"},
            ]
        },
    }


@pytest.fixture
def sample_linear_webhook_payload(sample_linear_issue):
    """Create sample Linear webhook payload for issue creation."""
    return {
        "action": "create",
        "type": "Issue",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "organizationId": "org-123",
        "webhookId": "webhook-456",
        "url": "https://linear.app/test/issue/ENG-123",
        "data": sample_linear_issue,
    }


@pytest.fixture
async def gitlab_sync_manager(
    mock_gitlab_config,
    mock_linear_client,
    mock_dedup_manager,
    mock_conflict_manager,
):
    """Create GitLabSyncManager instance for testing."""
    manager = GitLabSyncManager(
        gitlab_config=mock_gitlab_config,
        linear_client=mock_linear_client,
        dedup_manager=mock_dedup_manager,
        conflict_manager=mock_conflict_manager,
    )
    return manager


# ============================================================================
# Integration Tests: Linear → GitLab Sync Flow
# ============================================================================


@pytest.mark.asyncio
async def test_linear_webhook_triggers_gitlab_issue_creation(
    gitlab_sync_manager,
    mock_gitlab_client,
    mock_gitlab_project,
    sample_linear_issue,
    mock_gitlab_issue,
):
    """Test that Linear webhook triggers GitLab issue creation."""
    # Setup
    patch_path = "src.integrations.linear.gitlab_sync.gitlab.Gitlab"
    with patch(patch_path, return_value=mock_gitlab_client):
        await gitlab_sync_manager.initialize()

        # Mock GitLab project and issue creation
        mock_gitlab_client.projects.get = MagicMock(return_value=mock_gitlab_project)
        mock_gitlab_project.issues.create = MagicMock(return_value=mock_gitlab_issue)

        # Sync Linear issue to GitLab
        result = await gitlab_sync_manager.sync_linear_to_gitlab(
            linear_issue_id=sample_linear_issue["id"],
            project_id="test-org/test-repo",
            create_if_missing=True,
        )

        # Verify GitLab issue was created
        assert result is not None
        assert result.iid == mock_gitlab_issue.iid
        mock_gitlab_project.issues.create.assert_called_once()

        # Verify issue title and labels
        call_args = mock_gitlab_project.issues.create.call_args
        issue_data = call_args.args[0]
        assert "Test Linear Issue" in issue_data["title"]
        assert "linear-sync" in issue_data["labels"]
        assert "bug" in issue_data["labels"]

        # Verify deduplication was checked
        gitlab_sync_manager._dedup_manager.should_process_event.assert_called()
        gitlab_sync_manager._dedup_manager.mark_processed.assert_called()

        await gitlab_sync_manager.close()


@pytest.mark.asyncio
async def test_linear_issue_update_syncs_to_gitlab(
    gitlab_sync_manager,
    mock_gitlab_client,
    mock_gitlab_project,
    sample_linear_issue,
    mock_gitlab_issue,
):
    """Test that Linear issue updates sync to existing GitLab issue."""
    # Setup
    patch_path = "src.integrations.linear.gitlab_sync.gitlab.Gitlab"
    with patch(patch_path, return_value=mock_gitlab_client):
        await gitlab_sync_manager.initialize()

        # Mock GitLab project and issue retrieval
        mock_gitlab_client.projects.get = MagicMock(return_value=mock_gitlab_project)
        mock_gitlab_project.issues.get = MagicMock(return_value=mock_gitlab_issue)

        # Update Linear issue data
        sample_linear_issue["title"] = "Updated Linear Issue Title"
        sample_linear_issue["state"]["type"] = "completed"

        # Sync updated Linear issue to GitLab
        result = await gitlab_sync_manager.sync_linear_to_gitlab(
            linear_issue_id=sample_linear_issue["id"],
            project_id="test-org/test-repo",
            gitlab_issue_iid=42,
        )

        # Verify GitLab issue was updated
        assert result is not None
        mock_gitlab_issue.save.assert_called()

        # Check that the issue was closed (Linear state is completed)
        assert mock_gitlab_issue.state_event == "close"

        await gitlab_sync_manager.close()


@pytest.mark.asyncio
async def test_gitlab_issue_creation_syncs_to_linear(
    gitlab_sync_manager,
    mock_gitlab_client,
    mock_gitlab_project,
    mock_linear_client,
    mock_gitlab_issue,
):
    """Test that GitLab issue creation syncs to Linear."""
    # Setup
    patch_path = "src.integrations.linear.gitlab_sync.gitlab.Gitlab"
    with patch(patch_path, return_value=mock_gitlab_client):
        await gitlab_sync_manager.initialize()

        # Mock GitLab project
        mock_gitlab_client.projects.get = MagicMock(return_value=mock_gitlab_project)
        mock_gitlab_project.issues.get = MagicMock(return_value=mock_gitlab_issue)

        # Mock Linear issue creation
        created_linear_issue = {
            "id": "linear-new-123",
            "identifier": "ENG-456",
            "title": "[GitLab] Test GitLab Issue",
            "description": "Synced from GitLab",
        }
        mock_linear_client.create_issue.return_value = created_linear_issue

        # Sync GitLab issue to Linear
        result = await gitlab_sync_manager.sync_gitlab_to_linear(
            project_id="test-org/test-repo",
            gitlab_issue_iid=42,
            create_if_missing=True,
        )

        # Verify Linear issue was created
        assert result is not None
        assert result["id"] == "linear-new-123"
        mock_linear_client.create_issue.assert_called_once()

        # Verify GitLab prefix in title
        call_args = mock_linear_client.create_issue.call_args
        assert "[GitLab]" in call_args.kwargs["title"]
        assert "gitlab.com/test-org/test-repo/-/issues/42" in call_args.kwargs["description"]

        await gitlab_sync_manager.close()


@pytest.mark.asyncio
async def test_gitlab_issue_update_syncs_to_linear(
    gitlab_sync_manager,
    mock_gitlab_client,
    mock_gitlab_project,
    mock_linear_client,
    mock_gitlab_issue,
):
    """Test that GitLab issue updates sync to Linear."""
    # Setup
    patch_path = "src.integrations.linear.gitlab_sync.gitlab.Gitlab"
    with patch(patch_path, return_value=mock_gitlab_client):
        await gitlab_sync_manager.initialize()

        # Mock GitLab project
        mock_gitlab_client.projects.get = MagicMock(return_value=mock_gitlab_project)
        mock_gitlab_project.issues.get = MagicMock(return_value=mock_gitlab_issue)

        # Mock Linear issue update
        updated_linear_issue = {
            "id": "linear-123",
            "identifier": "ENG-123",
            "title": "[GitLab] Test GitLab Issue",
            "description": "Updated from GitLab",
        }
        mock_linear_client.update_issue.return_value = updated_linear_issue

        # Sync GitLab issue to existing Linear issue
        result = await gitlab_sync_manager.sync_gitlab_to_linear(
            project_id="test-org/test-repo",
            gitlab_issue_iid=42,
            linear_issue_id="linear-123",
        )

        # Verify Linear issue was updated
        assert result is not None
        mock_linear_client.update_issue.assert_called_once()

        # Verify conflict resolution was checked
        gitlab_sync_manager._conflict_manager.should_apply_update.assert_called()
        gitlab_sync_manager._conflict_manager.record_update.assert_called()

        await gitlab_sync_manager.close()


@pytest.mark.asyncio
async def test_bidirectional_sync_no_infinite_loop(
    gitlab_sync_manager,
    mock_gitlab_client,
    mock_gitlab_project,
    mock_linear_client,
    sample_linear_issue,
    mock_gitlab_issue,
):
    """Test that bidirectional sync doesn't create infinite loops."""
    # Setup
    patch_path = "src.integrations.linear.gitlab_sync.gitlab.Gitlab"
    with patch(patch_path, return_value=mock_gitlab_client):
        await gitlab_sync_manager.initialize()

        mock_gitlab_client.projects.get = MagicMock(return_value=mock_gitlab_project)
        mock_gitlab_project.issues.create = MagicMock(return_value=mock_gitlab_issue)
        mock_gitlab_project.issues.get = MagicMock(return_value=mock_gitlab_issue)

        # First sync: Linear → GitLab (should succeed)
        gitlab_sync_manager._dedup_manager.should_process_event.return_value = True
        result1 = await gitlab_sync_manager.sync_linear_to_gitlab(
            linear_issue_id=sample_linear_issue["id"],
            project_id="test-org/test-repo",
        )
        assert result1 is not None

        # Simulate deduplication manager detecting loop on second sync attempt
        gitlab_sync_manager._dedup_manager.should_process_event.return_value = False

        # Second sync: GitLab → Linear (should be blocked by deduplication)
        result2 = await gitlab_sync_manager.sync_gitlab_to_linear(
            project_id="test-org/test-repo",
            gitlab_issue_iid=42,
            linear_issue_id=sample_linear_issue["id"],
        )
        assert result2 is None  # Sync blocked due to deduplication

        # Verify deduplication manager was called multiple times
        assert gitlab_sync_manager._dedup_manager.should_process_event.call_count >= 2

        await gitlab_sync_manager.close()


@pytest.mark.asyncio
async def test_linear_comment_syncs_to_gitlab(
    gitlab_sync_manager,
    mock_gitlab_client,
    mock_gitlab_issue,
):
    """Test that Linear comments sync to GitLab."""
    # Setup
    patch_path = "src.integrations.linear.gitlab_sync.gitlab.Gitlab"
    with patch(patch_path, return_value=mock_gitlab_client):
        await gitlab_sync_manager.initialize()

        # Mock GitLab comment creation
        mock_note = MagicMock()
        mock_note.id = 789
        mock_gitlab_issue.notes.create = MagicMock(return_value=mock_note)

        # Sync Linear comment to GitLab
        result = await gitlab_sync_manager.sync_linear_comment_to_gitlab(
            gitlab_issue=mock_gitlab_issue,
            linear_comment_body="This is a test comment from Linear",
            linear_comment_user="Test User",
        )

        # Verify comment was created
        assert result is not None
        mock_gitlab_issue.notes.create.assert_called_once()

        # Verify comment includes attribution
        call_args = mock_gitlab_issue.notes.create.call_args
        comment_data = call_args.args[0]
        assert "Test User" in comment_data["body"]
        assert "Linear" in comment_data["body"]

        await gitlab_sync_manager.close()


@pytest.mark.asyncio
async def test_gitlab_comment_syncs_to_linear(
    gitlab_sync_manager,
    mock_gitlab_client,
    mock_linear_client,
):
    """Test that GitLab comments sync to Linear."""
    # Setup
    patch_path = "src.integrations.linear.gitlab_sync.gitlab.Gitlab"
    with patch(patch_path, return_value=mock_gitlab_client):
        await gitlab_sync_manager.initialize()

        # Mock Linear comment creation
        created_comment = {
            "id": "comment-123",
            "body": "Comment from GitLab",
        }
        mock_linear_client.add_comment.return_value = created_comment

        # Sync GitLab comment to Linear
        result = await gitlab_sync_manager.sync_gitlab_comment_to_linear(
            linear_issue_id="linear-123",
            gitlab_comment_body="This is a test comment from GitLab",
            gitlab_comment_author="commenter",
            gitlab_comment_id=123456,
        )

        # Verify comment was created
        assert result is not None
        mock_linear_client.add_comment.assert_called_once()

        # Verify comment includes GitLab user attribution
        call_args = mock_linear_client.add_comment.call_args
        assert "commenter" in call_args.kwargs["body"]
        assert "GitLab" in call_args.kwargs["body"]

        # Verify deduplication
        gitlab_sync_manager._dedup_manager.should_process_event.assert_called()
        gitlab_sync_manager._dedup_manager.mark_processed.assert_called()

        await gitlab_sync_manager.close()


@pytest.mark.asyncio
async def test_mr_merged_status_syncs_to_linear(
    gitlab_sync_manager,
    mock_gitlab_client,
    mock_linear_client,
    mock_gitlab_mr,
):
    """Test that merged MR status syncs to Linear issue."""
    # Setup
    patch_path = "src.integrations.linear.gitlab_sync.gitlab.Gitlab"
    with patch(patch_path, return_value=mock_gitlab_client):
        await gitlab_sync_manager.initialize()

        # Mock merged MR
        mock_gitlab_mr.state = "merged"

        # Mock Linear comment creation
        created_comment = {
            "id": "comment-mr-123",
            "body": "MR merged notification",
        }
        mock_linear_client.add_comment.return_value = created_comment

        # Sync MR status to Linear
        result = await gitlab_sync_manager.sync_mr_status_to_linear(
            linear_issue_id="linear-123",
            merge_request=mock_gitlab_mr,
        )

        # Verify comment was added
        assert result is not None
        mock_linear_client.add_comment.assert_called_once()

        # Verify comment indicates merge
        call_args = mock_linear_client.add_comment.call_args
        assert "merged" in call_args.kwargs["body"].lower()
        assert mock_gitlab_mr.web_url in call_args.kwargs["body"]

        await gitlab_sync_manager.close()


@pytest.mark.asyncio
async def test_mr_closed_status_syncs_to_linear(
    gitlab_sync_manager,
    mock_gitlab_client,
    mock_linear_client,
    mock_gitlab_mr,
):
    """Test that closed MR status (without merge) syncs to Linear."""
    # Setup
    patch_path = "src.integrations.linear.gitlab_sync.gitlab.Gitlab"
    with patch(patch_path, return_value=mock_gitlab_client):
        await gitlab_sync_manager.initialize()

        # Mock closed (not merged) MR
        mock_gitlab_mr.state = "closed"

        # Mock Linear comment creation
        created_comment = {
            "id": "comment-mr-456",
            "body": "MR closed notification",
        }
        mock_linear_client.add_comment.return_value = created_comment

        # Sync MR status to Linear
        result = await gitlab_sync_manager.sync_mr_status_to_linear(
            linear_issue_id="linear-123",
            merge_request=mock_gitlab_mr,
        )

        # Verify comment was added
        assert result is not None
        mock_linear_client.add_comment.assert_called_once()

        # Verify comment indicates closure without merge
        call_args = mock_linear_client.add_comment.call_args
        assert "closed" in call_args.kwargs["body"].lower()

        await gitlab_sync_manager.close()


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_gitlab_authentication_error(
    gitlab_sync_manager,
    mock_gitlab_client,
):
    """Test handling of GitLab authentication errors."""
    from gitlab.exceptions import GitlabAuthenticationError as GitlabAuthError

    patch_path = "src.integrations.linear.gitlab_sync.gitlab.Gitlab"
    with patch(patch_path, return_value=mock_gitlab_client):
        # Mock authentication failure
        mock_gitlab_client.auth.side_effect = GitlabAuthError("401: Unauthorized")

        # Verify authentication error is raised
        with pytest.raises(GitLabAuthenticationError) as exc_info:
            await gitlab_sync_manager.initialize()

        assert "authentication failed" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_gitlab_project_not_found(
    gitlab_sync_manager,
    mock_gitlab_client,
    sample_linear_issue,
):
    """Test handling of project not found errors."""
    from gitlab.exceptions import GitlabGetError

    patch_path = "src.integrations.linear.gitlab_sync.gitlab.Gitlab"
    with patch(patch_path, return_value=mock_gitlab_client):
        await gitlab_sync_manager.initialize()

        # Mock project not found
        mock_error = GitlabGetError("404: Project Not Found")
        mock_error.response_code = 404
        mock_gitlab_client.projects.get.side_effect = mock_error

        # Verify not found error is raised
        with pytest.raises(GitLabNotFoundError) as exc_info:
            await gitlab_sync_manager.sync_linear_to_gitlab(
                linear_issue_id=sample_linear_issue["id"],
                project_id="nonexistent/repo",
            )

        assert "not found" in str(exc_info.value).lower()

        await gitlab_sync_manager.close()


@pytest.mark.asyncio
async def test_gitlab_rate_limit_error(
    gitlab_sync_manager,
    mock_gitlab_client,
    sample_linear_issue,
):
    """Test handling of GitLab rate limit errors."""
    from gitlab.exceptions import GitlabGetError

    patch_path = "src.integrations.linear.gitlab_sync.gitlab.Gitlab"
    with patch(patch_path, return_value=mock_gitlab_client):
        await gitlab_sync_manager.initialize()

        # Mock rate limit error with retry info
        mock_error = GitlabGetError("429: Too Many Requests")
        mock_error.response_code = 429
        mock_error.response_headers = {"Retry-After": "60"}
        mock_gitlab_client.projects.get.side_effect = mock_error

        # Verify rate limit error is raised
        with pytest.raises(GitLabRateLimitError) as exc_info:
            await gitlab_sync_manager.sync_linear_to_gitlab(
                linear_issue_id=sample_linear_issue["id"],
                project_id="test/repo",
            )

        assert "rate limit" in str(exc_info.value).lower()
        assert exc_info.value.retry_after == 60

        await gitlab_sync_manager.close()


@pytest.mark.asyncio
async def test_conflict_resolution_blocks_older_update(
    gitlab_sync_manager,
    mock_gitlab_client,
    mock_linear_client,
    sample_linear_issue,
):
    """Test that conflict resolution blocks older updates."""
    # Setup
    patch_path = "src.integrations.linear.gitlab_sync.gitlab.Gitlab"
    with patch(patch_path, return_value=mock_gitlab_client):
        await gitlab_sync_manager.initialize()

        # Mock conflict resolution to reject update (older)
        gitlab_sync_manager._conflict_manager.should_apply_update.return_value = False

        # Attempt to sync (should be blocked)
        result = await gitlab_sync_manager.sync_linear_to_gitlab(
            linear_issue_id=sample_linear_issue["id"],
            project_id="test-org/test-repo",
        )

        # Verify sync was skipped
        assert result is None

        # Verify conflict manager was consulted
        gitlab_sync_manager._conflict_manager.should_apply_update.assert_called()

        await gitlab_sync_manager.close()


@pytest.mark.asyncio
async def test_complete_bidirectional_flow_with_comments(
    gitlab_sync_manager,
    mock_gitlab_client,
    mock_gitlab_project,
    mock_linear_client,
    sample_linear_issue,
    mock_gitlab_issue,
    mock_gitlab_comment,
):
    """Test complete bidirectional flow: Linear → GitLab → Comments → Linear."""
    # Setup
    patch_path = "src.integrations.linear.gitlab_sync.gitlab.Gitlab"
    with patch(patch_path, return_value=mock_gitlab_client):
        await gitlab_sync_manager.initialize()

        # Step 1: Create GitLab issue from Linear
        mock_gitlab_client.projects.get = MagicMock(return_value=mock_gitlab_project)
        mock_gitlab_project.issues.create = MagicMock(return_value=mock_gitlab_issue)
        mock_gitlab_project.issues.get = MagicMock(return_value=mock_gitlab_issue)

        gitlab_issue = await gitlab_sync_manager.sync_linear_to_gitlab(
            linear_issue_id=sample_linear_issue["id"],
            project_id="test-org/test-repo",
        )
        assert gitlab_issue is not None
        assert gitlab_issue.iid == 42

        # Step 2: Add comment on GitLab and sync to Linear
        created_linear_comment = {
            "id": "linear-comment-123",
            "body": "Comment from GitLab",
        }
        mock_linear_client.add_comment.return_value = created_linear_comment

        linear_comment = await gitlab_sync_manager.sync_gitlab_comment_to_linear(
            linear_issue_id=sample_linear_issue["id"],
            gitlab_comment_body=mock_gitlab_comment.body,
            gitlab_comment_author=mock_gitlab_comment.author.username,
            gitlab_comment_id=mock_gitlab_comment.id,
        )
        assert linear_comment is not None

        # Step 3: Add comment on Linear and sync to GitLab
        mock_gitlab_note_result = MagicMock()
        mock_gitlab_note_result.id = 999
        mock_gitlab_issue.notes.create = MagicMock(return_value=mock_gitlab_note_result)

        gitlab_comment = await gitlab_sync_manager.sync_linear_comment_to_gitlab(
            gitlab_issue=gitlab_issue,
            linear_comment_body="Reply from Linear",
            linear_comment_user="Linear User",
        )
        assert gitlab_comment is not None

        # Verify all syncs completed
        assert mock_gitlab_project.issues.create.call_count == 1
        assert mock_linear_client.add_comment.call_count == 1
        assert mock_gitlab_issue.notes.create.call_count == 1

        await gitlab_sync_manager.close()


@pytest.mark.asyncio
async def test_sync_manager_context_manager(
    mock_gitlab_config,
    mock_linear_client,
    mock_dedup_manager,
    mock_conflict_manager,
    mock_gitlab_client,
):
    """Test GitLabSyncManager as async context manager."""
    patch_path = "src.integrations.linear.gitlab_sync.gitlab.Gitlab"
    with patch(patch_path, return_value=mock_gitlab_client):
        manager = GitLabSyncManager(
            gitlab_config=mock_gitlab_config,
            linear_client=mock_linear_client,
            dedup_manager=mock_dedup_manager,
            conflict_manager=mock_conflict_manager,
        )

        # Use as context manager
        async with manager as sync_mgr:
            assert sync_mgr._initialized is True
            assert sync_mgr._gitlab_client is not None

        # Verify cleanup
        assert manager._initialized is False


@pytest.mark.asyncio
async def test_deduplication_event_id_generation(
    gitlab_sync_manager,
    mock_gitlab_client,
    mock_gitlab_project,
    sample_linear_issue,
    mock_gitlab_issue,
):
    """Test that event IDs are properly generated for deduplication."""
    # Setup
    patch_path = "src.integrations.linear.gitlab_sync.gitlab.Gitlab"
    with patch(patch_path, return_value=mock_gitlab_client):
        await gitlab_sync_manager.initialize()

        mock_gitlab_client.projects.get = MagicMock(return_value=mock_gitlab_project)
        mock_gitlab_project.issues.create = MagicMock(return_value=mock_gitlab_issue)

        # Sync issue
        await gitlab_sync_manager.sync_linear_to_gitlab(
            linear_issue_id=sample_linear_issue["id"],
            project_id="test-org/test-repo",
        )

        # Verify event ID contains issue ID and timestamp
        call_args = gitlab_sync_manager._dedup_manager.should_process_event.call_args
        event_id = call_args.kwargs["event_id"]

        assert "linear-to-gitlab" in event_id
        assert sample_linear_issue["id"] in event_id
        assert sample_linear_issue["updatedAt"] in event_id

        await gitlab_sync_manager.close()


@pytest.mark.asyncio
async def test_gitlab_issue_state_transitions(
    gitlab_sync_manager,
    mock_gitlab_client,
    mock_gitlab_project,
    sample_linear_issue,
    mock_gitlab_issue,
):
    """Test GitLab issue state transitions based on Linear state."""
    # Setup
    patch_path = "src.integrations.linear.gitlab_sync.gitlab.Gitlab"
    with patch(patch_path, return_value=mock_gitlab_client):
        await gitlab_sync_manager.initialize()

        mock_gitlab_client.projects.get = MagicMock(return_value=mock_gitlab_project)
        mock_gitlab_project.issues.get = MagicMock(return_value=mock_gitlab_issue)

        # Test case 1: Linear completed → GitLab closed
        sample_linear_issue["state"]["type"] = "completed"
        mock_gitlab_issue.state = "opened"

        await gitlab_sync_manager.sync_linear_to_gitlab(
            linear_issue_id=sample_linear_issue["id"],
            project_id="test-org/test-repo",
            gitlab_issue_iid=42,
        )

        assert mock_gitlab_issue.state_event == "close"
        mock_gitlab_issue.save.assert_called()

        # Test case 2: Linear started → GitLab reopened
        sample_linear_issue["state"]["type"] = "started"
        mock_gitlab_issue.state = "closed"
        mock_gitlab_issue.state_event = None

        await gitlab_sync_manager.sync_linear_to_gitlab(
            linear_issue_id=sample_linear_issue["id"],
            project_id="test-org/test-repo",
            gitlab_issue_iid=42,
        )

        assert mock_gitlab_issue.state_event == "reopen"

        await gitlab_sync_manager.close()
