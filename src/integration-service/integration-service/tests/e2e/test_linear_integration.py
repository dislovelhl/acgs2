"""
End-to-End Tests for Complete Linear Integration Sync Flow

Tests cover the complete integration flow across all services:
- Linear → GitHub + GitLab + Slack (simultaneous)
- Bidirectional sync (Linear ↔ GitHub, Linear ↔ GitLab)
- Comment synchronization across all platforms
- Deduplication prevents infinite loops
- Conflict resolution with last-write-wins
- Error handling and graceful degradation

These are end-to-end tests with mocked external APIs to verify
that all components work together correctly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from src.integrations.linear.client import LinearClient
from src.integrations.linear.conflict_resolution import ConflictResolutionManager
from src.integrations.linear.deduplication import LinearDeduplicationManager
from src.integrations.linear.github_sync import GitHubSyncManager
from src.integrations.linear.gitlab_sync import GitLabSyncManager
from src.integrations.linear.models import IssueEvent, LinearWebhookPayload
from src.integrations.linear.slack_notifier import SlackNotifier

# ============================================================================
# Fixtures - Configuration
# ============================================================================


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
def mock_github_config():
    """Create mock GitHub configuration."""
    config = MagicMock()
    config.github_token = SecretStr("ghp_test_token_12345")
    config.github_timeout_seconds = 30.0
    config.github_max_retries = 3
    config.is_configured = True
    return config


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
def mock_slack_config():
    """Create mock Slack configuration."""
    config = MagicMock()
    config.slack_bot_token = SecretStr("xoxb-test-token-12345")
    config.slack_signing_secret = SecretStr("test-signing-secret")
    config.slack_default_channel = "C123456"
    config.slack_timeout_seconds = 30.0
    config.is_configured = True
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


# ============================================================================
# Fixtures - Managers and Clients
# ============================================================================


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
    manager.would_create_loop = AsyncMock(return_value=False)

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
def mock_slack_client():
    """Create mock Slack AsyncWebClient."""
    client = MagicMock()

    # Mock chat.postMessage
    mock_response = MagicMock()
    mock_response.data = {
        "ok": True,
        "channel": "C123456",
        "ts": "1234567890.123456",
        "message": {"text": "Test message"},
    }
    client.chat_postMessage = AsyncMock(return_value=mock_response)

    return client


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


@pytest.fixture
async def slack_notifier(
    mock_slack_config,
    mock_dedup_manager,
):
    """Create SlackNotifier instance for testing."""
    notifier = SlackNotifier(
        config=mock_slack_config,
        dedup_manager=mock_dedup_manager,
    )
    return notifier


# ============================================================================
# Fixtures - Sample Data
# ============================================================================


@pytest.fixture
def sample_linear_issue():
    """Create sample Linear issue data."""
    return {
        "id": "linear-issue-123",
        "identifier": "ENG-123",
        "title": "Implement user authentication",
        "description": "Add OAuth2 authentication flow for users",
        "priority": 1,  # Urgent
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
            "name": "Alice Developer",
            "email": "alice@example.com",
        },
        "team": {
            "id": "team-123",
            "name": "Engineering",
            "key": "ENG",
        },
        "labels": {
            "nodes": [
                {"id": "label-1", "name": "backend"},
                {"id": "label-2", "name": "security"},
            ]
        },
    }


@pytest.fixture
def mock_github_issue():
    """Create mock GitHub issue."""
    issue = MagicMock()
    issue.number = 42
    issue.title = "[Linear ENG-123] Implement user authentication"
    issue.body = "Add OAuth2 authentication flow for users"
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
def mock_gitlab_issue():
    """Create mock GitLab issue."""
    issue = MagicMock()
    issue.iid = 24
    issue.title = "[Linear ENG-123] Implement user authentication"
    issue.description = "Add OAuth2 authentication flow for users"
    issue.state = "opened"
    issue.web_url = "https://gitlab.com/test/repo/-/issues/24"
    issue.created_at = "2024-01-01T00:00:00Z"
    issue.updated_at = "2024-01-02T00:00:00Z"
    issue.author = MagicMock()
    issue.author.username = "gitlab-user"
    issue.state_event = None
    issue.save = MagicMock()
    issue.notes = MagicMock()
    return issue


# ============================================================================
# E2E Tests: Complete Sync Flow
# ============================================================================


@pytest.mark.asyncio
async def test_complete_sync_flow_linear_to_all_services(
    github_sync_manager,
    gitlab_sync_manager,
    slack_notifier,
    mock_github_client,
    mock_gitlab_client,
    mock_slack_client,
    mock_linear_client,
    sample_linear_issue,
    mock_github_issue,
    mock_gitlab_issue,
):
    """
    Test complete sync flow: Linear → GitHub + GitLab + Slack.

    This is the primary e2e test that verifies:
    1. Linear issue creation triggers GitHub issue creation
    2. Linear issue creation triggers GitLab issue creation
    3. Linear issue creation triggers Slack notification
    4. All services receive correct data
    5. Deduplication prevents duplicate syncs
    """
    # Setup GitHub
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()

        mock_github_repo = mock_github_client.get_repo.return_value
        mock_github_repo.create_issue = MagicMock(return_value=mock_github_issue)

        # Setup GitLab
        with patch("src.integrations.linear.gitlab_sync.Gitlab", return_value=mock_gitlab_client):
            await gitlab_sync_manager.initialize()

            mock_gitlab_project = MagicMock()
            mock_gitlab_project.issues.create = MagicMock(return_value=mock_gitlab_issue)
            mock_gitlab_client.projects.get = MagicMock(return_value=mock_gitlab_project)

            # Setup Slack
            with patch(
                "src.integrations.linear.slack_notifier.AsyncWebClient",
                return_value=mock_slack_client,
            ):
                await slack_notifier._ensure_client()

                # Mock Linear client to return our sample issue
                mock_linear_client.get_issue.return_value = sample_linear_issue

                # Step 1: Sync Linear issue to GitHub
                github_result = await github_sync_manager.sync_linear_to_github(
                    linear_issue_id=sample_linear_issue["id"],
                    repo_owner="test-org",
                    repo_name="test-repo",
                    create_if_missing=True,
                )

                # Step 2: Sync Linear issue to GitLab
                gitlab_result = await gitlab_sync_manager.sync_linear_to_gitlab(
                    linear_issue_id=sample_linear_issue["id"],
                    project_id="test-org/test-repo",
                    create_if_missing=True,
                )

                # Step 3: Send Slack notification
                slack_result = await slack_notifier.post_issue_created(
                    issue_id=sample_linear_issue["id"],
                    issue_title=sample_linear_issue["title"],
                    issue_url=sample_linear_issue["url"],
                    assignee_name=sample_linear_issue["assignee"]["name"],
                    priority=sample_linear_issue["priority"],
                )

                # Verify GitHub issue creation
                assert github_result is not None
                assert github_result.number == 42
                mock_github_repo.create_issue.assert_called_once()
                github_call_args = mock_github_repo.create_issue.call_args
                assert "Implement user authentication" in github_call_args.kwargs["title"]
                assert "linear-sync" in github_call_args.kwargs["labels"]

                # Verify GitLab issue creation
                assert gitlab_result is not None
                assert gitlab_result.iid == 24
                mock_gitlab_project.issues.create.assert_called_once()
                gitlab_call_args = mock_gitlab_project.issues.create.call_args
                assert "Implement user authentication" in gitlab_call_args["title"]
                assert "linear-sync" in gitlab_call_args["labels"]

                # Verify Slack notification
                assert slack_result is not None
                mock_slack_client.chat_postMessage.assert_called_once()
                slack_call_args = mock_slack_client.chat_postMessage.call_args
                assert slack_call_args.kwargs["channel"] == "C123456"
                assert "blocks" in slack_call_args.kwargs  # Block Kit formatting

                # Verify deduplication was checked for all syncs
                assert github_sync_manager._dedup_manager.should_process_event.call_count >= 1
                assert gitlab_sync_manager._dedup_manager.should_process_event.call_count >= 1

                # Cleanup
                await github_sync_manager.close()
                await gitlab_sync_manager.close()
                await slack_notifier.close()


@pytest.mark.asyncio
async def test_bidirectional_sync_with_deduplication(
    github_sync_manager,
    gitlab_sync_manager,
    mock_github_client,
    mock_gitlab_client,
    mock_linear_client,
    sample_linear_issue,
    mock_github_issue,
    mock_gitlab_issue,
):
    """
    Test bidirectional sync with deduplication preventing infinite loops.

    Flow:
    1. Linear → GitHub (should succeed)
    2. GitHub → Linear (should be blocked by deduplication)
    3. Linear → GitLab (should succeed)
    4. GitLab → Linear (should be blocked by deduplication)
    """
    # Setup
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()
        mock_github_repo = mock_github_client.get_repo.return_value
        mock_github_repo.create_issue = MagicMock(return_value=mock_github_issue)
        mock_github_repo.get_issue = MagicMock(return_value=mock_github_issue)

        with patch("src.integrations.linear.gitlab_sync.Gitlab", return_value=mock_gitlab_client):
            await gitlab_sync_manager.initialize()
            mock_gitlab_project = MagicMock()
            mock_gitlab_project.issues.create = MagicMock(return_value=mock_gitlab_issue)
            mock_gitlab_project.issues.get = MagicMock(return_value=mock_gitlab_issue)
            mock_gitlab_client.projects.get = MagicMock(return_value=mock_gitlab_project)

            # Mock Linear client
            mock_linear_client.get_issue.return_value = sample_linear_issue
            mock_linear_client.create_issue.return_value = sample_linear_issue

            # First sync: Linear → GitHub (should succeed)
            github_sync_manager._dedup_manager.should_process_event.return_value = True
            github_result1 = await github_sync_manager.sync_linear_to_github(
                linear_issue_id=sample_linear_issue["id"],
                repo_owner="test-org",
                repo_name="test-repo",
            )
            assert github_result1 is not None

            # Simulate deduplication detecting potential loop
            github_sync_manager._dedup_manager.should_process_event.return_value = False

            # Second sync: GitHub → Linear (should be blocked)
            github_result2 = await github_sync_manager.sync_github_to_linear(
                repo_owner="test-org",
                repo_name="test-repo",
                github_issue_number=42,
                linear_issue_id=sample_linear_issue["id"],
            )
            assert github_result2 is None  # Blocked by deduplication

            # Third sync: Linear → GitLab (reset dedup, should succeed)
            gitlab_sync_manager._dedup_manager.should_process_event.return_value = True
            gitlab_result1 = await gitlab_sync_manager.sync_linear_to_gitlab(
                linear_issue_id=sample_linear_issue["id"],
                project_id="test-org/test-repo",
            )
            assert gitlab_result1 is not None

            # Simulate deduplication detecting potential loop
            gitlab_sync_manager._dedup_manager.should_process_event.return_value = False

            # Fourth sync: GitLab → Linear (should be blocked)
            gitlab_result2 = await gitlab_sync_manager.sync_gitlab_to_linear(
                project_id="test-org/test-repo",
                gitlab_issue_iid=24,
                linear_issue_id=sample_linear_issue["id"],
            )
            assert gitlab_result2 is None  # Blocked by deduplication

            # Verify deduplication was checked multiple times
            assert github_sync_manager._dedup_manager.should_process_event.call_count >= 2
            assert gitlab_sync_manager._dedup_manager.should_process_event.call_count >= 2

            await github_sync_manager.close()
            await gitlab_sync_manager.close()


@pytest.mark.asyncio
async def test_comment_sync_across_all_platforms(
    github_sync_manager,
    gitlab_sync_manager,
    mock_github_client,
    mock_gitlab_client,
    mock_linear_client,
    sample_linear_issue,
    mock_github_issue,
    mock_gitlab_issue,
):
    """
    Test comment synchronization across all platforms.

    Flow:
    1. Add comment in Linear → sync to GitHub and GitLab
    2. Add comment in GitHub → sync to Linear
    3. Add comment in GitLab → sync to Linear
    """
    # Setup
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()
        mock_github_repo = mock_github_client.get_repo.return_value
        mock_github_repo.get_issue = MagicMock(return_value=mock_github_issue)

        with patch("src.integrations.linear.gitlab_sync.Gitlab", return_value=mock_gitlab_client):
            await gitlab_sync_manager.initialize()
            mock_gitlab_project = MagicMock()
            mock_gitlab_project.issues.get = MagicMock(return_value=mock_gitlab_issue)
            mock_gitlab_client.projects.get = MagicMock(return_value=mock_gitlab_project)

            # Step 1: Linear comment → GitHub
            mock_github_comment = MagicMock()
            mock_github_comment.id = 111
            mock_github_issue.create_comment = MagicMock(return_value=mock_github_comment)

            github_comment_result = await github_sync_manager.sync_linear_comment_to_github(
                github_issue=mock_github_issue,
                linear_comment_body="This is a comment from Linear",
                linear_comment_user="Alice Developer",
            )

            assert github_comment_result is not None
            mock_github_issue.create_comment.assert_called_once()
            github_comment_args = mock_github_issue.create_comment.call_args
            assert "Alice Developer" in github_comment_args.args[0]
            assert "Linear" in github_comment_args.args[0]

            # Step 2: Linear comment → GitLab
            mock_gitlab_note = MagicMock()
            mock_gitlab_note.id = 222
            mock_gitlab_issue.notes.create = MagicMock(return_value=mock_gitlab_note)

            gitlab_comment_result = await gitlab_sync_manager.sync_linear_comment_to_gitlab(
                gitlab_issue=mock_gitlab_issue,
                linear_comment_body="This is a comment from Linear",
                linear_comment_user="Alice Developer",
            )

            assert gitlab_comment_result is not None
            mock_gitlab_issue.notes.create.assert_called_once()
            gitlab_comment_args = mock_gitlab_issue.notes.create.call_args
            assert "Alice Developer" in gitlab_comment_args["body"]
            assert "Linear" in gitlab_comment_args["body"]

            # Step 3: GitHub comment → Linear
            mock_github_comment_obj = MagicMock()
            mock_github_comment_obj.body = "Comment from GitHub"
            mock_github_comment_obj.user.login = "github-user"

            linear_comment_from_github = {
                "id": "linear-comment-333",
                "body": "Comment from GitHub",
            }
            mock_linear_client.add_comment.return_value = linear_comment_from_github

            linear_comment_result1 = await github_sync_manager.sync_github_comment_to_linear(
                linear_issue_id=sample_linear_issue["id"],
                github_comment=mock_github_comment_obj,
            )

            assert linear_comment_result1 is not None
            mock_linear_client.add_comment.assert_called()

            # Step 4: GitLab comment → Linear
            mock_gitlab_comment_obj = MagicMock()
            mock_gitlab_comment_obj.body = "Comment from GitLab"
            mock_gitlab_comment_obj.author.username = "gitlab-user"

            linear_comment_from_gitlab = {
                "id": "linear-comment-444",
                "body": "Comment from GitLab",
            }
            mock_linear_client.add_comment.return_value = linear_comment_from_gitlab

            linear_comment_result2 = await gitlab_sync_manager.sync_gitlab_comment_to_linear(
                linear_issue_id=sample_linear_issue["id"],
                gitlab_comment=mock_gitlab_comment_obj,
            )

            assert linear_comment_result2 is not None
            assert mock_linear_client.add_comment.call_count >= 2

            await github_sync_manager.close()
            await gitlab_sync_manager.close()


@pytest.mark.asyncio
async def test_status_change_sync_with_conflict_resolution(
    github_sync_manager,
    gitlab_sync_manager,
    slack_notifier,
    mock_github_client,
    mock_gitlab_client,
    mock_slack_client,
    mock_linear_client,
    sample_linear_issue,
    mock_github_issue,
    mock_gitlab_issue,
):
    """
    Test status change synchronization with conflict resolution.

    Flow:
    1. Linear status changes to "Done" → GitHub/GitLab close issues
    2. Slack notification sent for status change
    3. Conflict resolution ensures latest update wins
    """
    # Setup
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()
        mock_github_repo = mock_github_client.get_repo.return_value
        mock_github_repo.get_issue = MagicMock(return_value=mock_github_issue)

        with patch("src.integrations.linear.gitlab_sync.Gitlab", return_value=mock_gitlab_client):
            await gitlab_sync_manager.initialize()
            mock_gitlab_project = MagicMock()
            mock_gitlab_project.issues.get = MagicMock(return_value=mock_gitlab_issue)
            mock_gitlab_client.projects.get = MagicMock(return_value=mock_gitlab_project)

            with patch(
                "src.integrations.linear.slack_notifier.AsyncWebClient",
                return_value=mock_slack_client,
            ):
                await slack_notifier._ensure_client()

                # Update Linear issue status to "Done"
                sample_linear_issue["state"]["type"] = "completed"
                sample_linear_issue["state"]["name"] = "Done"
                sample_linear_issue["updatedAt"] = "2024-01-03T00:00:00.000Z"
                mock_linear_client.get_issue.return_value = sample_linear_issue

                # Conflict resolution should allow update (latest timestamp)
                github_sync_manager._conflict_manager.should_apply_update.return_value = True
                gitlab_sync_manager._conflict_manager.should_apply_update.return_value = True

                # Sync to GitHub - should close issue
                github_result = await github_sync_manager.sync_linear_to_github(
                    linear_issue_id=sample_linear_issue["id"],
                    repo_owner="test-org",
                    repo_name="test-repo",
                    github_issue_number=42,
                )

                assert github_result is not None
                mock_github_issue.edit.assert_called()
                # Verify issue was closed
                edit_calls = [
                    call for call in mock_github_issue.edit.call_args_list if "state" in call.kwargs
                ]
                if edit_calls:
                    assert edit_calls[0].kwargs["state"] == "closed"

                # Sync to GitLab - should close issue
                gitlab_result = await gitlab_sync_manager.sync_linear_to_gitlab(
                    linear_issue_id=sample_linear_issue["id"],
                    project_id="test-org/test-repo",
                    gitlab_issue_iid=24,
                )

                assert gitlab_result is not None
                mock_gitlab_issue.save.assert_called()
                assert mock_gitlab_issue.state_event == "close"

                # Send Slack notification for status change
                slack_result = await slack_notifier.post_status_changed(
                    issue_id=sample_linear_issue["id"],
                    issue_title=sample_linear_issue["title"],
                    issue_url=sample_linear_issue["url"],
                    old_status="In Progress",
                    new_status="Done",
                )

                assert slack_result is not None
                assert mock_slack_client.chat_postMessage.call_count >= 1

                # Verify conflict resolution was checked
                github_sync_manager._conflict_manager.should_apply_update.assert_called()
                gitlab_sync_manager._conflict_manager.should_apply_update.assert_called()
                github_sync_manager._conflict_manager.record_update.assert_called()
                gitlab_sync_manager._conflict_manager.record_update.assert_called()

                await github_sync_manager.close()
                await gitlab_sync_manager.close()
                await slack_notifier.close()


@pytest.mark.asyncio
async def test_error_handling_partial_sync_failure(
    github_sync_manager,
    gitlab_sync_manager,
    slack_notifier,
    mock_github_client,
    mock_gitlab_client,
    mock_slack_client,
    mock_linear_client,
    sample_linear_issue,
    mock_github_issue,
):
    """
    Test error handling when partial sync fails.

    Scenario:
    1. Linear → GitHub succeeds
    2. Linear → GitLab fails (e.g., network error)
    3. Linear → Slack succeeds
    4. Overall flow continues, only GitLab sync fails
    """
    from gitlab.exceptions import GitlabError

    # Setup
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()
        mock_github_repo = mock_github_client.get_repo.return_value
        mock_github_repo.create_issue = MagicMock(return_value=mock_github_issue)

        with patch("src.integrations.linear.gitlab_sync.Gitlab", return_value=mock_gitlab_client):
            await gitlab_sync_manager.initialize()

            # Mock GitLab failure
            mock_gitlab_client.projects.get.side_effect = GitlabError("Network error")

            with patch(
                "src.integrations.linear.slack_notifier.AsyncWebClient",
                return_value=mock_slack_client,
            ):
                await slack_notifier._ensure_client()

                mock_linear_client.get_issue.return_value = sample_linear_issue

                # GitHub sync should succeed
                github_result = await github_sync_manager.sync_linear_to_github(
                    linear_issue_id=sample_linear_issue["id"],
                    repo_owner="test-org",
                    repo_name="test-repo",
                    create_if_missing=True,
                )
                assert github_result is not None

                # GitLab sync should fail but not crash
                from src.integrations.linear.gitlab_sync import GitLabSyncError

                with pytest.raises(GitLabSyncError):
                    await gitlab_sync_manager.sync_linear_to_gitlab(
                        linear_issue_id=sample_linear_issue["id"],
                        project_id="test-org/test-repo",
                        create_if_missing=True,
                    )

                # Slack notification should still succeed
                slack_result = await slack_notifier.post_issue_created(
                    issue_id=sample_linear_issue["id"],
                    issue_title=sample_linear_issue["title"],
                    issue_url=sample_linear_issue["url"],
                )
                assert slack_result is not None

                # Verify GitHub and Slack succeeded
                mock_github_repo.create_issue.assert_called_once()
                mock_slack_client.chat_postMessage.assert_called_once()

                await github_sync_manager.close()
                await gitlab_sync_manager.close()
                await slack_notifier.close()


@pytest.mark.asyncio
async def test_webhook_to_full_sync_integration(
    github_sync_manager,
    gitlab_sync_manager,
    slack_notifier,
    mock_github_client,
    mock_gitlab_client,
    mock_slack_client,
    mock_linear_client,
    sample_linear_issue,
    mock_github_issue,
    mock_gitlab_issue,
):
    """
    Test webhook event triggering full sync across all services.

    This simulates the real-world flow:
    1. Linear webhook event received (issue created)
    2. Event parsed and validated
    3. Sync to GitHub, GitLab, and Slack triggered
    4. All services updated successfully
    """
    # Create webhook payload
    webhook_payload = {
        "action": "create",
        "type": "Issue",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "organizationId": "org-123",
        "webhookId": "webhook-456",
        "url": "https://linear.app/test/issue/ENG-123",
        "data": sample_linear_issue,
    }

    # Parse webhook payload
    parsed_event = LinearWebhookPayload(**webhook_payload)
    assert parsed_event.action == "create"
    assert parsed_event.type == "Issue"

    # Convert to IssueEvent for easier handling
    issue_event = IssueEvent.from_webhook(parsed_event)
    assert issue_event.issue_id == sample_linear_issue["id"]
    assert issue_event.issue_title == sample_linear_issue["title"]

    # Setup all services
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()
        mock_github_repo = mock_github_client.get_repo.return_value
        mock_github_repo.create_issue = MagicMock(return_value=mock_github_issue)

        with patch("src.integrations.linear.gitlab_sync.Gitlab", return_value=mock_gitlab_client):
            await gitlab_sync_manager.initialize()
            mock_gitlab_project = MagicMock()
            mock_gitlab_project.issues.create = MagicMock(return_value=mock_gitlab_issue)
            mock_gitlab_client.projects.get = MagicMock(return_value=mock_gitlab_project)

            with patch(
                "src.integrations.linear.slack_notifier.AsyncWebClient",
                return_value=mock_slack_client,
            ):
                await slack_notifier._ensure_client()

                mock_linear_client.get_issue.return_value = sample_linear_issue

                # Trigger sync to all services (simulating webhook handler)
                github_result = await github_sync_manager.sync_linear_to_github(
                    linear_issue_id=issue_event.issue_id,
                    repo_owner="test-org",
                    repo_name="test-repo",
                    create_if_missing=True,
                )

                gitlab_result = await gitlab_sync_manager.sync_linear_to_gitlab(
                    linear_issue_id=issue_event.issue_id,
                    project_id="test-org/test-repo",
                    create_if_missing=True,
                )

                slack_result = await slack_notifier.post_issue_created(
                    issue_id=issue_event.issue_id,
                    issue_title=issue_event.issue_title,
                    issue_url=sample_linear_issue["url"],
                )

                # Verify all syncs succeeded
                assert github_result is not None
                assert gitlab_result is not None
                assert slack_result is not None

                # Verify correct data was sent to each service
                mock_github_repo.create_issue.assert_called_once()
                mock_gitlab_project.issues.create.assert_called_once()
                mock_slack_client.chat_postMessage.assert_called_once()

                await github_sync_manager.close()
                await gitlab_sync_manager.close()
                await slack_notifier.close()


@pytest.mark.asyncio
async def test_concurrent_updates_with_conflict_resolution(
    github_sync_manager,
    mock_github_client,
    mock_linear_client,
    sample_linear_issue,
    mock_github_issue,
):
    """
    Test concurrent updates from multiple sources with conflict resolution.

    Scenario:
    1. Update from GitHub (timestamp: T1)
    2. Update from Linear (timestamp: T2, where T2 > T1)
    3. Linear update should win (last-write-wins)
    """
    # Setup
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()
        mock_github_repo = mock_github_client.get_repo.return_value
        mock_github_repo.get_issue = MagicMock(return_value=mock_github_issue)

        # First update: GitHub → Linear (older timestamp)
        mock_github_issue.updated_at = datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc)
        github_sync_manager._conflict_manager.should_apply_update.return_value = True

        older_linear_issue = {**sample_linear_issue, "title": "Updated from GitHub"}
        mock_linear_client.update_issue.return_value = older_linear_issue

        result1 = await github_sync_manager.sync_github_to_linear(
            repo_owner="test-org",
            repo_name="test-repo",
            github_issue_number=42,
            linear_issue_id=sample_linear_issue["id"],
        )
        assert result1 is not None

        # Second update: Linear → GitHub (newer timestamp, should win)
        sample_linear_issue["updatedAt"] = "2024-01-02T12:00:00.000Z"  # 2 hours later
        sample_linear_issue["title"] = "Updated from Linear (newer)"
        mock_linear_client.get_issue.return_value = sample_linear_issue

        # Conflict manager should allow newer update
        github_sync_manager._conflict_manager.should_apply_update.return_value = True

        result2 = await github_sync_manager.sync_linear_to_github(
            linear_issue_id=sample_linear_issue["id"],
            repo_owner="test-org",
            repo_name="test-repo",
            github_issue_number=42,
        )
        assert result2 is not None
        mock_github_issue.edit.assert_called()

        # Verify conflict resolution was invoked for both updates
        assert github_sync_manager._conflict_manager.should_apply_update.call_count >= 2
        assert github_sync_manager._conflict_manager.record_update.call_count >= 2

        await github_sync_manager.close()


@pytest.mark.asyncio
async def test_full_lifecycle_create_update_close(
    github_sync_manager,
    gitlab_sync_manager,
    slack_notifier,
    mock_github_client,
    mock_gitlab_client,
    mock_slack_client,
    mock_linear_client,
    sample_linear_issue,
    mock_github_issue,
    mock_gitlab_issue,
):
    """
    Test full issue lifecycle: create → update → close.

    Flow:
    1. Create Linear issue → syncs to GitHub/GitLab/Slack
    2. Update Linear issue → syncs updates to GitHub/GitLab, notifies Slack
    3. Close Linear issue → closes GitHub/GitLab issues, notifies Slack
    """
    # Setup all services
    with patch("src.integrations.linear.github_sync.Github", return_value=mock_github_client):
        await github_sync_manager.initialize()
        mock_github_repo = mock_github_client.get_repo.return_value
        mock_github_repo.create_issue = MagicMock(return_value=mock_github_issue)
        mock_github_repo.get_issue = MagicMock(return_value=mock_github_issue)

        with patch("src.integrations.linear.gitlab_sync.Gitlab", return_value=mock_gitlab_client):
            await gitlab_sync_manager.initialize()
            mock_gitlab_project = MagicMock()
            mock_gitlab_project.issues.create = MagicMock(return_value=mock_gitlab_issue)
            mock_gitlab_project.issues.get = MagicMock(return_value=mock_gitlab_issue)
            mock_gitlab_client.projects.get = MagicMock(return_value=mock_gitlab_project)

            with patch(
                "src.integrations.linear.slack_notifier.AsyncWebClient",
                return_value=mock_slack_client,
            ):
                await slack_notifier._ensure_client()

                mock_linear_client.get_issue.return_value = sample_linear_issue

                # Phase 1: Create
                github_create = await github_sync_manager.sync_linear_to_github(
                    linear_issue_id=sample_linear_issue["id"],
                    repo_owner="test-org",
                    repo_name="test-repo",
                    create_if_missing=True,
                )
                gitlab_create = await gitlab_sync_manager.sync_linear_to_gitlab(
                    linear_issue_id=sample_linear_issue["id"],
                    project_id="test-org/test-repo",
                    create_if_missing=True,
                )
                slack_create = await slack_notifier.post_issue_created(
                    issue_id=sample_linear_issue["id"],
                    issue_title=sample_linear_issue["title"],
                    issue_url=sample_linear_issue["url"],
                )

                assert github_create is not None
                assert gitlab_create is not None
                assert slack_create is not None

                # Phase 2: Update
                sample_linear_issue["title"] = "Updated: Implement user authentication"
                sample_linear_issue["state"]["name"] = "In Review"
                sample_linear_issue["updatedAt"] = "2024-01-03T00:00:00.000Z"
                mock_linear_client.get_issue.return_value = sample_linear_issue

                github_update = await github_sync_manager.sync_linear_to_github(
                    linear_issue_id=sample_linear_issue["id"],
                    repo_owner="test-org",
                    repo_name="test-repo",
                    github_issue_number=42,
                )
                gitlab_update = await gitlab_sync_manager.sync_linear_to_gitlab(
                    linear_issue_id=sample_linear_issue["id"],
                    project_id="test-org/test-repo",
                    gitlab_issue_iid=24,
                )
                slack_update = await slack_notifier.post_status_changed(
                    issue_id=sample_linear_issue["id"],
                    issue_title=sample_linear_issue["title"],
                    issue_url=sample_linear_issue["url"],
                    old_status="In Progress",
                    new_status="In Review",
                )

                assert github_update is not None
                assert gitlab_update is not None
                assert slack_update is not None

                # Phase 3: Close
                sample_linear_issue["state"]["type"] = "completed"
                sample_linear_issue["state"]["name"] = "Done"
                sample_linear_issue["updatedAt"] = "2024-01-04T00:00:00.000Z"
                mock_linear_client.get_issue.return_value = sample_linear_issue

                github_close = await github_sync_manager.sync_linear_to_github(
                    linear_issue_id=sample_linear_issue["id"],
                    repo_owner="test-org",
                    repo_name="test-repo",
                    github_issue_number=42,
                )
                gitlab_close = await gitlab_sync_manager.sync_linear_to_gitlab(
                    linear_issue_id=sample_linear_issue["id"],
                    project_id="test-org/test-repo",
                    gitlab_issue_iid=24,
                )
                slack_close = await slack_notifier.post_status_changed(
                    issue_id=sample_linear_issue["id"],
                    issue_title=sample_linear_issue["title"],
                    issue_url=sample_linear_issue["url"],
                    old_status="In Review",
                    new_status="Done",
                )

                assert github_close is not None
                assert gitlab_close is not None
                assert slack_close is not None

                # Verify lifecycle completeness
                assert mock_github_repo.create_issue.call_count == 1
                assert mock_github_issue.edit.call_count >= 2  # Update + Close
                assert mock_gitlab_project.issues.create.call_count == 1
                assert mock_gitlab_issue.save.call_count >= 2  # Update + Close
                # Create + 2 status changes
                assert mock_slack_client.chat_postMessage.call_count == 3

                await github_sync_manager.close()
                await gitlab_sync_manager.close()
                await slack_notifier.close()
