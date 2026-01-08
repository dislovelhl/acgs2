#!/usr/bin/env python3
"""
Create and assign a coordination task for the ACGS-2 swarm
"""

import json
import os
import uuid
from datetime import datetime


def create_task():
    """Create a sample coordination task"""

    task = {
        "id": str(uuid.uuid4())[:8],
        "task": "Implement user authentication system",
        "description": "Design and implement a secure user authentication system with password hashing, JWT tokens, and role-based access control for the ACGS-2 platform",
        "priority": "high",
        "agent_type": "coder",
        "skills": ["python", "security", "authentication", "jwt"],
        "estimated_effort": "4-6 hours",
        "impact": "Critical security component for platform access",
        "status": "pending",
        "created_at": datetime.now().timestamp(),
        "assigned_agent": None,
        "dependencies": [],
        "subtasks": [
            "Design authentication schema",
            "Implement password hashing with bcrypt",
            "Create JWT token generation and validation",
            "Add role-based access control",
            "Write comprehensive tests",
            "Update API documentation",
        ],
    }

    # Save task to storage
    storage_dir = "src/claude-flow/claude-flow/storage"
    os.makedirs(storage_dir, exist_ok=True)

    task_file = os.path.join(storage_dir, f"task_{task['id']}.json")
    with open(task_file, "w") as f:
        json.dump(task, f, indent=2)

    result = {
        "success": True,
        "task": task,
        "message": f"Task '{task['task']}' created and ready for swarm coordination",
    }

    return result


if __name__ == "__main__":
    create_task()
