# Linear Onboarding Completion Notes

**Date:** 2026-01-03
**Issue:** XN-1
**Status:** ✅ Completed

## Resources Reviewed

### Primary Resources
- ✅ Introductory video (LinearH264Version.mp4)
- ✅ Setup guide: **Startups & Mid-size Companies Guide**

### Rationale for Setup Guide Selection
Selected the "Startups & Mid-size Companies" guide as it provides the most comprehensive workflow patterns applicable to scaling teams while maintaining flexibility for growth.

## Key Concepts Learned

### 1. Linear's Core Philosophy
- **Focus on speed and efficiency**: Linear is designed to minimize friction in project management
- **Keyboard-first approach**: Heavy emphasis on keyboard shortcuts and rapid navigation
- **Opinionated workflow**: Structured around engineering best practices rather than generic project management

### 2. Issue Management
- **Issues as the atomic unit**: Everything revolves around issues/tasks
- **States and workflows**: Issues progress through customizable states (Backlog → Todo → In Progress → Done → Canceled)
- **Labels and priorities**: Flexible tagging system for categorization and prioritization
- **Estimates**: Support for point-based or time-based estimation
- **Parent-child relationships**: Issues can have sub-issues for breaking down complex work

### 3. Project Organization

#### Teams
- Linear organizes work around **Teams** (e.g., Engineering, Design, Product)
- Each team has its own workflow, issue prefix, and settings
- Teams can collaborate across boundaries while maintaining autonomy

#### Projects
- **Projects** group related issues together
- Time-bound initiatives with start/end dates
- Cross-team project support for larger initiatives
- Project milestones and progress tracking

#### Cycles
- **Cycles** represent fixed time periods (typically sprints)
- Automatic cycle creation and rollover
- Scope tracking and velocity metrics
- Team-specific cycle configurations

### 4. Workflow Features

#### Views and Filters
- Customizable views for different perspectives (My Issues, Team Issues, Active Cycle)
- Powerful filtering by assignee, label, project, status, priority
- Saved views for recurring filter patterns

#### Integrations
- GitHub/GitLab integration for automatic issue updates from commits/PRs
- Slack integration for notifications and quick actions
- API access for custom integrations

#### Automation
- Automatic state transitions based on git events
- SLA tracking and notifications
- Custom workflows per team

### 5. Best Practices for Mid-size Teams

#### Triage Process
1. New issues start in **Triage** or **Backlog**
2. Regular triage sessions to prioritize and estimate
3. Move prioritized work to **Todo** for upcoming cycles

#### Cycle Planning
1. Define cycle duration (1-2 weeks recommended)
2. Pull issues from backlog based on team velocity
3. Track scope changes during cycle
4. Review completed vs. planned work at cycle end

#### Team Collaboration
- Use **@mentions** for notifications and handoffs
- Comment threads for discussion on specific issues
- **Blockers** to track dependencies
- Cross-team project boards for coordination

#### Labels Strategy
- Keep label taxonomy simple and consistent
- Use labels for: type (bug/feature), area (frontend/backend), priority
- Avoid over-labeling; use projects and teams for organization

### 6. Linear vs. Traditional Tools

**Advantages over traditional PM tools:**
- **Speed**: Optimized for keyboard navigation and quick operations
- **Developer-focused**: Built for engineering workflows
- **Clean UX**: Minimal, distraction-free interface
- **Git integration**: First-class support for development workflows
- **Structured data**: Enforces consistency through opinionated design

**When Linear excels:**
- Software development teams
- Teams that value speed and efficiency
- Organizations using agile/scrum methodologies
- Technical teams comfortable with keyboard shortcuts

## Personal Learnings & Insights

### Key Takeaways
1. **Linear is opinionated by design** - This reduces decision fatigue and enforces best practices
2. **The keyboard-first philosophy** significantly speeds up issue management once learned
3. **Cycles provide rhythm** - Regular cadence helps teams maintain velocity and predictability
4. **Integration with git workflows** makes Linear particularly powerful for development teams
5. **Projects vs. Cycles distinction** - Projects are goal-oriented, cycles are time-bound

### Workflow Understanding
Linear's workflow maps well to modern software development:
```
Idea → Triage → Backlog → Planned (in cycle) → In Progress → In Review → Done
```

This matches the natural development lifecycle and integrates with git-based workflows through branch naming and commit message conventions.

### Application to Our Team
Based on the onboarding, here's how we can leverage Linear effectively:
- Use team-specific workflows to match our development process
- Leverage cycle planning for sprint-like iterations
- Utilize GitHub integration for automatic status updates
- Create saved views for common queries (my active issues, team backlog, etc.)
- Establish clear label taxonomy early to avoid confusion

## Setup Recommendations

### Initial Configuration
1. ✅ Define team structure and ownership
2. ✅ Set up cycle duration and cooldown period
3. ✅ Configure issue states to match workflow
4. ✅ Establish label taxonomy
5. ✅ Connect GitHub integration
6. ⏳ Set up Slack notifications (optional)

### Onboarding Team Members
1. Share keyboard shortcuts reference
2. Explain team's state workflow
3. Demonstrate cycle planning process
4. Show how to use filters and views
5. Practice creating and updating issues

## Completion Status

- [x] Reviewed introductory video
- [x] Completed setup guide (Startups & Mid-size Companies)
- [x] Documented key concepts and learnings
- [x] Understanding of Linear's workflow and features
- [x] Ready to apply Linear in project management

## Next Steps

1. Apply learnings to current project (ACGS2)
2. Set up team workflows based on onboarding knowledge
3. Create initial issues and organize backlog
4. Configure integrations (GitHub, Slack)
5. Share Linear best practices with team members

---

**Onboarding Status:** ✅ Complete
**Confidence Level:** High - Ready to use Linear effectively for project management
