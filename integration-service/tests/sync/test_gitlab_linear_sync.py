"""
Tests for GitLab Sync Manager for Linear ↔ GitLab Bidirectional Sync.

Tests cover:
- GitLabSyncManager initialization and configuration
- Linear → GitLab issue sync (create and update)
- GitLab → Linear issue sync (create and update)
- Comment synchronization (bidirectional)
- MR status synchronization
- Deduplication logic to prevent infinite loops
- Conflict resolution with last-write-wins
- Error handling (auth failures, rate limits, not found)
- Async context manager support
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

# Mock gitlab module before importing (since python-gitlab isn't installed in test environment)
gitlab_mock = MagicMock()
GitlabError = type("GitlabError", (Exception,), {"response_code": 500, "response_headers": {}})
GitlabAuthError = type("GitlabAuthenticationError", (GitlabError,), {})
GitlabGetError = type(
    "GitlabGetError", (GitlabError,), {"response_code": 500, "response_headers": {}}
)

gitlab_mock.GitlabError = GitlabError
gitlab_mock.exceptions = MagicMock()
gitlab_mock.exceptions.GitlabAuthenticationError = GitlabAuthError
gitlab_mock.exceptions.GitlabError = GitlabError
gitlab_mock.exceptions.GitlabGetError = GitlabGetError

sys.modules["gitlab"] = gitlab_mock
sys.modules["gitlab.exceptions"] = gitlab_mock.exceptions
sys.modules["gitlab.v4"] = MagicMock()
sys.modules["gitlab.v4.objects"] = MagicMock()

# Now import the sync manager (after mocking gitlab modules)
from src.integrations.linear.gitlab_sync import (  # noqa: E402
    GitLabAuthenticationError,
    GitLabNotFoundError,
    GitLabRateLimitError,
    GitLabSyncError,
    GitLabSyncManager,
    get_gitlab_sync_manager,
    reset_gitlab_sync_manager,
)

if TYPE_CHECKING:
    pass


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_gitlab_config():
    """Create sample GitLab configuration for testing."""
    config = MagicMock()
    config.gitlab_token = SecretStr("test-gitlab-token-12345")
    config.gitlab_url = "https://gitlab.example.com"
    config.gitlab_timeout_seconds = 30
    config.gitlab_max_retries = 3
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
def gitlab_sync_manager(
    sample_gitlab_config,
    mock_linear_client,
    mock_dedup_manager,
    mock_conflict_manager,
):
    """Create a GitLab sync manager for testing."""
    return GitLabSyncManager(
        gitlab_config=sample_gitlab_config,
        linear_client=mock_linear_client,
        dedup_manager=mock_dedup_manager,
        conflict_manager=mock_conflict_manager,
    )


@pytest.fixture
async def initialized_sync_manager(gitlab_sync_manager: GitLabSyncManager):
    """Create an initialized GitLab sync manager for testing."""
    with patch("src.integrations.linear.gitlab_sync.gitlab.Gitlab") as mock_gitlab_class:
        mock_gitlab_instance = MagicMock()
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_gitlab_instance.user = mock_user
        mock_gitlab_instance.auth = MagicMock()
        mock_gitlab_class.return_value = mock_gitlab_instance

        await gitlab_sync_manager.initialize()

        yield gitlab_sync_manager

        await gitlab_sync_manager.close()


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
def sample_gitlab_issue():
    """Create sample GitLab issue object."""
    issue = MagicMock()
    issue.iid = 42
    issue.title = "Test GitLab Issue"
    issue.description = "This is a test GitLab issue"
    issue.web_url = "https://gitlab.example.com/test/repo/-/issues/42"
    issue.state = "opened"
    issue.updated_at = "2024-01-01T00:00:00Z"
    issue.notes = MagicMock()
    issue.notes.create = MagicMock()
    issue.save = MagicMock()
    return issue


@pytest.fixture
def sample_gitlab_comment():
    """Create sample GitLab comment object."""
    comment = MagicMock()
    comment.id = 999
    comment.body = "This is a test comment"
    comment.author = MagicMock()
    comment.author.username = "commenter"
    comment.updated_at = "2024-01-01T00:00:00Z"
    return comment


@pytest.fixture
def sample_gitlab_mr():
    """Create sample GitLab merge request object."""
    mr = MagicMock()
    mr.iid = 10
    mr.title = "Test MR"
    mr.web_url = "https://gitlab.example.com/test/repo/-/merge_requests/10"
    mr.state = "opened"
    mr.merged = False
    return mr


# ============================================================================
# Initialization Tests
# ============================================================================


class TestGitLabSyncManagerInit:
    """Tests for GitLabSyncManager initialization."""

    def test_initialization(self, gitlab_sync_manager: GitLabSyncManager):
        """Test sync manager initializes correctly."""
        assert gitlab_sync_manager._initialized is False
        assert gitlab_sync_manager._gitlab_client is None
        assert gitlab_sync_manager.linear_client is not None

    def test_initialization_uses_default_config(self):
        """Test sync manager uses default config when none provided."""
        with patch("src.integrations.linear.gitlab_sync.get_gitlab_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.is_configured = True
            mock_get_config.return_value = mock_config

            manager = GitLabSyncManager()

            assert manager.config == mock_config
            mock_get_config.assert_called_once()

    def test_initialization_uses_default_dedup_manager(self):
        """Test sync manager uses default dedup manager when none provided."""
        with patch("src.integrations.linear.gitlab_sync.get_dedup_manager") as mock_get_dedup:
            mock_dedup = MagicMock()
            mock_get_dedup.return_value = mock_dedup

            manager = GitLabSyncManager()

            assert manager._dedup_manager == mock_dedup
            mock_get_dedup.assert_called_once()

    def test_initialization_uses_default_conflict_manager(self):
        """Test sync manager uses default conflict manager when none provided."""
        with patch("src.integrations.linear.gitlab_sync.get_conflict_manager") as mock_get_conflict:
            mock_conflict = MagicMock()
            mock_get_conflict.return_value = mock_conflict

            manager = GitLabSyncManager()

            assert manager._conflict_manager == mock_conflict
            mock_get_conflict.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_raises_error_when_not_configured(self):
        """Test that initialize raises error when GitLab not configured."""
        config = MagicMock()
        config.is_configured = False

        manager = GitLabSyncManager(gitlab_config=config)

        with pytest.raises(GitLabSyncError, match="not configured"):
            await manager.initialize()

    @pytest.mark.asyncio
    async def test_initialize_creates_gitlab_client(self, gitlab_sync_manager: GitLabSyncManager):
        """Test that initialize creates GitLab client with correct token."""
        with patch("src.integrations.linear.gitlab_sync.gitlab.Gitlab") as mock_gitlab_class:
            mock_gitlab_instance = MagicMock()
            mock_user = MagicMock()
            mock_user.username = "testuser"
            mock_gitlab_instance.user = mock_user
            mock_gitlab_instance.auth = MagicMock()
            mock_gitlab_class.return_value = mock_gitlab_instance

            await gitlab_sync_manager.initialize()

            mock_gitlab_class.assert_called_once()
            call_args = mock_gitlab_class.call_args
            assert call_args[0][0] == "https://gitlab.example.com"
            assert call_args[1]["private_token"] == "test-gitlab-token-12345"
            assert call_args[1]["timeout"] == 30
            assert call_args[1]["retry_transient_errors"] is True

    @pytest.mark.asyncio
    async def test_initialize_verifies_authentication(self, gitlab_sync_manager: GitLabSyncManager):
        """Test that initialize verifies GitLab authentication."""
        with patch("src.integrations.linear.gitlab_sync.gitlab.Gitlab") as mock_gitlab_class:
            mock_gitlab_instance = MagicMock()
            mock_user = MagicMock()
            mock_user.username = "testuser"
            mock_gitlab_instance.user = mock_user
            mock_gitlab_instance.auth = MagicMock()
            mock_gitlab_class.return_value = mock_gitlab_instance

            await gitlab_sync_manager.initialize()

            mock_gitlab_instance.auth.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_raises_auth_error_on_failure(
        self, gitlab_sync_manager: GitLabSyncManager
    ):
        """Test that initialize raises GitLabAuthenticationError on auth failure."""
        with patch("src.integrations.linear.gitlab_sync.gitlab.Gitlab") as mock_gitlab_class:
            mock_gitlab_instance = MagicMock()
            mock_gitlab_instance.auth.side_effect = GitlabAuthError("Auth failed")
            mock_gitlab_class.return_value = mock_gitlab_instance

            with pytest.raises(GitLabAuthenticationError, match="authentication failed"):
                await gitlab_sync_manager.initialize()

    @pytest.mark.asyncio
    async def test_initialize_connects_dedup_manager(
        self, gitlab_sync_manager: GitLabSyncManager, mock_dedup_manager
    ):
        """Test that initialize connects deduplication manager."""
        with patch("src.integrations.linear.gitlab_sync.gitlab.Gitlab") as mock_gitlab_class:
            mock_gitlab_instance = MagicMock()
            mock_user = MagicMock()
            mock_user.username = "testuser"
            mock_gitlab_instance.user = mock_user
            mock_gitlab_instance.auth = MagicMock()
            mock_gitlab_class.return_value = mock_gitlab_instance

            await gitlab_sync_manager.initialize()

            mock_dedup_manager.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_connects_conflict_manager(
        self, gitlab_sync_manager: GitLabSyncManager, mock_conflict_manager
    ):
        """Test that initialize connects conflict resolution manager."""
        with patch("src.integrations.linear.gitlab_sync.gitlab.Gitlab") as mock_gitlab_class:
            mock_gitlab_instance = MagicMock()
            mock_user = MagicMock()
            mock_user.username = "testuser"
            mock_gitlab_instance.user = mock_user
            mock_gitlab_instance.auth = MagicMock()
            mock_gitlab_class.return_value = mock_gitlab_instance

            await gitlab_sync_manager.initialize()

            mock_conflict_manager.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_sets_initialized_flag(self, gitlab_sync_manager: GitLabSyncManager):
        """Test that initialize sets the initialized flag."""
        with patch("src.integrations.linear.gitlab_sync.gitlab.Gitlab") as mock_gitlab_class:
            mock_gitlab_instance = MagicMock()
            mock_user = MagicMock()
            mock_user.username = "testuser"
            mock_gitlab_instance.user = mock_user
            mock_gitlab_instance.auth = MagicMock()
            mock_gitlab_class.return_value = mock_gitlab_instance

            await gitlab_sync_manager.initialize()

            assert gitlab_sync_manager._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, gitlab_sync_manager: GitLabSyncManager):
        """Test that initialize can be called multiple times safely."""
        with patch("src.integrations.linear.gitlab_sync.gitlab.Gitlab") as mock_gitlab_class:
            mock_gitlab_instance = MagicMock()
            mock_user = MagicMock()
            mock_user.username = "testuser"
            mock_gitlab_instance.user = mock_user
            mock_gitlab_instance.auth = MagicMock()
            mock_gitlab_class.return_value = mock_gitlab_instance

            await gitlab_sync_manager.initialize()
            await gitlab_sync_manager.initialize()

            # Should only be called once
            assert mock_gitlab_class.call_count == 1

    @pytest.mark.asyncio
    async def test_close_cleans_up_resources(self, initialized_sync_manager: GitLabSyncManager):
        """Test that close properly cleans up resources."""
        assert initialized_sync_manager._initialized is False
        assert initialized_sync_manager._gitlab_client is None

    @pytest.mark.asyncio
    async def test_context_manager_support(self, gitlab_sync_manager: GitLabSyncManager):
        """Test that sync manager works as async context manager."""
        with patch("src.integrations.linear.gitlab_sync.gitlab.Gitlab") as mock_gitlab_class:
            mock_gitlab_instance = MagicMock()
            mock_user = MagicMock()
            mock_user.username = "testuser"
            mock_gitlab_instance.user = mock_user
            mock_gitlab_instance.auth = MagicMock()
            mock_gitlab_class.return_value = mock_gitlab_instance

            async with gitlab_sync_manager as manager:
                assert manager._initialized is True

            assert gitlab_sync_manager._initialized is False


# ============================================================================
# Linear → GitLab Sync Tests
# ============================================================================


class TestLinearToGitLabSync:
    """Tests for Linear → GitLab issue synchronization."""

    @pytest.mark.asyncio
    async def test_sync_linear_to_gitlab_requires_initialization(
        self, gitlab_sync_manager: GitLabSyncManager
    ):
        """Test that syncing requires initialization."""
        with pytest.raises(GitLabSyncError, match="not initialized"):
            await gitlab_sync_manager.sync_linear_to_gitlab(
                linear_issue_id="issue-123",
                project_id="test/repo",
            )

    @pytest.mark.asyncio
    async def test_sync_linear_to_gitlab_creates_new_issue(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_linear_client,
        sample_linear_issue,
    ):
        """Test syncing Linear issue creates new GitLab issue."""
        # Setup mocks
        mock_linear_client.get_issue.return_value = sample_linear_issue

        mock_project = MagicMock()
        mock_gitlab_issue = MagicMock()
        mock_gitlab_issue.iid = 42
        mock_project.issues = MagicMock()
        mock_project.issues.create = MagicMock(return_value=mock_gitlab_issue)

        with patch.object(
            initialized_sync_manager, "_get_gitlab_project", return_value=mock_project
        ):
            result = await initialized_sync_manager.sync_linear_to_gitlab(
                linear_issue_id="linear-issue-123",
                project_id="test/repo",
            )

            assert result == mock_gitlab_issue
            mock_linear_client.get_issue.assert_called_once_with("linear-issue-123")
            mock_project.issues.create.assert_called_once()

            # Verify issue creation args
            call_args = mock_project.issues.create.call_args
            assert call_args[0][0]["title"] == "Test Issue"
            assert "linear-sync" in call_args[0][0]["labels"]

    @pytest.mark.asyncio
    async def test_sync_linear_to_gitlab_updates_existing_issue(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_linear_client,
        sample_linear_issue,
    ):
        """Test syncing Linear issue updates existing GitLab issue."""
        # Setup mocks
        mock_linear_client.get_issue.return_value = sample_linear_issue

        mock_project = MagicMock()
        mock_gitlab_issue = MagicMock()
        mock_gitlab_issue.iid = 42
        mock_gitlab_issue.state = "opened"
        mock_project.issues = MagicMock()
        mock_project.issues.get = MagicMock(return_value=mock_gitlab_issue)

        with patch.object(
            initialized_sync_manager, "_get_gitlab_project", return_value=mock_project
        ):
            result = await initialized_sync_manager.sync_linear_to_gitlab(
                linear_issue_id="linear-issue-123",
                project_id="test/repo",
                gitlab_issue_iid=42,
            )

            assert result == mock_gitlab_issue
            mock_project.issues.get.assert_called_once_with(42)
            mock_gitlab_issue.save.assert_called()

    @pytest.mark.asyncio
    async def test_sync_linear_to_gitlab_respects_deduplication(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_linear_client,
        mock_dedup_manager,
        sample_linear_issue,
    ):
        """Test that sync respects deduplication logic."""
        mock_linear_client.get_issue.return_value = sample_linear_issue
        mock_dedup_manager.should_process_event.return_value = False

        result = await initialized_sync_manager.sync_linear_to_gitlab(
            linear_issue_id="linear-issue-123",
            project_id="test/repo",
        )

        assert result is None
        mock_dedup_manager.should_process_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_linear_to_gitlab_respects_conflict_resolution(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_linear_client,
        mock_conflict_manager,
        sample_linear_issue,
    ):
        """Test that sync respects conflict resolution logic."""
        mock_linear_client.get_issue.return_value = sample_linear_issue
        mock_conflict_manager.should_apply_update.return_value = False

        result = await initialized_sync_manager.sync_linear_to_gitlab(
            linear_issue_id="linear-issue-123",
            project_id="test/repo",
        )

        assert result is None
        mock_conflict_manager.should_apply_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_linear_to_gitlab_marks_event_processed(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_linear_client,
        mock_dedup_manager,
        sample_linear_issue,
    ):
        """Test that sync marks event as processed."""
        mock_linear_client.get_issue.return_value = sample_linear_issue

        mock_project = MagicMock()
        mock_gitlab_issue = MagicMock()
        mock_gitlab_issue.iid = 42
        mock_project.issues = MagicMock()
        mock_project.issues.create = MagicMock(return_value=mock_gitlab_issue)

        with patch.object(
            initialized_sync_manager, "_get_gitlab_project", return_value=mock_project
        ):
            await initialized_sync_manager.sync_linear_to_gitlab(
                linear_issue_id="linear-issue-123",
                project_id="test/repo",
            )

            mock_dedup_manager.mark_processed.assert_called_once()
            mock_dedup_manager.record_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_linear_to_gitlab_records_conflict_update(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_linear_client,
        mock_conflict_manager,
        sample_linear_issue,
    ):
        """Test that sync records update for conflict resolution."""
        mock_linear_client.get_issue.return_value = sample_linear_issue

        mock_project = MagicMock()
        mock_gitlab_issue = MagicMock()
        mock_gitlab_issue.iid = 42
        mock_project.issues = MagicMock()
        mock_project.issues.create = MagicMock(return_value=mock_gitlab_issue)

        with patch.object(
            initialized_sync_manager, "_get_gitlab_project", return_value=mock_project
        ):
            await initialized_sync_manager.sync_linear_to_gitlab(
                linear_issue_id="linear-issue-123",
                project_id="test/repo",
            )

            mock_conflict_manager.record_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_linear_to_gitlab_closes_completed_issues(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_linear_client,
        sample_linear_issue,
    ):
        """Test that completed Linear issues close GitLab issues."""
        # Mark Linear issue as completed
        completed_issue = sample_linear_issue.copy()
        completed_issue["state"] = {
            "id": "state-completed",
            "name": "Done",
            "type": "completed",
        }
        mock_linear_client.get_issue.return_value = completed_issue

        mock_project = MagicMock()
        mock_gitlab_issue = MagicMock()
        mock_gitlab_issue.iid = 42
        mock_gitlab_issue.state = "opened"
        mock_project.issues = MagicMock()
        mock_project.issues.get = MagicMock(return_value=mock_gitlab_issue)

        with patch.object(
            initialized_sync_manager, "_get_gitlab_project", return_value=mock_project
        ):
            await initialized_sync_manager.sync_linear_to_gitlab(
                linear_issue_id="linear-issue-123",
                project_id="test/repo",
                gitlab_issue_iid=42,
            )

            # Verify issue was closed
            assert mock_gitlab_issue.state_event == "close"
            mock_gitlab_issue.save.assert_called()

    @pytest.mark.asyncio
    async def test_sync_linear_to_gitlab_handles_not_found_error(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_linear_client,
        sample_linear_issue,
    ):
        """Test that sync handles GitLab project not found error."""
        mock_linear_client.get_issue.return_value = sample_linear_issue

        with patch.object(
            initialized_sync_manager,
            "_get_gitlab_project",
            side_effect=GitLabNotFoundError("Project not found"),
        ):
            with pytest.raises(GitLabNotFoundError, match="not found"):
                await initialized_sync_manager.sync_linear_to_gitlab(
                    linear_issue_id="linear-issue-123",
                    project_id="test/repo",
                )


# ============================================================================
# GitLab → Linear Sync Tests
# ============================================================================


class TestGitLabToLinearSync:
    """Tests for GitLab → Linear issue synchronization."""

    @pytest.mark.asyncio
    async def test_sync_gitlab_to_linear_requires_initialization(
        self, gitlab_sync_manager: GitLabSyncManager
    ):
        """Test that syncing requires initialization."""
        with pytest.raises(GitLabSyncError, match="not initialized"):
            await gitlab_sync_manager.sync_gitlab_to_linear(
                project_id="test/repo",
                gitlab_issue_iid=42,
            )

    @pytest.mark.asyncio
    async def test_sync_gitlab_to_linear_creates_new_issue(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_linear_client,
        sample_gitlab_issue,
    ):
        """Test syncing GitLab issue creates new Linear issue."""
        # Setup mocks
        mock_linear_issue = {
            "id": "linear-123",
            "identifier": "LIN-1",
            "title": "[GitLab] Test GitLab Issue",
        }
        mock_linear_client.create_issue.return_value = mock_linear_issue

        mock_project = MagicMock()
        mock_project.issues = MagicMock()
        mock_project.issues.get = MagicMock(return_value=sample_gitlab_issue)

        with patch.object(
            initialized_sync_manager, "_get_gitlab_project", return_value=mock_project
        ):
            result = await initialized_sync_manager.sync_gitlab_to_linear(
                project_id="test/repo",
                gitlab_issue_iid=42,
            )

            assert result == mock_linear_issue
            mock_linear_client.create_issue.assert_called_once()

            # Verify issue creation args
            call_args = mock_linear_client.create_issue.call_args
            assert "[GitLab]" in call_args[1]["title"]
            assert "gitlab.example.com" in call_args[1]["description"]

    @pytest.mark.asyncio
    async def test_sync_gitlab_to_linear_updates_existing_issue(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_linear_client,
        sample_gitlab_issue,
    ):
        """Test syncing GitLab issue updates existing Linear issue."""
        # Setup mocks
        mock_linear_issue = {
            "id": "linear-123",
            "identifier": "LIN-1",
            "title": "[GitLab] Test GitLab Issue",
        }
        mock_linear_client.update_issue.return_value = mock_linear_issue

        mock_project = MagicMock()
        mock_project.issues = MagicMock()
        mock_project.issues.get = MagicMock(return_value=sample_gitlab_issue)

        with patch.object(
            initialized_sync_manager, "_get_gitlab_project", return_value=mock_project
        ):
            result = await initialized_sync_manager.sync_gitlab_to_linear(
                project_id="test/repo",
                gitlab_issue_iid=42,
                linear_issue_id="linear-123",
            )

            assert result == mock_linear_issue
            mock_linear_client.update_issue.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_gitlab_to_linear_respects_deduplication(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_dedup_manager,
        sample_gitlab_issue,
    ):
        """Test that sync respects deduplication logic."""
        mock_dedup_manager.should_process_event.return_value = False

        mock_project = MagicMock()
        mock_project.issues = MagicMock()
        mock_project.issues.get = MagicMock(return_value=sample_gitlab_issue)

        with patch.object(
            initialized_sync_manager, "_get_gitlab_project", return_value=mock_project
        ):
            result = await initialized_sync_manager.sync_gitlab_to_linear(
                project_id="test/repo",
                gitlab_issue_iid=42,
            )

            assert result is None
            mock_dedup_manager.should_process_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_gitlab_to_linear_marks_event_processed(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_linear_client,
        mock_dedup_manager,
        sample_gitlab_issue,
    ):
        """Test that sync marks event as processed."""
        mock_linear_issue = {
            "id": "linear-123",
            "identifier": "LIN-1",
            "title": "[GitLab] Test",
        }
        mock_linear_client.create_issue.return_value = mock_linear_issue

        mock_project = MagicMock()
        mock_project.issues = MagicMock()
        mock_project.issues.get = MagicMock(return_value=sample_gitlab_issue)

        with patch.object(
            initialized_sync_manager, "_get_gitlab_project", return_value=mock_project
        ):
            await initialized_sync_manager.sync_gitlab_to_linear(
                project_id="test/repo",
                gitlab_issue_iid=42,
            )

            mock_dedup_manager.mark_processed.assert_called_once()
            mock_dedup_manager.record_sync.assert_called_once()


# ============================================================================
# Comment Sync Tests
# ============================================================================


class TestCommentSync:
    """Tests for comment synchronization."""

    @pytest.mark.asyncio
    async def test_sync_gitlab_comment_to_linear(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_linear_client,
    ):
        """Test syncing GitLab comment to Linear."""
        mock_linear_comment = {
            "id": "comment-123",
            "body": "**testuser** commented on GitLab:\n\nThis is a test comment",
        }
        mock_linear_client.add_comment.return_value = mock_linear_comment

        result = await initialized_sync_manager.sync_gitlab_comment_to_linear(
            linear_issue_id="linear-123",
            gitlab_comment_body="This is a test comment",
            gitlab_comment_author="testuser",
            gitlab_comment_id=999,
        )

        assert result == mock_linear_comment
        mock_linear_client.add_comment.assert_called_once()

        # Verify comment attribution
        call_args = mock_linear_client.add_comment.call_args
        assert "testuser" in call_args[1]["body"]
        assert "GitLab" in call_args[1]["body"]

    @pytest.mark.asyncio
    async def test_sync_gitlab_comment_respects_deduplication(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_dedup_manager,
    ):
        """Test that comment sync respects deduplication."""
        mock_dedup_manager.should_process_event.return_value = False

        result = await initialized_sync_manager.sync_gitlab_comment_to_linear(
            linear_issue_id="linear-123",
            gitlab_comment_body="This is a test comment",
            gitlab_comment_id=999,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_sync_linear_comment_to_gitlab(
        self,
        initialized_sync_manager: GitLabSyncManager,
        sample_gitlab_issue,
    ):
        """Test syncing Linear comment to GitLab."""
        mock_gitlab_comment = MagicMock()
        sample_gitlab_issue.notes.create.return_value = mock_gitlab_comment

        result = await initialized_sync_manager.sync_linear_comment_to_gitlab(
            gitlab_issue=sample_gitlab_issue,
            linear_comment_body="Test comment from Linear",
            linear_comment_user="Linear User",
        )

        assert result == mock_gitlab_comment
        sample_gitlab_issue.notes.create.assert_called_once()

        # Verify comment attribution
        call_args = sample_gitlab_issue.notes.create.call_args
        assert "Linear User" in call_args[0][0]["body"]
        assert "Linear" in call_args[0][0]["body"]

    @pytest.mark.asyncio
    async def test_sync_linear_comment_without_user(
        self,
        initialized_sync_manager: GitLabSyncManager,
        sample_gitlab_issue,
    ):
        """Test syncing Linear comment without user attribution."""
        mock_gitlab_comment = MagicMock()
        sample_gitlab_issue.notes.create.return_value = mock_gitlab_comment

        result = await initialized_sync_manager.sync_linear_comment_to_gitlab(
            gitlab_issue=sample_gitlab_issue,
            linear_comment_body="Test comment",
        )

        assert result is not None
        call_args = sample_gitlab_issue.notes.create.call_args
        assert "Comment from Linear" in call_args[0][0]["body"]


# ============================================================================
# MR Status Sync Tests
# ============================================================================


class TestMRStatusSync:
    """Tests for MR status synchronization."""

    @pytest.mark.asyncio
    async def test_sync_merged_mr_to_linear(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_linear_client,
        sample_gitlab_mr,
    ):
        """Test syncing merged MR status to Linear."""
        sample_gitlab_mr.state = "merged"
        mock_comment = {"id": "comment-123", "body": "MR merged"}
        mock_linear_client.add_comment.return_value = mock_comment

        result = await initialized_sync_manager.sync_mr_status_to_linear(
            linear_issue_id="linear-123",
            merge_request=sample_gitlab_mr,
        )

        assert result is not None
        mock_linear_client.add_comment.assert_called_once()

        # Verify comment mentions merge
        call_args = mock_linear_client.add_comment.call_args
        assert "merged" in call_args[1]["body"].lower()

    @pytest.mark.asyncio
    async def test_sync_closed_mr_to_linear(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_linear_client,
        sample_gitlab_mr,
    ):
        """Test syncing closed (not merged) MR to Linear."""
        sample_gitlab_mr.state = "closed"
        mock_comment = {"id": "comment-123", "body": "MR closed"}
        mock_linear_client.add_comment.return_value = mock_comment

        result = await initialized_sync_manager.sync_mr_status_to_linear(
            linear_issue_id="linear-123",
            merge_request=sample_gitlab_mr,
        )

        assert result is not None
        mock_linear_client.add_comment.assert_called_once()

        # Verify comment mentions closed
        call_args = mock_linear_client.add_comment.call_args
        assert "closed" in call_args[1]["body"].lower()

    @pytest.mark.asyncio
    async def test_sync_open_mr_to_linear(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_linear_client,
        sample_gitlab_mr,
    ):
        """Test syncing open MR to Linear."""
        sample_gitlab_mr.state = "opened"
        mock_comment = {"id": "comment-123", "body": "MR opened"}
        mock_linear_client.add_comment.return_value = mock_comment

        result = await initialized_sync_manager.sync_mr_status_to_linear(
            linear_issue_id="linear-123",
            merge_request=sample_gitlab_mr,
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
    async def test_get_project_handles_not_found(self, initialized_sync_manager: GitLabSyncManager):
        """Test that getting a project handles not found error."""
        error = GitlabGetError("Not Found")
        error.response_code = 404
        initialized_sync_manager._gitlab_client.projects.get.side_effect = error

        with pytest.raises(GitLabNotFoundError, match="not found"):
            initialized_sync_manager._get_gitlab_project("test/nonexistent")

    @pytest.mark.asyncio
    async def test_get_project_handles_rate_limit(
        self, initialized_sync_manager: GitLabSyncManager
    ):
        """Test that getting a project handles rate limit error."""
        error = GitlabGetError("Rate limit exceeded")
        error.response_code = 429
        error.response_headers = {"Retry-After": "60"}
        initialized_sync_manager._gitlab_client.projects.get.side_effect = error

        with pytest.raises(GitLabRateLimitError, match="rate limit exceeded"):
            initialized_sync_manager._get_gitlab_project("test/repo")

    @pytest.mark.asyncio
    async def test_sync_handles_linear_client_error(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_linear_client,
    ):
        """Test that sync handles Linear client errors."""
        from src.integrations.linear.client import LinearClientError

        mock_linear_client.get_issue.side_effect = LinearClientError("Linear API error")

        with pytest.raises(LinearClientError):
            await initialized_sync_manager.sync_linear_to_gitlab(
                linear_issue_id="linear-123",
                project_id="test/repo",
            )

    @pytest.mark.asyncio
    async def test_sync_handles_gitlab_exception(
        self,
        initialized_sync_manager: GitLabSyncManager,
        mock_linear_client,
        sample_linear_issue,
    ):
        """Test that sync handles GitLab exceptions."""
        mock_linear_client.get_issue.return_value = sample_linear_issue

        with patch.object(
            initialized_sync_manager,
            "_get_gitlab_project",
            side_effect=GitlabError("Server error"),
        ):
            with pytest.raises(GitLabSyncError):
                await initialized_sync_manager.sync_linear_to_gitlab(
                    linear_issue_id="linear-123",
                    project_id="test/repo",
                )


# ============================================================================
# Singleton Tests
# ============================================================================


class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_gitlab_sync_manager_returns_singleton(self):
        """Test that get_gitlab_sync_manager returns the same instance."""
        reset_gitlab_sync_manager()

        manager1 = get_gitlab_sync_manager()
        manager2 = get_gitlab_sync_manager()

        assert manager1 is manager2

    def test_reset_gitlab_sync_manager(self):
        """Test that reset_gitlab_sync_manager resets the singleton."""
        manager1 = get_gitlab_sync_manager()
        reset_gitlab_sync_manager()
        manager2 = get_gitlab_sync_manager()

        assert manager1 is not manager2
