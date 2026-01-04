"""
Tests for GitHub Sync Manager for Linear ↔ GitHub Bidirectional Sync.

Tests cover:
- GitHubSyncManager initialization and configuration
- Linear → GitHub issue sync (create and update)
- GitHub → Linear issue sync (create and update)
- Comment synchronization (bidirectional)
- PR status synchronization
- Deduplication logic to prevent infinite loops
- Conflict resolution with last-write-wins
- Error handling (auth failures, rate limits, not found)
- Async context manager support
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

# Mock github module before importing (since PyGithub isn't installed in test environment)
github_mock = MagicMock()
GithubException = type("GithubException", (Exception,), {"status": 500})
RateLimitExceededException = type("RateLimitExceededException", (GithubException,), {})
UnknownObjectException = type("UnknownObjectException", (GithubException,), {})

github_mock.GithubException = GithubException
github_mock.RateLimitExceededException = RateLimitExceededException
github_mock.UnknownObjectException = UnknownObjectException

sys.modules["github"] = github_mock
sys.modules["github.Issue"] = MagicMock()
sys.modules["github.IssueComment"] = MagicMock()
sys.modules["github.PullRequest"] = MagicMock()
sys.modules["github.Repository"] = MagicMock()

# Now import the sync manager (after mocking github modules)
from src.integrations.linear.github_sync import (  # noqa: E402
    GitHubAuthenticationError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubSyncError,
    GitHubSyncManager,
    get_github_sync_manager,
    reset_github_sync_manager,
)

if TYPE_CHECKING:
    pass


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_github_config():
    """Create sample GitHub configuration for testing."""
    config = MagicMock()
    config.github_token = SecretStr("test-github-token-12345")
    config.github_timeout_seconds = 30
    config.github_max_retries = 3
    config.is_configured = True
    return config


@pytest.fixture
def mock_linear_client():
    """Create a mock Linear client for testing."""
    client = MagicMock()
    client.initialize = AsyncMock()
    client.close = AsyncMock()
    client.get_issue = AsyncMock()
    client.create_issue = AsyncMock()
    client.update_issue = AsyncMock()
    client.add_comment = AsyncMock()
    return client


@pytest.fixture
def mock_dedup_manager():
    """Create a mock deduplication manager."""
    manager = MagicMock()
    manager.connect = AsyncMock()
    manager.should_process_event = AsyncMock(return_value=True)
    manager.mark_processed = AsyncMock()
    manager.record_sync = AsyncMock()
    return manager


@pytest.fixture
def mock_conflict_manager():
    """Create a mock conflict resolution manager."""
    manager = MagicMock()
    manager.connect = AsyncMock()
    manager.should_apply_update = AsyncMock(return_value=True)
    manager.record_update = AsyncMock()
    return manager


@pytest.fixture
def github_sync_manager(
    sample_github_config,
    mock_linear_client,
    mock_dedup_manager,
    mock_conflict_manager,
):
    """Create a GitHub sync manager for testing."""
    return GitHubSyncManager(
        github_config=sample_github_config,
        linear_client=mock_linear_client,
        dedup_manager=mock_dedup_manager,
        conflict_manager=mock_conflict_manager,
    )


@pytest.fixture
async def initialized_sync_manager(github_sync_manager: GitHubSyncManager):
    """Create an initialized GitHub sync manager for testing."""
    with patch("src.integrations.linear.github_sync.Github") as mock_github_class:
        mock_github_instance = MagicMock()
        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_github_instance.get_user.return_value = mock_user
        mock_github_instance.close = MagicMock()
        mock_github_class.return_value = mock_github_instance

        await github_sync_manager.initialize()

        yield github_sync_manager

        await github_sync_manager.close()


@pytest.fixture
def sample_linear_issue():
    """Create sample Linear issue data."""
    return {
        "id": "linear-issue-123",
        "identifier": "LIN-42",
        "title": "Test Issue",
        "description": "This is a test issue",
        "url": "https://linear.app/test/issue/LIN-42",
        "updatedAt": "2024-01-01T00:00:00Z",
        "state": {
            "id": "state-123",
            "name": "In Progress",
            "type": "started",
        },
        "assignee": {
            "id": "user-123",
            "name": "John Doe",
        },
        "priority": 2,
        "labels": {
            "nodes": [
                {"id": "label-1", "name": "bug"},
                {"id": "label-2", "name": "urgent"},
            ]
        },
    }


@pytest.fixture
def sample_github_issue():
    """Create sample GitHub issue object."""
    issue = MagicMock()
    issue.number = 42
    issue.title = "Test GitHub Issue"
    issue.body = "This is a test GitHub issue"
    issue.html_url = "https://github.com/test/repo/issues/42"
    issue.state = "open"
    issue.updated_at = datetime.now(timezone.utc)
    issue.user = MagicMock()
    issue.user.login = "githubuser"
    issue.create_comment = MagicMock()
    issue.edit = MagicMock()
    return issue


@pytest.fixture
def sample_github_comment():
    """Create sample GitHub comment object."""
    comment = MagicMock()
    comment.id = 999
    comment.body = "This is a test comment"
    comment.user = MagicMock()
    comment.user.login = "commenter"
    comment.updated_at = datetime.now(timezone.utc)
    return comment


@pytest.fixture
def sample_github_pr():
    """Create sample GitHub pull request object."""
    pr = MagicMock()
    pr.number = 10
    pr.title = "Test PR"
    pr.html_url = "https://github.com/test/repo/pull/10"
    pr.state = "open"
    pr.merged = False
    return pr


# ============================================================================
# Initialization Tests
# ============================================================================


class TestGitHubSyncManagerInit:
    """Tests for GitHubSyncManager initialization."""

    def test_initialization(self, github_sync_manager: GitHubSyncManager):
        """Test sync manager initializes correctly."""
        assert github_sync_manager._initialized is False
        assert github_sync_manager._github_client is None
        assert github_sync_manager.linear_client is not None

    def test_initialization_uses_default_config(self):
        """Test sync manager uses default config when none provided."""
        with patch("src.integrations.linear.github_sync.get_github_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.is_configured = True
            mock_get_config.return_value = mock_config

            manager = GitHubSyncManager()

            assert manager.config == mock_config
            mock_get_config.assert_called_once()

    def test_initialization_uses_default_dedup_manager(self):
        """Test sync manager uses default dedup manager when none provided."""
        with patch("src.integrations.linear.github_sync.get_dedup_manager") as mock_get_dedup:
            mock_dedup = MagicMock()
            mock_get_dedup.return_value = mock_dedup

            manager = GitHubSyncManager()

            assert manager._dedup_manager == mock_dedup
            mock_get_dedup.assert_called_once()

    def test_initialization_uses_default_conflict_manager(self):
        """Test sync manager uses default conflict manager when none provided."""
        with patch("src.integrations.linear.github_sync.get_conflict_manager") as mock_get_conflict:
            mock_conflict = MagicMock()
            mock_get_conflict.return_value = mock_conflict

            manager = GitHubSyncManager()

            assert manager._conflict_manager == mock_conflict
            mock_get_conflict.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_raises_error_when_not_configured(self):
        """Test that initialize raises error when GitHub not configured."""
        config = MagicMock()
        config.is_configured = False

        manager = GitHubSyncManager(github_config=config)

        with pytest.raises(GitHubSyncError, match="not configured"):
            await manager.initialize()

    @pytest.mark.asyncio
    async def test_initialize_creates_github_client(self, github_sync_manager: GitHubSyncManager):
        """Test that initialize creates GitHub client with correct token."""
        with patch("src.integrations.linear.github_sync.Github") as mock_github_class:
            mock_github_instance = MagicMock()
            mock_user = MagicMock()
            mock_user.login = "testuser"
            mock_github_instance.get_user.return_value = mock_user
            mock_github_class.return_value = mock_github_instance

            await github_sync_manager.initialize()

            mock_github_class.assert_called_once()
            call_args = mock_github_class.call_args
            assert call_args[0][0] == "test-github-token-12345"
            assert call_args[1]["timeout"] == 30
            assert call_args[1]["retry"] == 3

    @pytest.mark.asyncio
    async def test_initialize_verifies_authentication(self, github_sync_manager: GitHubSyncManager):
        """Test that initialize verifies GitHub authentication."""
        with patch("src.integrations.linear.github_sync.Github") as mock_github_class:
            mock_github_instance = MagicMock()
            mock_user = MagicMock()
            mock_user.login = "testuser"
            mock_github_instance.get_user.return_value = mock_user
            mock_github_class.return_value = mock_github_instance

            await github_sync_manager.initialize()

            mock_github_instance.get_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_raises_auth_error_on_failure(
        self, github_sync_manager: GitHubSyncManager
    ):
        """Test that initialize raises GitHubAuthenticationError on auth failure."""
        with patch("src.integrations.linear.github_sync.Github") as mock_github_class:
            mock_github_instance = MagicMock()
            mock_github_instance.get_user.side_effect = GithubException("Auth failed", 401)
            mock_github_class.return_value = mock_github_instance

            with pytest.raises(GitHubAuthenticationError, match="authentication failed"):
                await github_sync_manager.initialize()

    @pytest.mark.asyncio
    async def test_initialize_connects_dedup_manager(
        self, github_sync_manager: GitHubSyncManager, mock_dedup_manager
    ):
        """Test that initialize connects deduplication manager."""
        with patch("src.integrations.linear.github_sync.Github") as mock_github_class:
            mock_github_instance = MagicMock()
            mock_user = MagicMock()
            mock_user.login = "testuser"
            mock_github_instance.get_user.return_value = mock_user
            mock_github_class.return_value = mock_github_instance

            await github_sync_manager.initialize()

            mock_dedup_manager.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_connects_conflict_manager(
        self, github_sync_manager: GitHubSyncManager, mock_conflict_manager
    ):
        """Test that initialize connects conflict resolution manager."""
        with patch("src.integrations.linear.github_sync.Github") as mock_github_class:
            mock_github_instance = MagicMock()
            mock_user = MagicMock()
            mock_user.login = "testuser"
            mock_github_instance.get_user.return_value = mock_user
            mock_github_class.return_value = mock_github_instance

            await github_sync_manager.initialize()

            mock_conflict_manager.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_sets_initialized_flag(self, github_sync_manager: GitHubSyncManager):
        """Test that initialize sets the initialized flag."""
        with patch("src.integrations.linear.github_sync.Github") as mock_github_class:
            mock_github_instance = MagicMock()
            mock_user = MagicMock()
            mock_user.login = "testuser"
            mock_github_instance.get_user.return_value = mock_user
            mock_github_class.return_value = mock_github_instance

            await github_sync_manager.initialize()

            assert github_sync_manager._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, github_sync_manager: GitHubSyncManager):
        """Test that initialize can be called multiple times safely."""
        with patch("src.integrations.linear.github_sync.Github") as mock_github_class:
            mock_github_instance = MagicMock()
            mock_user = MagicMock()
            mock_user.login = "testuser"
            mock_github_instance.get_user.return_value = mock_user
            mock_github_class.return_value = mock_github_instance

            await github_sync_manager.initialize()
            await github_sync_manager.initialize()

            # Should only be called once
            assert mock_github_class.call_count == 1

    @pytest.mark.asyncio
    async def test_close_cleans_up_resources(self, initialized_sync_manager: GitHubSyncManager):
        """Test that close properly cleans up resources."""
        assert initialized_sync_manager._initialized is False
        assert initialized_sync_manager._github_client is None

    @pytest.mark.asyncio
    async def test_context_manager_support(self, github_sync_manager: GitHubSyncManager):
        """Test that sync manager works as async context manager."""
        with patch("src.integrations.linear.github_sync.Github") as mock_github_class:
            mock_github_instance = MagicMock()
            mock_user = MagicMock()
            mock_user.login = "testuser"
            mock_github_instance.get_user.return_value = mock_user
            mock_github_instance.close = MagicMock()
            mock_github_class.return_value = mock_github_instance

            async with github_sync_manager as manager:
                assert manager._initialized is True

            assert github_sync_manager._initialized is False


# ============================================================================
# Linear → GitHub Sync Tests
# ============================================================================


class TestLinearToGitHubSync:
    """Tests for Linear → GitHub issue synchronization."""

    @pytest.mark.asyncio
    async def test_sync_linear_to_github_requires_initialization(
        self, github_sync_manager: GitHubSyncManager
    ):
        """Test that syncing requires initialization."""
        with pytest.raises(GitHubSyncError, match="not initialized"):
            await github_sync_manager.sync_linear_to_github(
                linear_issue_id="issue-123",
                repo_owner="test",
                repo_name="repo",
            )

    @pytest.mark.asyncio
    async def test_sync_linear_to_github_creates_new_issue(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_linear_client,
        sample_linear_issue,
    ):
        """Test syncing Linear issue creates new GitHub issue."""
        # Setup mocks
        mock_linear_client.get_issue.return_value = sample_linear_issue

        mock_repo = MagicMock()
        mock_github_issue = MagicMock()
        mock_github_issue.number = 42
        mock_repo.create_issue.return_value = mock_github_issue

        with patch.object(initialized_sync_manager, "_get_github_repo", return_value=mock_repo):
            result = await initialized_sync_manager.sync_linear_to_github(
                linear_issue_id="linear-issue-123",
                repo_owner="test",
                repo_name="repo",
            )

            assert result == mock_github_issue
            mock_linear_client.get_issue.assert_called_once_with("linear-issue-123")
            mock_repo.create_issue.assert_called_once()

            # Verify issue creation args
            call_args = mock_repo.create_issue.call_args
            assert call_args[1]["title"] == "Test Issue"
            assert "linear-sync" in call_args[1]["labels"]

    @pytest.mark.asyncio
    async def test_sync_linear_to_github_updates_existing_issue(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_linear_client,
        sample_linear_issue,
    ):
        """Test syncing Linear issue updates existing GitHub issue."""
        # Setup mocks
        mock_linear_client.get_issue.return_value = sample_linear_issue

        mock_repo = MagicMock()
        mock_github_issue = MagicMock()
        mock_github_issue.number = 42
        mock_github_issue.state = "open"
        mock_repo.get_issue.return_value = mock_github_issue

        with patch.object(initialized_sync_manager, "_get_github_repo", return_value=mock_repo):
            result = await initialized_sync_manager.sync_linear_to_github(
                linear_issue_id="linear-issue-123",
                repo_owner="test",
                repo_name="repo",
                github_issue_number=42,
            )

            assert result == mock_github_issue
            mock_repo.get_issue.assert_called_once_with(42)
            mock_github_issue.edit.assert_called()

    @pytest.mark.asyncio
    async def test_sync_linear_to_github_respects_deduplication(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_linear_client,
        mock_dedup_manager,
        sample_linear_issue,
    ):
        """Test that sync respects deduplication logic."""
        mock_linear_client.get_issue.return_value = sample_linear_issue
        mock_dedup_manager.should_process_event.return_value = False

        result = await initialized_sync_manager.sync_linear_to_github(
            linear_issue_id="linear-issue-123",
            repo_owner="test",
            repo_name="repo",
        )

        assert result is None
        mock_dedup_manager.should_process_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_linear_to_github_respects_conflict_resolution(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_linear_client,
        mock_conflict_manager,
        sample_linear_issue,
    ):
        """Test that sync respects conflict resolution logic."""
        mock_linear_client.get_issue.return_value = sample_linear_issue
        mock_conflict_manager.should_apply_update.return_value = False

        result = await initialized_sync_manager.sync_linear_to_github(
            linear_issue_id="linear-issue-123",
            repo_owner="test",
            repo_name="repo",
        )

        assert result is None
        mock_conflict_manager.should_apply_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_linear_to_github_marks_event_processed(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_linear_client,
        mock_dedup_manager,
        sample_linear_issue,
    ):
        """Test that sync marks event as processed."""
        mock_linear_client.get_issue.return_value = sample_linear_issue

        mock_repo = MagicMock()
        mock_github_issue = MagicMock()
        mock_github_issue.number = 42
        mock_repo.create_issue.return_value = mock_github_issue

        with patch.object(initialized_sync_manager, "_get_github_repo", return_value=mock_repo):
            await initialized_sync_manager.sync_linear_to_github(
                linear_issue_id="linear-issue-123",
                repo_owner="test",
                repo_name="repo",
            )

            mock_dedup_manager.mark_processed.assert_called_once()
            mock_dedup_manager.record_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_linear_to_github_records_conflict_update(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_linear_client,
        mock_conflict_manager,
        sample_linear_issue,
    ):
        """Test that sync records update for conflict resolution."""
        mock_linear_client.get_issue.return_value = sample_linear_issue

        mock_repo = MagicMock()
        mock_github_issue = MagicMock()
        mock_github_issue.number = 42
        mock_repo.create_issue.return_value = mock_github_issue

        with patch.object(initialized_sync_manager, "_get_github_repo", return_value=mock_repo):
            await initialized_sync_manager.sync_linear_to_github(
                linear_issue_id="linear-issue-123",
                repo_owner="test",
                repo_name="repo",
            )

            mock_conflict_manager.record_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_linear_to_github_closes_completed_issues(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_linear_client,
        sample_linear_issue,
    ):
        """Test that completed Linear issues close GitHub issues."""
        # Mark Linear issue as completed
        completed_issue = sample_linear_issue.copy()
        completed_issue["state"] = {
            "id": "state-completed",
            "name": "Done",
            "type": "completed",
        }
        mock_linear_client.get_issue.return_value = completed_issue

        mock_repo = MagicMock()
        mock_github_issue = MagicMock()
        mock_github_issue.number = 42
        mock_github_issue.state = "open"
        mock_repo.get_issue.return_value = mock_github_issue

        with patch.object(initialized_sync_manager, "_get_github_repo", return_value=mock_repo):
            await initialized_sync_manager.sync_linear_to_github(
                linear_issue_id="linear-issue-123",
                repo_owner="test",
                repo_name="repo",
                github_issue_number=42,
            )

            # Verify issue was closed
            mock_github_issue.edit.assert_any_call(state="closed")

    @pytest.mark.asyncio
    async def test_sync_linear_to_github_handles_not_found_error(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_linear_client,
        sample_linear_issue,
    ):
        """Test that sync handles GitHub repository not found error."""
        mock_linear_client.get_issue.return_value = sample_linear_issue

        with patch.object(
            initialized_sync_manager,
            "_get_github_repo",
            side_effect=GitHubNotFoundError("Repository not found"),
        ):
            with pytest.raises(GitHubNotFoundError, match="not found"):
                await initialized_sync_manager.sync_linear_to_github(
                    linear_issue_id="linear-issue-123",
                    repo_owner="test",
                    repo_name="repo",
                )


# ============================================================================
# GitHub → Linear Sync Tests
# ============================================================================


class TestGitHubToLinearSync:
    """Tests for GitHub → Linear issue synchronization."""

    @pytest.mark.asyncio
    async def test_sync_github_to_linear_requires_initialization(
        self, github_sync_manager: GitHubSyncManager
    ):
        """Test that syncing requires initialization."""
        with pytest.raises(GitHubSyncError, match="not initialized"):
            await github_sync_manager.sync_github_to_linear(
                repo_owner="test",
                repo_name="repo",
                github_issue_number=42,
            )

    @pytest.mark.asyncio
    async def test_sync_github_to_linear_creates_new_issue(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_linear_client,
        sample_github_issue,
    ):
        """Test syncing GitHub issue creates new Linear issue."""
        # Setup mocks
        mock_linear_issue = {
            "id": "linear-123",
            "identifier": "LIN-1",
            "title": "[GitHub] Test GitHub Issue",
        }
        mock_linear_client.create_issue.return_value = mock_linear_issue

        mock_repo = MagicMock()
        mock_repo.get_issue.return_value = sample_github_issue

        with patch.object(initialized_sync_manager, "_get_github_repo", return_value=mock_repo):
            result = await initialized_sync_manager.sync_github_to_linear(
                repo_owner="test",
                repo_name="repo",
                github_issue_number=42,
            )

            assert result == mock_linear_issue
            mock_linear_client.create_issue.assert_called_once()

            # Verify issue creation args
            call_args = mock_linear_client.create_issue.call_args
            assert "[GitHub]" in call_args[1]["title"]
            assert "github.com" in call_args[1]["description"]

    @pytest.mark.asyncio
    async def test_sync_github_to_linear_updates_existing_issue(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_linear_client,
        sample_github_issue,
    ):
        """Test syncing GitHub issue updates existing Linear issue."""
        # Setup mocks
        mock_linear_issue = {
            "id": "linear-123",
            "identifier": "LIN-1",
            "title": "[GitHub] Test GitHub Issue",
        }
        mock_linear_client.update_issue.return_value = mock_linear_issue

        mock_repo = MagicMock()
        mock_repo.get_issue.return_value = sample_github_issue

        with patch.object(initialized_sync_manager, "_get_github_repo", return_value=mock_repo):
            result = await initialized_sync_manager.sync_github_to_linear(
                repo_owner="test",
                repo_name="repo",
                github_issue_number=42,
                linear_issue_id="linear-123",
            )

            assert result == mock_linear_issue
            mock_linear_client.update_issue.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_github_to_linear_respects_deduplication(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_dedup_manager,
        sample_github_issue,
    ):
        """Test that sync respects deduplication logic."""
        mock_dedup_manager.should_process_event.return_value = False

        mock_repo = MagicMock()
        mock_repo.get_issue.return_value = sample_github_issue

        with patch.object(initialized_sync_manager, "_get_github_repo", return_value=mock_repo):
            result = await initialized_sync_manager.sync_github_to_linear(
                repo_owner="test",
                repo_name="repo",
                github_issue_number=42,
            )

            assert result is None
            mock_dedup_manager.should_process_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_github_to_linear_marks_event_processed(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_linear_client,
        mock_dedup_manager,
        sample_github_issue,
    ):
        """Test that sync marks event as processed."""
        mock_linear_issue = {
            "id": "linear-123",
            "identifier": "LIN-1",
            "title": "[GitHub] Test",
        }
        mock_linear_client.create_issue.return_value = mock_linear_issue

        mock_repo = MagicMock()
        mock_repo.get_issue.return_value = sample_github_issue

        with patch.object(initialized_sync_manager, "_get_github_repo", return_value=mock_repo):
            await initialized_sync_manager.sync_github_to_linear(
                repo_owner="test",
                repo_name="repo",
                github_issue_number=42,
            )

            mock_dedup_manager.mark_processed.assert_called_once()
            mock_dedup_manager.record_sync.assert_called_once()


# ============================================================================
# Comment Sync Tests
# ============================================================================


class TestCommentSync:
    """Tests for comment synchronization."""

    @pytest.mark.asyncio
    async def test_sync_github_comment_to_linear(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_linear_client,
        sample_github_comment,
    ):
        """Test syncing GitHub comment to Linear."""
        mock_linear_comment = {
            "id": "comment-123",
            "body": "**commenter** commented on GitHub:\n\nThis is a test comment",
        }
        mock_linear_client.add_comment.return_value = mock_linear_comment

        result = await initialized_sync_manager.sync_github_comment_to_linear(
            linear_issue_id="linear-123",
            github_comment=sample_github_comment,
        )

        assert result == mock_linear_comment
        mock_linear_client.add_comment.assert_called_once()

        # Verify comment attribution
        call_args = mock_linear_client.add_comment.call_args
        assert "commenter" in call_args[1]["body"]
        assert "GitHub" in call_args[1]["body"]

    @pytest.mark.asyncio
    async def test_sync_github_comment_respects_deduplication(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_dedup_manager,
        sample_github_comment,
    ):
        """Test that comment sync respects deduplication."""
        mock_dedup_manager.should_process_event.return_value = False

        result = await initialized_sync_manager.sync_github_comment_to_linear(
            linear_issue_id="linear-123",
            github_comment=sample_github_comment,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_sync_linear_comment_to_github(
        self,
        initialized_sync_manager: GitHubSyncManager,
        sample_github_issue,
    ):
        """Test syncing Linear comment to GitHub."""
        mock_github_comment = MagicMock()
        sample_github_issue.create_comment.return_value = mock_github_comment

        result = await initialized_sync_manager.sync_linear_comment_to_github(
            github_issue=sample_github_issue,
            linear_comment_body="Test comment from Linear",
            linear_comment_user="Linear User",
        )

        assert result == mock_github_comment
        sample_github_issue.create_comment.assert_called_once()

        # Verify comment attribution
        call_args = sample_github_issue.create_comment.call_args
        assert "Linear User" in call_args[0][0]
        assert "Linear" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_sync_linear_comment_without_user(
        self,
        initialized_sync_manager: GitHubSyncManager,
        sample_github_issue,
    ):
        """Test syncing Linear comment without user attribution."""
        mock_github_comment = MagicMock()
        sample_github_issue.create_comment.return_value = mock_github_comment

        result = await initialized_sync_manager.sync_linear_comment_to_github(
            github_issue=sample_github_issue,
            linear_comment_body="Test comment",
        )

        assert result is not None
        call_args = sample_github_issue.create_comment.call_args
        assert "Comment from Linear" in call_args[0][0]


# ============================================================================
# PR Status Sync Tests
# ============================================================================


class TestPRStatusSync:
    """Tests for PR status synchronization."""

    @pytest.mark.asyncio
    async def test_sync_merged_pr_to_linear(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_linear_client,
        sample_github_pr,
    ):
        """Test syncing merged PR status to Linear."""
        sample_github_pr.merged = True
        mock_comment = {"id": "comment-123", "body": "PR merged"}
        mock_linear_client.add_comment.return_value = mock_comment

        result = await initialized_sync_manager.sync_pr_status_to_linear(
            linear_issue_id="linear-123",
            pull_request=sample_github_pr,
        )

        assert result is not None
        mock_linear_client.add_comment.assert_called_once()

        # Verify comment mentions merge
        call_args = mock_linear_client.add_comment.call_args
        assert "merged" in call_args[1]["body"].lower()

    @pytest.mark.asyncio
    async def test_sync_closed_pr_to_linear(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_linear_client,
        sample_github_pr,
    ):
        """Test syncing closed (not merged) PR to Linear."""
        sample_github_pr.state = "closed"
        sample_github_pr.merged = False
        mock_comment = {"id": "comment-123", "body": "PR closed"}
        mock_linear_client.add_comment.return_value = mock_comment

        result = await initialized_sync_manager.sync_pr_status_to_linear(
            linear_issue_id="linear-123",
            pull_request=sample_github_pr,
        )

        assert result is not None
        mock_linear_client.add_comment.assert_called_once()

        # Verify comment mentions closed
        call_args = mock_linear_client.add_comment.call_args
        assert "closed" in call_args[1]["body"].lower()

    @pytest.mark.asyncio
    async def test_sync_open_pr_to_linear(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_linear_client,
        sample_github_pr,
    ):
        """Test syncing open PR to Linear."""
        sample_github_pr.state = "open"
        mock_comment = {"id": "comment-123", "body": "PR opened"}
        mock_linear_client.add_comment.return_value = mock_comment

        result = await initialized_sync_manager.sync_pr_status_to_linear(
            linear_issue_id="linear-123",
            pull_request=sample_github_pr,
        )

        assert result is not None
        mock_linear_client.add_comment.assert_called_once()

        # Verify comment mentions opened
        call_args = mock_linear_client.add_comment.call_args
        assert "opened" in call_args[1]["body"].lower()


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_get_repo_handles_not_found(self, initialized_sync_manager: GitHubSyncManager):
        """Test that getting a repo handles not found error."""
        initialized_sync_manager._github_client.get_repo.side_effect = UnknownObjectException(
            404, {"message": "Not Found"}
        )

        with pytest.raises(GitHubNotFoundError, match="not found"):
            initialized_sync_manager._get_github_repo("test", "nonexistent")

    @pytest.mark.asyncio
    async def test_get_repo_handles_rate_limit(self, initialized_sync_manager: GitHubSyncManager):
        """Test that getting a repo handles rate limit error."""
        # Mock rate limit
        rate_limit = MagicMock()
        rate_limit.core = MagicMock()
        rate_limit.core.reset = datetime.now(timezone.utc)
        initialized_sync_manager._github_client.get_rate_limit.return_value = rate_limit

        initialized_sync_manager._github_client.get_repo.side_effect = RateLimitExceededException(
            429, {"message": "Rate limit exceeded"}
        )

        with pytest.raises(GitHubRateLimitError, match="rate limit exceeded"):
            initialized_sync_manager._get_github_repo("test", "repo")

    @pytest.mark.asyncio
    async def test_sync_handles_linear_client_error(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_linear_client,
    ):
        """Test that sync handles Linear client errors."""
        from src.integrations.linear.client import LinearClientError

        mock_linear_client.get_issue.side_effect = LinearClientError("Linear API error")

        with pytest.raises(LinearClientError):
            await initialized_sync_manager.sync_linear_to_github(
                linear_issue_id="linear-123",
                repo_owner="test",
                repo_name="repo",
            )

    @pytest.mark.asyncio
    async def test_sync_handles_github_exception(
        self,
        initialized_sync_manager: GitHubSyncManager,
        mock_linear_client,
        sample_linear_issue,
    ):
        """Test that sync handles GitHub exceptions."""
        mock_linear_client.get_issue.return_value = sample_linear_issue

        with patch.object(
            initialized_sync_manager,
            "_get_github_repo",
            side_effect=GithubException(500, {"message": "Server error"}),
        ):
            with pytest.raises(GitHubSyncError):
                await initialized_sync_manager.sync_linear_to_github(
                    linear_issue_id="linear-123",
                    repo_owner="test",
                    repo_name="repo",
                )


# ============================================================================
# Singleton Tests
# ============================================================================


class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_github_sync_manager_returns_singleton(self):
        """Test that get_github_sync_manager returns the same instance."""
        reset_github_sync_manager()

        manager1 = get_github_sync_manager()
        manager2 = get_github_sync_manager()

        assert manager1 is manager2

    def test_reset_github_sync_manager(self):
        """Test that reset_github_sync_manager resets the singleton."""
        manager1 = get_github_sync_manager()
        reset_github_sync_manager()
        manager2 = get_github_sync_manager()

        assert manager1 is not manager2
