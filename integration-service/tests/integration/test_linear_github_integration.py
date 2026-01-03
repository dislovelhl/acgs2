"""
Integration Tests for Linear → GitHub Sync Flow

Tests cover the complete bidirectional synchronization flow between Linear and GitHub:
- Linear webhook → GitHub issue creation
- Linear issue update → GitHub issue update
- GitHub issue update → Linear issue update
- Comment synchronization (Linear ↔ GitHub)
- PR status synchronization (GitHub → Linear)
- Deduplication logic prevents infinite loops
- Conflict resolution with last-write-wins strategy

These are integration tests with mocked external APIs (Linear GraphQL, GitHub REST).
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from src.integrations.linear.client import LinearClient
from src.integrations.linear.conflict_resolution import ConflictResolutionManager
from src.integrations.linear.deduplication import LinearDeduplicationManager
from src.integrations.linear.github_sync import (
    GitHubAuthenticationError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubSyncManager,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_github_config():
    """Create mock GitHub configuration."""
    config = MagicMock()
    config.github_token = SecretStr("ghp_test_token_12345")
    config.github_timeout_seconds = 30.0
    config.github_max_retries = 3
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
def mock_github_client():
    """Create mock GitHub client."""
    github = MagicMock()

    # Mock user for authentication verification
    mock_user = MagicMock()
    mock_user.login = "test-user"
    github.get_user = MagicMock(return_value=mock_user)

    # Mock repository
    mock_repo = MagicMock()
    github.get_repo = MagicMock(return_value=mock_repo)

    # Mock close method
    github.close = MagicMock()

    return github


@pytest.fixture
def mock_github_issue():
    """Create mock GitHub issue."""
    issue = MagicMock()
    issue.number = 42
    issue.title = "Test GitHub Issue"
    issue.body = "This is a test issue from GitHub"
    issue.state = "open"
    issue.html_url = "https://github.com/test/repo/issues/42"
    issue.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    issue.updated_at = datetime(2024, 1, 2, tzinfo=timezone.utc)
    issue.user = MagicMock()
    issue.user.login = "github-user"
    issue.edit = MagicMock()
    issue.create_comment = MagicMock()
    return issue


@pytest.fixture
def mock_github_comment():
    """Create mock GitHub comment."""
    comment = MagicMock()
    comment.id = 123456
    comment.body = "This is a test comment from GitHub"
    comment.user = MagicMock()
    comment.user.login = "commenter"
    comment.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    comment.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return comment


@pytest.fixture
def mock_github_pr():
    """Create mock GitHub pull request."""
    pr = MagicMock()
    pr.number = 10
    pr.title = "Test PR"
    pr.state = "open"
    pr.merged = False
    pr.html_url = "https://github.com/test/repo/pull/10"
    pr.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    pr.updated_at = datetime(2024, 1, 2, tzinfo=timezone.utc)
    return pr


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
async def github_sync_manager(
    mock_github_config,
    mock_linear_client,
    mock_dedup_manager,
    mock_conflict_manager,
):
    """Create GitHubSyncManager instance for testing."""
    manager = GitHubSyncManager(
        github_config=mock_github_config,
        linear_client=mock_linear_client,
        dedup_manager=mock_dedup_manager,
        conflict_manager=mock_conflict_manager,
    )
    return manager


# ============================================================================
# Integration Tests: Linear → GitHub Sync Flow
# ============================================================================


@pytest.mark.asyncio
async def test_linear_webhook_triggers_github_issue_creation(
    github_sync_manager,
    mock_github_client,
    sample_linear_issue,
    mock_github_issue,
):
    """Test that Linear webhook triggers GitHub issue creation."""
    # Setup
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()

        # Mock GitHub repository and issue creation
        mock_repo = mock_github_client.get_repo.return_value
        mock_repo.create_issue = MagicMock(return_value=mock_github_issue)

        # Sync Linear issue to GitHub
        result = await github_sync_manager.sync_linear_to_github(
            linear_issue_id=sample_linear_issue["id"],
            repo_owner="test-org",
            repo_name="test-repo",
            create_if_missing=True,
        )

        # Verify GitHub issue was created
        assert result is not None
        assert result.number == mock_github_issue.number
        mock_repo.create_issue.assert_called_once()

        # Verify issue title and labels
        call_args = mock_repo.create_issue.call_args
        assert "Test Linear Issue" in call_args.kwargs["title"]
        assert "linear-sync" in call_args.kwargs["labels"]
        assert "bug" in call_args.kwargs["labels"]

        # Verify deduplication was checked
        github_sync_manager._dedup_manager.should_process_event.assert_called()
        github_sync_manager._dedup_manager.mark_processed.assert_called()

        await github_sync_manager.close()


@pytest.mark.asyncio
async def test_linear_issue_update_syncs_to_github(
    github_sync_manager,
    mock_github_client,
    sample_linear_issue,
    mock_github_issue,
):
    """Test that Linear issue updates sync to existing GitHub issue."""
    # Setup
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()

        # Mock GitHub repository and issue retrieval
        mock_repo = mock_github_client.get_repo.return_value
        mock_repo.get_issue = MagicMock(return_value=mock_github_issue)

        # Update Linear issue data
        sample_linear_issue["title"] = "Updated Linear Issue Title"
        sample_linear_issue["state"]["type"] = "completed"

        # Sync updated Linear issue to GitHub
        result = await github_sync_manager.sync_linear_to_github(
            linear_issue_id=sample_linear_issue["id"],
            repo_owner="test-org",
            repo_name="test-repo",
            github_issue_number=42,
        )

        # Verify GitHub issue was updated
        assert result is not None
        mock_github_issue.edit.assert_called()

        # Check that the issue was closed (Linear state is completed)
        edit_calls = [
            call for call in mock_github_issue.edit.call_args_list if "state" in call.kwargs
        ]
        if edit_calls:
            assert edit_calls[0].kwargs["state"] == "closed"

        await github_sync_manager.close()


@pytest.mark.asyncio
async def test_github_issue_creation_syncs_to_linear(
    github_sync_manager,
    mock_github_client,
    mock_linear_client,
    mock_github_issue,
):
    """Test that GitHub issue creation syncs to Linear."""
    # Setup
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()

        # Mock GitHub repository
        mock_repo = mock_github_client.get_repo.return_value
        mock_repo.get_issue = MagicMock(return_value=mock_github_issue)

        # Mock Linear issue creation
        created_linear_issue = {
            "id": "linear-new-123",
            "identifier": "ENG-456",
            "title": "[GitHub] Test GitHub Issue",
            "description": "Synced from GitHub",
        }
        mock_linear_client.create_issue.return_value = created_linear_issue

        # Sync GitHub issue to Linear
        result = await github_sync_manager.sync_github_to_linear(
            repo_owner="test-org",
            repo_name="test-repo",
            github_issue_number=42,
            create_if_missing=True,
        )

        # Verify Linear issue was created
        assert result is not None
        assert result["id"] == "linear-new-123"
        mock_linear_client.create_issue.assert_called_once()

        # Verify GitHub prefix in title
        call_args = mock_linear_client.create_issue.call_args
        assert "[GitHub]" in call_args.kwargs["title"]
        assert "github.com/test/repo/issues/42" in call_args.kwargs["description"]

        await github_sync_manager.close()


@pytest.mark.asyncio
async def test_github_issue_update_syncs_to_linear(
    github_sync_manager,
    mock_github_client,
    mock_linear_client,
    mock_github_issue,
):
    """Test that GitHub issue updates sync to Linear."""
    # Setup
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()

        # Mock GitHub repository
        mock_repo = mock_github_client.get_repo.return_value
        mock_repo.get_issue = MagicMock(return_value=mock_github_issue)

        # Mock Linear issue update
        updated_linear_issue = {
            "id": "linear-123",
            "identifier": "ENG-123",
            "title": "[GitHub] Test GitHub Issue",
            "description": "Updated from GitHub",
        }
        mock_linear_client.update_issue.return_value = updated_linear_issue

        # Sync GitHub issue to existing Linear issue
        result = await github_sync_manager.sync_github_to_linear(
            repo_owner="test-org",
            repo_name="test-repo",
            github_issue_number=42,
            linear_issue_id="linear-123",
        )

        # Verify Linear issue was updated
        assert result is not None
        mock_linear_client.update_issue.assert_called_once()

        # Verify conflict resolution was checked
        github_sync_manager._conflict_manager.should_apply_update.assert_called()
        github_sync_manager._conflict_manager.record_update.assert_called()

        await github_sync_manager.close()


@pytest.mark.asyncio
async def test_bidirectional_sync_no_infinite_loop(
    github_sync_manager,
    mock_github_client,
    mock_linear_client,
    sample_linear_issue,
    mock_github_issue,
):
    """Test that bidirectional sync doesn't create infinite loops."""
    # Setup
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()

        mock_repo = mock_github_client.get_repo.return_value
        mock_repo.create_issue = MagicMock(return_value=mock_github_issue)
        mock_repo.get_issue = MagicMock(return_value=mock_github_issue)

        # First sync: Linear → GitHub (should succeed)
        github_sync_manager._dedup_manager.should_process_event.return_value = True
        result1 = await github_sync_manager.sync_linear_to_github(
            linear_issue_id=sample_linear_issue["id"],
            repo_owner="test-org",
            repo_name="test-repo",
        )
        assert result1 is not None

        # Simulate deduplication manager detecting loop on second sync attempt
        github_sync_manager._dedup_manager.should_process_event.return_value = False

        # Second sync: GitHub → Linear (should be blocked by deduplication)
        result2 = await github_sync_manager.sync_github_to_linear(
            repo_owner="test-org",
            repo_name="test-repo",
            github_issue_number=42,
            linear_issue_id=sample_linear_issue["id"],
        )
        assert result2 is None  # Sync blocked due to deduplication

        # Verify deduplication manager was called multiple times
        assert github_sync_manager._dedup_manager.should_process_event.call_count >= 2

        await github_sync_manager.close()


@pytest.mark.asyncio
async def test_linear_comment_syncs_to_github(
    github_sync_manager,
    mock_github_client,
    mock_github_issue,
):
    """Test that Linear comments sync to GitHub."""
    # Setup
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()

        # Mock GitHub comment creation
        mock_comment = MagicMock()
        mock_comment.id = 789
        mock_github_issue.create_comment = MagicMock(return_value=mock_comment)

        # Sync Linear comment to GitHub
        result = await github_sync_manager.sync_linear_comment_to_github(
            github_issue=mock_github_issue,
            linear_comment_body="This is a test comment from Linear",
            linear_comment_user="Test User",
        )

        # Verify comment was created
        assert result is not None
        mock_github_issue.create_comment.assert_called_once()

        # Verify comment includes attribution
        call_args = mock_github_issue.create_comment.call_args
        comment_body = call_args.args[0]
        assert "Test User" in comment_body
        assert "Linear" in comment_body

        await github_sync_manager.close()


@pytest.mark.asyncio
async def test_github_comment_syncs_to_linear(
    github_sync_manager,
    mock_github_client,
    mock_linear_client,
    mock_github_comment,
):
    """Test that GitHub comments sync to Linear."""
    # Setup
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()

        # Mock Linear comment creation
        created_comment = {
            "id": "comment-123",
            "body": "Comment from GitHub",
        }
        mock_linear_client.add_comment.return_value = created_comment

        # Sync GitHub comment to Linear
        result = await github_sync_manager.sync_github_comment_to_linear(
            linear_issue_id="linear-123",
            github_comment=mock_github_comment,
        )

        # Verify comment was created
        assert result is not None
        mock_linear_client.add_comment.assert_called_once()

        # Verify comment includes GitHub user attribution
        call_args = mock_linear_client.add_comment.call_args
        assert "commenter" in call_args.kwargs["body"]
        assert "GitHub" in call_args.kwargs["body"]

        # Verify deduplication
        github_sync_manager._dedup_manager.should_process_event.assert_called()
        github_sync_manager._dedup_manager.mark_processed.assert_called()

        await github_sync_manager.close()


@pytest.mark.asyncio
async def test_pr_merged_status_syncs_to_linear(
    github_sync_manager,
    mock_github_client,
    mock_linear_client,
    mock_github_pr,
):
    """Test that merged PR status syncs to Linear issue."""
    # Setup
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()

        # Mock merged PR
        mock_github_pr.merged = True
        mock_github_pr.state = "closed"

        # Mock Linear comment creation
        created_comment = {
            "id": "comment-pr-123",
            "body": "PR merged notification",
        }
        mock_linear_client.add_comment.return_value = created_comment

        # Sync PR status to Linear
        result = await github_sync_manager.sync_pr_status_to_linear(
            linear_issue_id="linear-123",
            pull_request=mock_github_pr,
        )

        # Verify comment was added
        assert result is not None
        mock_linear_client.add_comment.assert_called_once()

        # Verify comment indicates merge
        call_args = mock_linear_client.add_comment.call_args
        assert "merged" in call_args.kwargs["body"].lower()
        assert mock_github_pr.html_url in call_args.kwargs["body"]

        await github_sync_manager.close()


@pytest.mark.asyncio
async def test_pr_closed_status_syncs_to_linear(
    github_sync_manager,
    mock_github_client,
    mock_linear_client,
    mock_github_pr,
):
    """Test that closed PR status (without merge) syncs to Linear."""
    # Setup
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()

        # Mock closed (not merged) PR
        mock_github_pr.merged = False
        mock_github_pr.state = "closed"

        # Mock Linear comment creation
        created_comment = {
            "id": "comment-pr-456",
            "body": "PR closed notification",
        }
        mock_linear_client.add_comment.return_value = created_comment

        # Sync PR status to Linear
        result = await github_sync_manager.sync_pr_status_to_linear(
            linear_issue_id="linear-123",
            pull_request=mock_github_pr,
        )

        # Verify comment was added
        assert result is not None
        mock_linear_client.add_comment.assert_called_once()

        # Verify comment indicates closure without merge
        call_args = mock_linear_client.add_comment.call_args
        assert "closed" in call_args.kwargs["body"].lower()

        await github_sync_manager.close()


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_github_authentication_error(
    github_sync_manager,
    mock_github_client,
):
    """Test handling of GitHub authentication errors."""
    from github import GithubException

    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        # Mock authentication failure
        mock_github_client.get_user.side_effect = GithubException(
            401, {"message": "Bad credentials"}, None
        )

        # Verify authentication error is raised
        with pytest.raises(GitHubAuthenticationError) as exc_info:
            await github_sync_manager.initialize()

        assert "authentication failed" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_github_repository_not_found(
    github_sync_manager,
    mock_github_client,
    sample_linear_issue,
):
    """Test handling of repository not found errors."""
    from github import UnknownObjectException

    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()

        # Mock repository not found
        mock_github_client.get_repo.side_effect = UnknownObjectException(
            404, {"message": "Not Found"}, None
        )

        # Verify not found error is raised
        with pytest.raises(GitHubNotFoundError) as exc_info:
            await github_sync_manager.sync_linear_to_github(
                linear_issue_id=sample_linear_issue["id"],
                repo_owner="nonexistent",
                repo_name="repo",
            )

        assert "not found" in str(exc_info.value).lower()

        await github_sync_manager.close()


@pytest.mark.asyncio
async def test_github_rate_limit_error(
    github_sync_manager,
    mock_github_client,
    sample_linear_issue,
):
    """Test handling of GitHub rate limit errors."""
    from github import RateLimitExceededException

    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()

        # Mock rate limit with retry info
        mock_rate_limit = MagicMock()
        mock_rate_limit.core.reset = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_github_client.get_rate_limit.return_value = mock_rate_limit

        # Mock rate limit exceeded
        mock_github_client.get_repo.side_effect = RateLimitExceededException(
            403, {"message": "API rate limit exceeded"}, None
        )

        # Verify rate limit error is raised
        with pytest.raises(GitHubRateLimitError) as exc_info:
            await github_sync_manager.sync_linear_to_github(
                linear_issue_id=sample_linear_issue["id"],
                repo_owner="test",
                repo_name="repo",
            )

        assert "rate limit" in str(exc_info.value).lower()
        assert exc_info.value.retry_after is not None

        await github_sync_manager.close()


@pytest.mark.asyncio
async def test_conflict_resolution_blocks_older_update(
    github_sync_manager,
    mock_github_client,
    mock_linear_client,
    sample_linear_issue,
):
    """Test that conflict resolution blocks older updates."""
    # Setup
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()

        # Mock conflict resolution to reject update (older)
        github_sync_manager._conflict_manager.should_apply_update.return_value = False

        # Attempt to sync (should be blocked)
        result = await github_sync_manager.sync_linear_to_github(
            linear_issue_id=sample_linear_issue["id"],
            repo_owner="test-org",
            repo_name="test-repo",
        )

        # Verify sync was skipped
        assert result is None

        # Verify conflict manager was consulted
        github_sync_manager._conflict_manager.should_apply_update.assert_called()

        await github_sync_manager.close()


@pytest.mark.asyncio
async def test_complete_bidirectional_flow_with_comments(
    github_sync_manager,
    mock_github_client,
    mock_linear_client,
    sample_linear_issue,
    mock_github_issue,
    mock_github_comment,
):
    """Test complete bidirectional flow: Linear → GitHub → Comments → Linear."""
    # Setup
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()

        # Step 1: Create GitHub issue from Linear
        mock_repo = mock_github_client.get_repo.return_value
        mock_repo.create_issue = MagicMock(return_value=mock_github_issue)
        mock_repo.get_issue = MagicMock(return_value=mock_github_issue)

        github_issue = await github_sync_manager.sync_linear_to_github(
            linear_issue_id=sample_linear_issue["id"],
            repo_owner="test-org",
            repo_name="test-repo",
        )
        assert github_issue is not None
        assert github_issue.number == 42

        # Step 2: Add comment on GitHub and sync to Linear
        created_linear_comment = {
            "id": "linear-comment-123",
            "body": "Comment from GitHub",
        }
        mock_linear_client.add_comment.return_value = created_linear_comment

        linear_comment = await github_sync_manager.sync_github_comment_to_linear(
            linear_issue_id=sample_linear_issue["id"],
            github_comment=mock_github_comment,
        )
        assert linear_comment is not None

        # Step 3: Add comment on Linear and sync to GitHub
        mock_github_comment_result = MagicMock()
        mock_github_comment_result.id = 999
        mock_github_issue.create_comment = MagicMock(return_value=mock_github_comment_result)

        github_comment = await github_sync_manager.sync_linear_comment_to_github(
            github_issue=github_issue,
            linear_comment_body="Reply from Linear",
            linear_comment_user="Linear User",
        )
        assert github_comment is not None

        # Verify all syncs completed
        assert mock_repo.create_issue.call_count == 1
        assert mock_linear_client.add_comment.call_count == 1
        assert mock_github_issue.create_comment.call_count == 1

        await github_sync_manager.close()


@pytest.mark.asyncio
async def test_sync_manager_context_manager(
    mock_github_config,
    mock_linear_client,
    mock_dedup_manager,
    mock_conflict_manager,
    mock_github_client,
):
    """Test GitHubSyncManager as async context manager."""
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        manager = GitHubSyncManager(
            github_config=mock_github_config,
            linear_client=mock_linear_client,
            dedup_manager=mock_dedup_manager,
            conflict_manager=mock_conflict_manager,
        )

        # Use as context manager
        async with manager as sync_mgr:
            assert sync_mgr._initialized is True
            assert sync_mgr._github_client is not None

        # Verify cleanup
        assert manager._initialized is False


@pytest.mark.asyncio
async def test_deduplication_event_id_generation(
    github_sync_manager,
    mock_github_client,
    sample_linear_issue,
):
    """Test that event IDs are properly generated for deduplication."""
    # Setup
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()

        mock_repo = mock_github_client.get_repo.return_value
        mock_repo.create_issue = MagicMock(return_value=MagicMock(number=1))

        # Sync issue
        await github_sync_manager.sync_linear_to_github(
            linear_issue_id=sample_linear_issue["id"],
            repo_owner="test-org",
            repo_name="test-repo",
        )

        # Verify event ID contains issue ID and timestamp
        call_args = github_sync_manager._dedup_manager.should_process_event.call_args
        event_id = call_args.kwargs["event_id"]

        assert "linear-to-github" in event_id
        assert sample_linear_issue["id"] in event_id
        assert sample_linear_issue["updatedAt"] in event_id

        await github_sync_manager.close()
