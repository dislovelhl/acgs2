# Specification: Set up your teams

## Overview

This task is a **non-technical administrative task** from Linear workspace onboarding. It provides guidance for setting up organizational teams in Linear's project management platform. The task contains only external documentation links and does not require any code changes to the ACGS2 monorepo.

## Workflow Type

**Type**: Administrative (marked as "feature" in requirements, but no development needed)

**Rationale**: This is a Linear workspace setup task that involves:
- Reading documentation about Linear's workspace, teams, and member management
- Inviting team members through Linear's settings interface
- Configuring organizational structure in Linear platform

**No codebase changes are required.**

## Task Scope

### Services Involved
- **None** - This task does not touch any services in the ACGS2 monorepo

### This Task Will:
- [ ] Provide guidance on Linear workspace configuration
- [ ] Direct user to Linear documentation for team setup
- [ ] Direct user to Linear settings for member invitations

### Out of Scope:
- Any code changes to analytics-dashboard
- Any code changes to integration-service
- Any code changes to adaptive-learning-engine
- Any code changes to claude-flow
- Any code changes to acgs2-neural-mcp
- Any database modifications
- Any API endpoint creation
- Any UI component development

## Service Context

### No Services Required

This task operates entirely within Linear's platform and does not involve the ACGS2 codebase.

**Available Services in ACGS2 Monorepo:**
- analytics-dashboard (React/TypeScript, port 3000)
- integration-service (FastAPI/Python, port 8000)
- adaptive-learning-engine (FastAPI/Python, port 8001)
- claude-flow (TypeScript CLI)
- acgs2-neural-mcp (TypeScript MCP server)

**None of these services require changes for this task.**

## Files to Modify

**No files require modification.**

| File | Service | What to Change |
|------|---------|---------------|
| N/A | N/A | This is an administrative task with no code changes |

## Files to Reference

**No reference files needed.**

| File | Pattern to Copy |
|------|----------------|
| N/A | This task does not involve code patterns |

## Patterns to Follow

### Administrative Task Pattern

**Key Points:**
- This task appears to be a default Linear onboarding issue
- It may have been automatically created when the workspace was set up
- The task is likely already complete or not applicable to this development project
- If the Linear workspace already has teams configured, this task can be marked complete

## Requirements

### Functional Requirements

1. **Understand Linear Workspace Structure**
   - Description: Read Linear's documentation on workspaces
   - Acceptance: User understands how Linear organizes work
   - Documentation: https://linear.app/docs/workspaces

2. **Understand Team Organization**
   - Description: Read Linear's documentation on teams
   - Acceptance: User understands how to structure teams and configure workflows
   - Documentation: https://linear.app/docs/teams

3. **Understand Member Roles**
   - Description: Read Linear's documentation on member roles (Admin, Member, Guest)
   - Acceptance: User understands role-based access control in Linear
   - Documentation: https://linear.app/docs/invite-members

4. **Invite Team Members (Optional)**
   - Description: If needed, invite team members via CSV or unique link
   - Acceptance: Team members have been added to the Linear workspace
   - Action: Navigate to http://linear.app/settings/members

### Edge Cases

1. **Task Already Complete** - If the Linear workspace already has teams and members configured, this task can be marked as complete
2. **Task Not Applicable** - If this is a solo project or teams are managed elsewhere, this task may not be relevant
3. **Automated Onboarding Task** - This appears to be a default Linear onboarding task that may not represent actual work needed

## Implementation Notes

### DO
- Review the Linear workspace to see if teams are already configured
- If teams need to be set up, follow Linear's documentation
- Mark this Linear issue as complete if teams are already configured
- Consider if this task is actually needed for the project

### DON'T
- Attempt to implement team management features in the codebase (unless explicitly requested as a separate feature)
- Create new services or components for this task
- Modify any existing code for this task

## Development Environment

### Start Services

**Not applicable** - No services need to be started for this administrative task.

For reference, the ACGS2 monorepo services can be started with:

```bash
# Frontend (analytics-dashboard)
cd analytics-dashboard && npm run dev

# Backend (integration-service)
cd integration-service && uvicorn src.main:app --reload --port 8000

# Backend (adaptive-learning-engine)
cd adaptive-learning-engine && uvicorn src.main:app --reload --port 8001

# CLI (claude-flow)
cd claude-flow && npm run dev

# MCP Server (acgs2-neural-mcp)
cd acgs2-neural-mcp && npm run dev
```

### Service URLs
- analytics-dashboard: http://localhost:3000
- integration-service: http://localhost:8000 (API docs: /docs)
- adaptive-learning-engine: http://localhost:8001 (API docs: /docs)

### Required Environment Variables
**Not applicable** - No environment variables needed for this administrative task.

## Success Criteria

The task is complete when:

1. [ ] User has reviewed Linear's workspace documentation
2. [ ] User has reviewed Linear's teams documentation
3. [ ] User has reviewed Linear's member invitation documentation
4. [ ] User has determined if teams need to be configured in Linear
5. [ ] If needed, team members have been invited via Linear settings
6. [ ] Linear issue XN-2 has been marked as complete

**Alternative Completion:**
If the Linear workspace already has teams and members configured, or if this task is not applicable to the project, the issue can be immediately marked as complete.

## QA Acceptance Criteria

**CRITICAL**: This is an administrative task with no code changes to verify.

### Administrative Verification
| Check | How to Verify | Expected Outcome |
|-------|---------------|------------------|
| Linear workspace configured | Visit Linear workspace | Workspace exists and is accessible |
| Teams configured (if needed) | Check Linear teams page | Teams are created and configured |
| Members invited (if needed) | Check Linear members page | Team members have appropriate roles |
| Issue status | Check Linear issue XN-2 | Issue is marked as complete |

### Unit Tests
**Not applicable** - No code changes, no unit tests required.

### Integration Tests
**Not applicable** - No code changes, no integration tests required.

### End-to-End Tests
**Not applicable** - No code changes, no E2E tests required.

### Browser Verification
**Not applicable** - This task does not involve the ACGS2 web applications.

### Database Verification
**Not applicable** - This task does not involve the ACGS2 databases.

### QA Sign-off Requirements
- [ ] User confirms Linear workspace is properly configured (or not needed)
- [ ] User confirms teams are set up (or not needed)
- [ ] User confirms members are invited (or not needed)
- [ ] Linear issue XN-2 is marked as complete
- [ ] No codebase changes were made (as none are required)

## Recommendations

### Option 1: Mark as Complete
If the Linear workspace already has teams and members configured, simply mark Linear issue XN-2 as complete.

### Option 2: Follow Linear Documentation
If team setup is actually needed, follow the documentation links provided in the issue description.

### Option 3: Clarify Requirements
If this task was intended to mean "implement team management features in the ACGS2 codebase", clarify with the project stakeholders and create a new, properly scoped issue with technical requirements.

### Option 4: Close as Not Applicable
If this is a solo project or teams are managed in a different system, close this issue as not applicable.

## Notes for Implementation Phase

**Critical**: The Implementation Agent should recognize that this is a non-technical task and:
1. Not attempt to write any code
2. Verify the Linear workspace configuration status
3. Guide the user to mark the issue as complete or take action in Linear's interface
4. Request clarification if the user actually wants team management features built into the codebase

**If a team management feature IS needed in the codebase**, a new specification should be created with:
- Database schema for workspaces, teams, and members
- API endpoints for team CRUD operations
- UI components for team management
- Role-based access control implementation
- CSV import functionality
- Invite link generation system
