"""
Slack Block Kit Templates for Linear Integration

Provides reusable Slack Block Kit message templates for Linear issue notifications.
Templates support rich formatting with headers, sections, metadata, and action buttons.

Features:
- Issue created notification templates
- Status change notification templates
- Comment added notification templates
- Rich formatting with emoji and markdown
- Priority-based visual indicators
- Truncation for long content
- Action buttons with direct links to Linear

Usage:
    blocks = build_issue_created_template(
        issue_id="LIN-123",
        title="Fix authentication bug",
        description="Users unable to log in...",
        assignee="Alice",
        status="In Progress",
        priority="high",
        url="https://linear.app/issue/123"
    )
"""

from typing import Any, Dict, List, Optional


def build_issue_created_template(
    issue_id: str,
    title: str,
    description: Optional[str] = None,
    assignee: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Build Slack Block Kit template for issue created notification.

    Creates a rich notification with header, issue details, metadata, and action button.
    Includes priority-based emoji indicators and truncated descriptions for long content.

    Args:
        issue_id: Linear issue ID (e.g., "LIN-123")
        title: Issue title
        description: Issue description (truncated to 500 chars if longer)
        assignee: Assignee display name
        status: Current issue status
        priority: Issue priority (urgent, high, medium, low)
        url: Direct link to the Linear issue

    Returns:
        List of Slack Block Kit blocks ready for chat.postMessage

    Example:
        >>> blocks = build_issue_created_template(
        ...     issue_id="LIN-123",
        ...     title="Fix authentication bug",
        ...     description="Users unable to log in with SSO",
        ...     assignee="Alice",
        ...     status="In Progress",
        ...     priority="high",
        ...     url="https://linear.app/issue/123"
        ... )
        >>> # Returns list of Block Kit blocks
    """
    # Map priority to emoji for visual indicators
    priority_emoji_map = {
        "urgent": ":red_circle:",
        "high": ":large_orange_circle:",
        "medium": ":large_blue_circle:",
        "low": ":white_circle:",
    }

    # Get emoji for priority (case-insensitive)
    priority_key = priority.lower() if priority else ""
    emoji = priority_emoji_map.get(priority_key, ":white_circle:")

    # Start with header block
    blocks: List[Dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} New Linear Issue Created",
                "emoji": True,
            },
        },
        # Issue title
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{title}*",
            },
        },
    ]

    # Add description if provided (truncate long descriptions)
    if description:
        max_description_length = 500
        truncated_description = (
            description[:max_description_length] + "..."
            if len(description) > max_description_length
            else description
        )
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": truncated_description,
            },
        })

    # Build metadata context
    metadata_parts = [f"*Issue ID:* `{issue_id}`"]
    if status:
        metadata_parts.append(f"*Status:* {status}")
    if priority:
        metadata_parts.append(f"*Priority:* {priority}")
    if assignee:
        metadata_parts.append(f"*Assignee:* {assignee}")

    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": " | ".join(metadata_parts),
            }
        ],
    })

    # Add action button if URL provided
    if url:
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View in Linear",
                        "emoji": True,
                    },
                    "url": url,
                    "style": "primary",
                }
            ],
        })

    return blocks


def build_status_changed_template(
    issue_id: str,
    title: str,
    old_status: str,
    new_status: str,
    assignee: Optional[str] = None,
    url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Build Slack Block Kit template for status change notification.

    Creates a notification showing the status transition with visual arrow indicator.

    Args:
        issue_id: Linear issue ID (e.g., "LIN-123")
        title: Issue title
        old_status: Previous status value
        new_status: New status value
        assignee: Assignee display name
        url: Direct link to the Linear issue

    Returns:
        List of Slack Block Kit blocks ready for chat.postMessage

    Example:
        >>> blocks = build_status_changed_template(
        ...     issue_id="LIN-123",
        ...     title="Fix authentication bug",
        ...     old_status="In Progress",
        ...     new_status="Done",
        ...     assignee="Alice",
        ...     url="https://linear.app/issue/123"
        ... )
        >>> # Returns list of Block Kit blocks with status transition
    """
    blocks: List[Dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":arrows_counterclockwise: Issue Status Changed",
                "emoji": True,
            },
        },
        # Issue title with status transition
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{title}*\n\n`{old_status}` → `{new_status}`",
            },
        },
        # Metadata context
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"*Issue ID:* `{issue_id}`"
                        + (f" | *Assignee:* {assignee}" if assignee else "")
                    ),
                }
            ],
        },
    ]

    # Add action button if URL provided
    if url:
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View in Linear",
                        "emoji": True,
                    },
                    "url": url,
                }
            ],
        })

    return blocks


def build_comment_added_template(
    issue_id: str,
    title: str,
    comment_author: str,
    comment_body: str,
    url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Build Slack Block Kit template for comment added notification.

    Creates a notification showing who commented and the comment content (truncated if long).

    Args:
        issue_id: Linear issue ID (e.g., "LIN-123")
        title: Issue title
        comment_author: Display name of comment author
        comment_body: Comment text content (truncated to 300 chars if longer)
        url: Direct link to the Linear issue

    Returns:
        List of Slack Block Kit blocks ready for chat.postMessage

    Example:
        >>> blocks = build_comment_added_template(
        ...     issue_id="LIN-123",
        ...     title="Fix authentication bug",
        ...     comment_author="Bob",
        ...     comment_body="I've identified the root cause...",
        ...     url="https://linear.app/issue/123"
        ... )
        >>> # Returns list of Block Kit blocks with comment
    """
    # Truncate long comments
    max_comment_length = 300
    truncated_comment = (
        comment_body[:max_comment_length] + "..."
        if len(comment_body) > max_comment_length
        else comment_body
    )

    blocks: List[Dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":speech_balloon: New Comment Added",
                "emoji": True,
            },
        },
        # Issue title
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{title}*",
            },
        },
        # Comment with author
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"_{comment_author} commented:_\n\n{truncated_comment}",
            },
        },
        # Metadata context
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"*Issue ID:* `{issue_id}`",
                }
            ],
        },
    ]

    # Add action button if URL provided
    if url:
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View in Linear",
                        "emoji": True,
                    },
                    "url": url,
                }
            ],
        })

    return blocks


def build_issue_assigned_template(
    issue_id: str,
    title: str,
    assignee: str,
    previous_assignee: Optional[str] = None,
    status: Optional[str] = None,
    url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Build Slack Block Kit template for issue assignment notification.

    Creates a notification when an issue is assigned or reassigned.

    Args:
        issue_id: Linear issue ID (e.g., "LIN-123")
        title: Issue title
        assignee: New assignee display name
        previous_assignee: Previous assignee display name (if reassignment)
        status: Current issue status
        url: Direct link to the Linear issue

    Returns:
        List of Slack Block Kit blocks ready for chat.postMessage

    Example:
        >>> blocks = build_issue_assigned_template(
        ...     issue_id="LIN-123",
        ...     title="Fix authentication bug",
        ...     assignee="Alice",
        ...     previous_assignee="Bob",
        ...     status="In Progress",
        ...     url="https://linear.app/issue/123"
        ... )
        >>> # Returns list of Block Kit blocks
    """
    # Determine if this is a reassignment
    assignment_text = (
        f"`{previous_assignee}` → `{assignee}`"
        if previous_assignee
        else f"`{assignee}`"
    )

    blocks: List[Dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":raising_hand: Issue Assigned",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{title}*\n\n*Assignee:* {assignment_text}",
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"*Issue ID:* `{issue_id}`"
                        + (f" | *Status:* {status}" if status else "")
                    ),
                }
            ],
        },
    ]

    # Add action button if URL provided
    if url:
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View in Linear",
                        "emoji": True,
                    },
                    "url": url,
                }
            ],
        })

    return blocks


def build_priority_changed_template(
    issue_id: str,
    title: str,
    old_priority: str,
    new_priority: str,
    assignee: Optional[str] = None,
    url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Build Slack Block Kit template for priority change notification.

    Creates a notification showing priority change with visual emoji indicators.

    Args:
        issue_id: Linear issue ID (e.g., "LIN-123")
        title: Issue title
        old_priority: Previous priority value
        new_priority: New priority value
        assignee: Assignee display name
        url: Direct link to the Linear issue

    Returns:
        List of Slack Block Kit blocks ready for chat.postMessage

    Example:
        >>> blocks = build_priority_changed_template(
        ...     issue_id="LIN-123",
        ...     title="Fix authentication bug",
        ...     old_priority="medium",
        ...     new_priority="urgent",
        ...     assignee="Alice",
        ...     url="https://linear.app/issue/123"
        ... )
        >>> # Returns list of Block Kit blocks
    """
    # Map priority to emoji
    priority_emoji_map = {
        "urgent": ":red_circle:",
        "high": ":large_orange_circle:",
        "medium": ":large_blue_circle:",
        "low": ":white_circle:",
    }

    old_emoji = priority_emoji_map.get(old_priority.lower(), ":white_circle:")
    new_emoji = priority_emoji_map.get(new_priority.lower(), ":white_circle:")

    blocks: List[Dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":warning: Priority Changed",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{title}*\n\n"
                    f"{old_emoji} `{old_priority}` → {new_emoji} `{new_priority}`"
                ),
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"*Issue ID:* `{issue_id}`"
                        + (f" | *Assignee:* {assignee}" if assignee else "")
                    ),
                }
            ],
        },
    ]

    # Add action button if URL provided
    if url:
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View in Linear",
                        "emoji": True,
                    },
                    "url": url,
                }
            ],
        })

    return blocks


# Template fallback text generators
def get_issue_created_fallback(title: str) -> str:
    """
    Get fallback text for issue created notification.

    Args:
        title: Issue title

    Returns:
        Plain text fallback message
    """
    return f"New Linear issue created: {title}"


def get_status_changed_fallback(title: str, old_status: str, new_status: str) -> str:
    """
    Get fallback text for status changed notification.

    Args:
        title: Issue title
        old_status: Previous status
        new_status: New status

    Returns:
        Plain text fallback message
    """
    return f"Linear issue status changed: {title} ({old_status} → {new_status})"


def get_comment_added_fallback(title: str) -> str:
    """
    Get fallback text for comment added notification.

    Args:
        title: Issue title

    Returns:
        Plain text fallback message
    """
    return f"New comment on Linear issue: {title}"


def get_issue_assigned_fallback(title: str, assignee: str) -> str:
    """
    Get fallback text for issue assigned notification.

    Args:
        title: Issue title
        assignee: Assignee name

    Returns:
        Plain text fallback message
    """
    return f"Linear issue assigned: {title} → {assignee}"


def get_priority_changed_fallback(
    title: str, old_priority: str, new_priority: str
) -> str:
    """
    Get fallback text for priority changed notification.

    Args:
        title: Issue title
        old_priority: Previous priority
        new_priority: New priority

    Returns:
        Plain text fallback message
    """
    return f"Linear issue priority changed: {title} ({old_priority} → {new_priority})"
