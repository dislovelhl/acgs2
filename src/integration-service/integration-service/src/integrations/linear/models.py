"""
Pydantic models for Linear webhook payloads.

Defines models for Linear webhook events including issues, comments, and status changes.
Based on Linear's GraphQL schema and webhook documentation.

References:
- https://developers.linear.app/docs/graphql/webhooks
- https://studio.apollographql.com/public/Linear-API/variant/current/home
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


class WebhookAction(str, Enum):
    """Actions that can trigger Linear webhooks."""

    CREATE = "create"
    UPDATE = "update"
    REMOVE = "remove"


class LinearWebhookType(str, Enum):
    """Types of Linear webhook events."""

    ISSUE = "Issue"
    COMMENT = "Comment"
    PROJECT = "Project"
    CYCLE = "Cycle"
    ISSUE_LABEL = "IssueLabel"
    REACTION = "Reaction"


class IssuePriority(int, Enum):
    """Linear issue priority levels."""

    NO_PRIORITY = 0
    URGENT = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


# ============================================================================
# Nested Data Models
# ============================================================================


class LinearUser(BaseModel):
    """Linear user/actor model."""

    id: str = Field(..., description="User ID")
    name: str = Field(..., description="User's full name")
    email: Optional[str] = Field(None, description="User's email address")
    displayName: Optional[str] = Field(None, description="User's display name")
    avatarUrl: Optional[str] = Field(None, description="User's avatar URL")
    active: Optional[bool] = Field(None, description="Whether user is active")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class LinearTeam(BaseModel):
    """Linear team model."""

    id: str = Field(..., description="Team ID")
    name: str = Field(..., description="Team name")
    key: str = Field(..., description="Team key/identifier")
    description: Optional[str] = Field(None, description="Team description")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class LinearWorkflowState(BaseModel):
    """Linear workflow state model."""

    id: str = Field(..., description="State ID")
    name: str = Field(..., description="State name (e.g., 'Todo', 'In Progress', 'Done')")
    type: str = Field(..., description="State type (e.g., 'unstarted', 'started', 'completed')")
    color: Optional[str] = Field(None, description="State color")
    position: Optional[float] = Field(None, description="State position in workflow")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class LinearProject(BaseModel):
    """Linear project model."""

    id: str = Field(..., description="Project ID")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    state: Optional[str] = Field(None, description="Project state")
    targetDate: Optional[datetime] = Field(None, description="Project target date")
    startDate: Optional[datetime] = Field(None, description="Project start date")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class LinearCycle(BaseModel):
    """Linear cycle model."""

    id: str = Field(..., description="Cycle ID")
    number: int = Field(..., description="Cycle number")
    name: Optional[str] = Field(None, description="Cycle name")
    startsAt: Optional[datetime] = Field(None, description="Cycle start date")
    endsAt: Optional[datetime] = Field(None, description="Cycle end date")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class LinearLabel(BaseModel):
    """Linear label model."""

    id: str = Field(..., description="Label ID")
    name: str = Field(..., description="Label name")
    color: Optional[str] = Field(None, description="Label color")
    description: Optional[str] = Field(None, description="Label description")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )


# ============================================================================
# Issue Models
# ============================================================================


class LinearIssue(BaseModel):
    """
    Linear issue model representing the full issue data.

    This model includes all fields that can be present in an issue
    from Linear's GraphQL API and webhook payloads.
    """

    id: str = Field(..., description="Issue ID (UUID)")
    identifier: str = Field(..., description="Issue identifier (e.g., 'ENG-123')")
    title: str = Field(..., description="Issue title")
    description: Optional[str] = Field(None, description="Issue description (markdown)")
    priority: Optional[int] = Field(
        None, ge=0, le=4, description="Issue priority (0=none, 1=urgent, 2=high, 3=medium, 4=low)"
    )
    priorityLabel: Optional[str] = Field(None, description="Human-readable priority label")

    # Relationships
    team: LinearTeam = Field(..., description="Team this issue belongs to")
    state: LinearWorkflowState = Field(..., description="Current workflow state")
    assignee: Optional[LinearUser] = Field(None, description="Assigned user")
    creator: Optional[LinearUser] = Field(None, description="User who created the issue")
    project: Optional[LinearProject] = Field(None, description="Associated project")
    cycle: Optional[LinearCycle] = Field(None, description="Associated cycle")
    parent: Optional[Dict[str, Any]] = Field(None, description="Parent issue (if sub-issue)")
    labels: List[LinearLabel] = Field(default_factory=list, description="Issue labels")

    # URLs
    url: str = Field(..., description="Web URL to view the issue")
    branchName: Optional[str] = Field(None, description="Git branch name for this issue")

    # Timestamps
    createdAt: datetime = Field(..., description="Issue creation timestamp")
    updatedAt: datetime = Field(..., description="Issue last update timestamp")
    completedAt: Optional[datetime] = Field(None, description="Issue completion timestamp")
    canceledAt: Optional[datetime] = Field(None, description="Issue cancellation timestamp")
    startedAt: Optional[datetime] = Field(None, description="When work started on the issue")
    dueDate: Optional[datetime] = Field(None, description="Issue due date")

    # Estimates
    estimate: Optional[float] = Field(None, description="Estimate (story points or time)")

    # State tracking
    archived: bool = Field(default=False, description="Whether issue is archived")
    trashed: bool = Field(default=False, description="Whether issue is trashed")

    # Counts
    subIssueSortOrder: Optional[float] = Field(None, description="Sort order for sub-issues")
    sortOrder: Optional[float] = Field(None, description="Sort order")

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="allow",  # Allow extra fields from Linear API
    )

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(cls, v: Any) -> Optional[int]:
        """Validate and normalize priority value."""
        if v is None:
            return None
        if isinstance(v, str):
            # Handle string priority values
            priority_map = {
                "urgent": 1,
                "high": 2,
                "medium": 3,
                "low": 4,
                "none": 0,
                "no priority": 0,
            }
            return priority_map.get(v.lower(), 0)
        return int(v)


# ============================================================================
# Comment Models
# ============================================================================


class LinearComment(BaseModel):
    """Linear comment model."""

    id: str = Field(..., description="Comment ID")
    body: str = Field(..., description="Comment body (markdown)")
    user: Optional[LinearUser] = Field(None, description="User who created the comment")
    issue: Optional[Dict[str, str]] = Field(
        None, description="Associated issue (minimal data: id, identifier)"
    )
    parent: Optional[Dict[str, str]] = Field(None, description="Parent comment if reply")

    createdAt: datetime = Field(..., description="Comment creation timestamp")
    updatedAt: datetime = Field(..., description="Comment last update timestamp")
    editedAt: Optional[datetime] = Field(None, description="Comment last edit timestamp")

    url: Optional[str] = Field(None, description="Web URL to view the comment")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="allow",
    )


# ============================================================================
# Webhook Event Models
# ============================================================================


class WebhookData(BaseModel):
    """Base webhook data model containing the changed entity."""

    id: str = Field(..., description="Entity ID")
    createdAt: datetime = Field(..., description="Entity creation timestamp")
    updatedAt: datetime = Field(..., description="Entity last update timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="allow",
    )


class IssueWebhookData(WebhookData):
    """Issue-specific webhook data."""

    identifier: str = Field(..., description="Issue identifier (e.g., 'ENG-123')")
    title: str = Field(..., description="Issue title")
    description: Optional[str] = Field(None, description="Issue description")
    priority: Optional[int] = Field(None, description="Issue priority")

    team: LinearTeam = Field(..., description="Team")
    state: LinearWorkflowState = Field(..., description="Workflow state")
    assignee: Optional[LinearUser] = Field(None, description="Assigned user")
    creator: Optional[LinearUser] = Field(None, description="Creator")
    project: Optional[LinearProject] = Field(None, description="Associated project")
    cycle: Optional[LinearCycle] = Field(None, description="Associated cycle")
    labels: List[LinearLabel] = Field(default_factory=list, description="Labels")

    url: str = Field(..., description="Issue URL")

    completedAt: Optional[datetime] = Field(None, description="Completion timestamp")
    canceledAt: Optional[datetime] = Field(None, description="Cancellation timestamp")
    startedAt: Optional[datetime] = Field(None, description="Start timestamp")
    dueDate: Optional[datetime] = Field(None, description="Due date")

    archived: bool = Field(default=False, description="Archived status")
    trashed: bool = Field(default=False, description="Trashed status")


class CommentWebhookData(WebhookData):
    """Comment-specific webhook data."""

    body: str = Field(..., description="Comment body")
    user: Optional[LinearUser] = Field(None, description="Comment author")
    issue: Optional[Dict[str, str]] = Field(None, description="Associated issue")
    editedAt: Optional[datetime] = Field(None, description="Last edit timestamp")


class LinearWebhookPayload(BaseModel):
    """
    Root Linear webhook payload model.

    Linear sends webhooks with this structure:
    {
        "action": "create" | "update" | "remove",
        "type": "Issue" | "Comment" | "Project" | etc.,
        "data": { ... entity data ... },
        "url": "https://linear.app/...",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "organizationId": "org-123",
        "webhookId": "webhook-123"
    }
    """

    action: WebhookAction = Field(..., description="Action that triggered the webhook")
    type: LinearWebhookType = Field(..., description="Type of entity that changed")
    data: Union[IssueWebhookData, CommentWebhookData, WebhookData] = Field(
        ..., description="The entity data"
    )

    url: str = Field(..., description="URL to view the entity in Linear")
    createdAt: datetime = Field(..., description="When the webhook was created")

    # Organization context
    organizationId: str = Field(..., description="Organization ID")
    webhookId: Optional[str] = Field(None, description="Webhook subscription ID")

    # Additional metadata
    updatedFrom: Optional[Dict[str, Any]] = Field(
        None, description="Previous values for updated fields (only on 'update' action)"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="allow",
    )

    @model_validator(mode="before")
    @classmethod
    def parse_data_by_type(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the 'data' field based on 'type' field."""
        if "data" in values and "type" in values:
            webhook_type = values["type"]
            data = values["data"]

            # Parse data into appropriate model based on type
            if webhook_type == "Issue" or webhook_type == LinearWebhookType.ISSUE:
                try:
                    values["data"] = IssueWebhookData.model_validate(data)
                except Exception:
                    pass  # Fallback to base WebhookData if parsing fails

            elif webhook_type == "Comment" or webhook_type == LinearWebhookType.COMMENT:
                try:
                    values["data"] = CommentWebhookData.model_validate(data)
                except Exception:
                    pass  # Fallback to base WebhookData if parsing fails

        return values


# ============================================================================
# Event-Specific Models (Convenience wrappers)
# ============================================================================


class IssueEvent(BaseModel):
    """
    Convenience model for Issue webhook events.

    Provides a simplified interface for working with issue-related webhooks.
    """

    webhook_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this webhook event",
    )
    action: WebhookAction = Field(..., description="Action performed")
    issue: LinearIssue = Field(..., description="The issue data")

    organization_id: str = Field(..., description="Organization ID")
    url: str = Field(..., description="URL to view the issue")
    created_at: datetime = Field(..., description="Event timestamp")

    # Change tracking
    updated_from: Optional[Dict[str, Any]] = Field(
        None, description="Previous values (for update events)"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    @classmethod
    def from_webhook_payload(cls, payload: LinearWebhookPayload) -> "IssueEvent":
        """Create an IssueEvent from a LinearWebhookPayload."""
        if payload.type != LinearWebhookType.ISSUE:
            raise ValueError(f"Expected Issue webhook, got {payload.type}")

        if not isinstance(payload.data, IssueWebhookData):
            raise ValueError("Payload data is not IssueWebhookData")

        # Convert IssueWebhookData to LinearIssue
        issue_dict = payload.data.model_dump()
        issue = LinearIssue.model_validate(issue_dict)

        return cls(
            webhook_id=payload.webhookId or str(uuid4()),
            action=payload.action,
            issue=issue,
            organization_id=payload.organizationId,
            url=payload.url,
            created_at=payload.createdAt,
            updated_from=payload.updatedFrom,
        )


class CommentEvent(BaseModel):
    """
    Convenience model for Comment webhook events.

    Provides a simplified interface for working with comment-related webhooks.
    """

    webhook_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this webhook event",
    )
    action: WebhookAction = Field(..., description="Action performed")
    comment: LinearComment = Field(..., description="The comment data")

    organization_id: str = Field(..., description="Organization ID")
    url: str = Field(..., description="URL to view the comment")
    created_at: datetime = Field(..., description="Event timestamp")

    # Change tracking
    updated_from: Optional[Dict[str, Any]] = Field(
        None, description="Previous values (for update events)"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    @classmethod
    def from_webhook_payload(cls, payload: LinearWebhookPayload) -> "CommentEvent":
        """Create a CommentEvent from a LinearWebhookPayload."""
        if payload.type != LinearWebhookType.COMMENT:
            raise ValueError(f"Expected Comment webhook, got {payload.type}")

        if not isinstance(payload.data, CommentWebhookData):
            raise ValueError("Payload data is not CommentWebhookData")

        # Convert CommentWebhookData to LinearComment
        comment_dict = payload.data.model_dump()
        comment = LinearComment.model_validate(comment_dict)

        return cls(
            webhook_id=payload.webhookId or str(uuid4()),
            action=payload.action,
            comment=comment,
            organization_id=payload.organizationId,
            url=payload.url,
            created_at=payload.createdAt,
            updated_from=payload.updatedFrom,
        )


class StatusChangeEvent(BaseModel):
    """
    Convenience model for status change events.

    This is a specialized IssueEvent that specifically tracks state transitions.
    """

    webhook_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this webhook event",
    )
    issue: LinearIssue = Field(..., description="The issue data")

    previous_state: Optional[LinearWorkflowState] = Field(
        None, description="Previous workflow state"
    )
    new_state: LinearWorkflowState = Field(..., description="New workflow state")

    organization_id: str = Field(..., description="Organization ID")
    url: str = Field(..., description="URL to view the issue")
    created_at: datetime = Field(..., description="Event timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    @classmethod
    def from_issue_event(cls, event: IssueEvent) -> Optional["StatusChangeEvent"]:
        """
        Create a StatusChangeEvent from an IssueEvent.

        Returns None if the event doesn't represent a state change.
        """
        if event.action != WebhookAction.UPDATE:
            return None

        if not event.updated_from or "state" not in event.updated_from:
            return None

        # Extract previous state from updated_from
        previous_state_data = event.updated_from.get("state")
        previous_state = None
        if previous_state_data:
            try:
                previous_state = LinearWorkflowState.model_validate(previous_state_data)
            except Exception:
                pass  # Keep previous_state as None if validation fails

        return cls(
            webhook_id=event.webhook_id,
            issue=event.issue,
            previous_state=previous_state,
            new_state=event.issue.state,
            organization_id=event.organization_id,
            url=event.url,
            created_at=event.created_at,
        )

    @classmethod
    def from_webhook_payload(cls, payload: LinearWebhookPayload) -> Optional["StatusChangeEvent"]:
        """Create a StatusChangeEvent from a LinearWebhookPayload if it's a state change."""
        try:
            issue_event = IssueEvent.from_webhook_payload(payload)
            return cls.from_issue_event(issue_event)
        except (ValueError, KeyError):
            return None
