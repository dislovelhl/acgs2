# Video Script: Example Project Walkthrough

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

## Video Metadata

| Property | Value |
|----------|-------|
| **Title** | ACGS-2 Examples: Running Your First Governance Project |
| **Duration** | 10-12 minutes |
| **Target Audience** | Developers who completed the quickstart |
| **Prerequisites** | ACGS-2 running, Python installed |
| **Outcome** | Viewer runs all 3 example projects end-to-end |

## Production Notes

### Recording Setup

- **Resolution**: 1920x1080 (1080p)
- **Frame Rate**: 30fps
- **Audio**: Clear voiceover with minimal background noise
- **Terminal Font**: 14pt minimum for readability
- **Browser**: Use Chrome or Firefox with clean profile

### Style Guidelines

- Keep terminal windows large and readable
- Pause after each command to show output
- Highlight key sections with callouts/annotations
- Use consistent pacing (not too fast)
- Add chapter markers for easy navigation
- Show code side-by-side with output where helpful

---

## Script

### [00:00] Introduction (30 seconds)

**VISUAL**: ACGS-2 logo with title "Example Project Walkthrough"

**VOICEOVER**:
> Welcome to the ACGS-2 Example Project Walkthrough! In this video, we'll run through all three example projects that demonstrate real-world AI governance scenarios.
>
> Each example builds on core concepts and shows you practical patterns you can use in your own projects.
>
> By the end, you'll understand how to implement RBAC policies, AI model approval workflows, and context-based data access control.

**ACTION**: Show quick preview of the three examples (folder structure)

---

### [00:30] Overview of Examples (1 minute)

**VISUAL**: Split screen showing examples folder structure

**VOICEOVER**:
> ACGS-2 includes three progressively advanced examples.

**ACTION**: Navigate to examples directory

```bash
cd examples
ls -la
```

**VOICEOVER**:
> First, we have Basic Policy Evaluation - a hello world example that demonstrates the fundamentals.
>
> Second, AI Model Approval - this shows a real governance workflow with risk-based approval decisions.
>
> Third, Data Access Control - implementing RBAC and attribute-based access control together.

**CALLOUT**: Highlight each directory:
- `01-basic-policy-evaluation/` - Hello world
- `02-ai-model-approval/` - Risk-based workflow
- `03-data-access-control/` - RBAC + ABAC patterns

---

### [01:30] Example 1: Basic Policy Evaluation (3 minutes)

**VISUAL**: Terminal window

**VOICEOVER**:
> Let's start with the basic example. This is your "hello world" for OPA policy evaluation.

**ACTION**: Navigate to directory

```bash
cd 01-basic-policy-evaluation
ls -la
```

**VOICEOVER**:
> Every example has the same structure: a README for documentation, compose.yaml for Docker, requirements.txt for Python dependencies, and a policies directory.

#### Start OPA

**ACTION**: Start OPA

```bash
docker compose up -d
docker compose ps
```

**VOICEOVER**:
> We start OPA using Docker Compose. This mounts our policies into the container.

**ACTION**: Show health check

```bash
curl -s http://localhost:8181/health | python3 -m json.tool
```

#### Explore the Policy

**VISUAL**: Show policy file in editor or cat

**ACTION**: Show the policy

```bash
cat policies/hello.rego
```

**VOICEOVER**:
> Here's our policy. It's a simple RBAC example that uses rego.v1 - the modern Rego syntax.
>
> Admins are allowed any action. Developers can only read. Anyone else is denied.

**CALLOUT**: Highlight key sections:
- `package hello` - Policy namespace
- `import rego.v1` - Modern syntax
- `default allow := false` - Deny by default

#### Run the Python Client

**ACTION**: Install and run Python client

```bash
pip install -r requirements.txt
python evaluate_policy.py
```

**VOICEOVER**:
> The Python client runs through several test cases, showing which requests are allowed and denied.

**ACTION**: Pause on output showing colored results

**CALLOUT**: Highlight:
- Green "ALLOWED" for admin access
- Red "DENIED" for guest access

#### Clean Up

```bash
docker compose down
cd ..
```

---

### [04:30] Example 2: AI Model Approval (3 minutes)

**VISUAL**: Terminal window with code editor split

**VOICEOVER**:
> Now let's look at a more realistic scenario - an AI model approval workflow. This demonstrates how enterprises govern AI deployments.

**ACTION**: Navigate to directory

```bash
cd 02-ai-model-approval
ls -la
```

#### Start Services

```bash
docker compose up -d
```

#### Explore the Policies

**ACTION**: Show the policy files

```bash
cat policies/model_approval.rego
```

**VOICEOVER**:
> This policy implements a tiered approval system based on risk score.
>
> Low-risk models - score under 0.3 - can be auto-approved.
> Medium-risk models need compliance checks.
> High-risk models require human reviewer approval.

**CALLOUT**: Highlight risk thresholds:
- Low: 0.0 - 0.3
- Medium: 0.3 - 0.7
- High: 0.7 - 1.0

**ACTION**: Show risk assessment policy

```bash
cat policies/risk_assessment.rego
```

**VOICEOVER**:
> The risk assessment policy categorizes models and provides helper rules that the approval policy uses.

#### Test Different Scenarios

**ACTION**: Query OPA directly

```bash
# Low-risk model - auto-approved
curl -s -X POST http://localhost:8181/v1/data/ai/model/approval/allowed \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "model": {"id": "simple-model", "risk_score": 0.2},
      "compliance": {"bias_tested": true, "documentation_complete": true, "security_reviewed": true},
      "deployment": {"environment": "staging"}
    }
  }' | python3 -m json.tool
```

**VOICEOVER**:
> A low-risk model with all compliance checks passes - result is true.

**ACTION**: Test high-risk without reviewer

```bash
# High-risk model - needs reviewer
curl -s -X POST http://localhost:8181/v1/data/ai/model/approval/denial_reasons \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "model": {"id": "risky-model", "risk_score": 0.85},
      "compliance": {"bias_tested": true, "documentation_complete": true, "security_reviewed": true},
      "deployment": {"environment": "production"}
    }
  }' | python3 -m json.tool
```

**VOICEOVER**:
> A high-risk model without reviewer approval is denied. The denial_reasons rule tells us exactly why - it needs a human reviewer.

**CALLOUT**: Highlight denial reason: "High-risk model requires reviewer approval"

#### Run the FastAPI Service

**ACTION**: Start the API

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000 &

# Give it a moment to start
sleep 3

# Test the endpoint
curl -s -X POST http://localhost:8000/api/models/approve \
  -H "Content-Type: application/json" \
  -d '{"model_id": "test-model", "risk_score": 0.25}' | python3 -m json.tool
```

**VOICEOVER**:
> The FastAPI service provides a REST API that wraps OPA queries. This is the pattern you'd use in production - your application calls your API, which calls OPA for policy decisions.

#### Clean Up

```bash
# Stop FastAPI
pkill -f uvicorn

docker compose down
cd ..
```

---

### [07:30] Example 3: Data Access Control (3 minutes)

**VISUAL**: Terminal window

**VOICEOVER**:
> Our final example combines RBAC and ABAC - role-based and attribute-based access control. This is what you'd use for protecting sensitive data.

**ACTION**: Navigate to directory

```bash
cd 03-data-access-control
ls -la
```

#### Start Services

```bash
docker compose up -d
```

#### Explore the Policies

**ACTION**: Show policy files

```bash
cat policies/rbac.rego
```

**VOICEOVER**:
> The RBAC policy defines roles and their permissions. We have a hierarchy where analysts inherit viewer permissions, and admins inherit analyst permissions.

**CALLOUT**: Highlight role hierarchy diagram

**ACTION**: Show data access policy

```bash
cat policies/data_access.rego
```

**VOICEOVER**:
> The data access policy goes further - it checks data sensitivity levels and user clearance. Even if you have the right role, you need proper clearance for highly sensitive data.

**CALLOUT**: Highlight sensitivity levels:
- public
- internal
- confidential
- restricted

#### Run Access Checks

**ACTION**: Run the Python client

```bash
pip install -r requirements.txt
python check_access.py
```

**VOICEOVER**:
> The client tests various scenarios - users accessing datasets with different sensitivity levels.

**ACTION**: Pause on output showing:
- Admin accessing restricted data: ALLOWED
- Analyst accessing confidential data: ALLOWED (within clearance)
- Viewer accessing restricted data: DENIED (insufficient clearance)

**CALLOUT**: Highlight the decision matrix

#### Understanding Context-Based Decisions

**ACTION**: Show a specific query

```bash
curl -s -X POST http://localhost:8181/v1/data/access/data/allowed \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "user": {"id": "bob", "role": "analyst", "clearance_level": 2},
      "resource": {"id": "financial-report", "sensitivity": "confidential", "sensitivity_level": 3},
      "action": "read"
    }
  }' | python3 -m json.tool
```

**VOICEOVER**:
> Bob is an analyst with clearance level 2, trying to access confidential data at level 3. Even though analysts can read confidential data by role, Bob's clearance is too low.

**ACTION**: Query denial reasons

```bash
curl -s -X POST http://localhost:8181/v1/data/access/data/denial_reasons ...
```

**VOICEOVER**:
> The denial reasons explain that clearance level is insufficient. This is the power of ABAC - decisions based on attributes, not just roles.

#### Clean Up

```bash
docker compose down
cd ..
```

---

### [10:30] Summary and Next Steps (1.5 minutes)

**VISUAL**: Summary slide with three examples

**VOICEOVER**:
> Let's recap what we've learned.
>
> Example 1 showed us the basics - how to write policies and query them from Python.
>
> Example 2 demonstrated a real-world governance workflow with risk-based decisions and tiered approval.
>
> Example 3 combined RBAC and ABAC for sophisticated data access control.

**ACTION**: Show file browser navigating to notebooks

**VOICEOVER**:
> For interactive experimentation, check out the Jupyter notebooks. They let you visualize policy decisions and test scenarios in a live environment.
>
> The notebooks are at notebooks/01-policy-experimentation.ipynb and notebooks/02-governance-visualization.ipynb.

**ACTION**: Show documentation links

**VOICEOVER**:
> If you want to dive deeper into Rego policy language, the docs/quickstart/README.md has a comprehensive guide.
>
> Thanks for watching! Don't forget to share your feedback to help us improve these examples.

**VISUAL**: End screen with:
- Link to examples/README.md
- Link to Jupyter notebooks
- Feedback form link
- ACGS-2 logo

---

## Chapter Markers

For YouTube or video platforms that support chapters:

```
0:00 Introduction
0:30 Overview of Examples
1:30 Example 1: Basic Policy Evaluation
4:30 Example 2: AI Model Approval
7:30 Example 3: Data Access Control
10:30 Summary and Next Steps
```

---

## Post-Production Checklist

- [ ] Add ACGS-2 intro/outro branding
- [ ] Add chapter markers
- [ ] Add captions/subtitles
- [ ] Add on-screen annotations for key commands
- [ ] Highlight risk thresholds and clearance levels
- [ ] Review audio levels
- [ ] Export in 1080p
- [ ] Upload to video hosting platform
- [ ] Update documentation with video link

---

## Video Hosting

After recording, upload to:

1. **YouTube** (primary) - Create unlisted/public video
2. **Vimeo** (alternative) - For embedded viewing
3. **Project assets** - Keep source files for future updates

Update the following files with video links:
- `examples/README.md` - Video Tutorials section
- `docs/quickstart/README.md` - Link in Examples section

---

## Recording Preparation Checklist

Before recording this video:

- [ ] Docker environment is clean (`docker compose down -v && docker system prune -f`)
- [ ] All three examples are tested and working
- [ ] Python dependencies are fresh (`pip install -r requirements.txt` in each example)
- [ ] No leftover containers or networks from previous attempts
- [ ] Terminal theme is consistent with other videos
- [ ] Audio levels are tested

---

*Script Version: 1.0.0*
*Last Updated: 2025-01-03*
*Constitutional Hash: cdd01ef066bc6cf2*
