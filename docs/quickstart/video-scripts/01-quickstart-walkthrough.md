# Video Script: ACGS-2 Quickstart Walkthrough

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

## Video Metadata

| Property | Value |
|----------|-------|
| **Title** | ACGS-2 Quickstart: From Zero to First Policy Evaluation |
| **Duration** | 8-10 minutes |
| **Target Audience** | Developers new to ACGS-2 and AI governance |
| **Prerequisites** | Viewers should have Docker and Git installed |
| **Outcome** | Viewer completes first policy evaluation |

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

---

## Script

### [00:00] Introduction (30 seconds)

**VISUAL**: ACGS-2 logo with title "Quickstart Walkthrough"

**VOICEOVER**:
> Welcome to the ACGS-2 Quickstart Walkthrough! In the next 8 minutes, you'll go from zero to your first AI governance policy evaluation.
>
> ACGS-2 is an enterprise-grade AI governance platform that uses the Open Policy Agent to enforce constitutional compliance for AI systems.
>
> By the end of this video, you'll have a running ACGS-2 environment and understand how to evaluate governance policies.

**ACTION**: Show quick preview of the end result (curl command returning policy result)

---

### [00:30] Prerequisites Check (1 minute)

**VISUAL**: Terminal window with prerequisite check script

**VOICEOVER**:
> Before we start, let's verify you have the required software installed.

**ACTION**: Run the prerequisite check script

```bash
# Show the commands being typed
docker --version
docker compose version
git --version
python3 --version
```

**VOICEOVER**:
> You need Docker 24 or later, Docker Compose 2.20 or later, Git, and Python 3.11 or later.
>
> If Docker isn't running, start Docker Desktop now.

**ACTION**: Show successful output for each command

**CALLOUT**: Add annotation pointing to version numbers

---

### [01:30] Clone Repository (45 seconds)

**VISUAL**: Terminal window

**VOICEOVER**:
> Let's clone the ACGS-2 repository from GitHub.

**ACTION**: Type and execute:

```bash
git clone https://github.com/dislovelhl/acgs2.git
cd ACGS-2
ls -la
```

**VOICEOVER**:
> We've cloned the repository and can see the project structure. Notice the docker-compose files, the docs folder, and the examples directory.

**CALLOUT**: Highlight important directories:
- `docker-compose.dev.yml` - Docker configuration
- `docs/` - Documentation
- `examples/` - Example projects

---

### [02:15] Configure Environment (30 seconds)

**VISUAL**: Terminal window, then briefly show .env.dev contents

**VOICEOVER**:
> ACGS-2 uses environment variables for configuration. We'll copy the development defaults.

**ACTION**: Type and execute:

```bash
cp .env.dev .env
cat .env | head -20
```

**VOICEOVER**:
> The .env.dev file includes pre-configured settings for local development, including service URLs, ports, and the constitutional hash for governance validation.

**CALLOUT**: Highlight `CONSTITUTIONAL_HASH=cdd01ef066bc6cf2`

---

### [02:45] Start Services (1 minute)

**VISUAL**: Terminal window with Docker Compose output

**VOICEOVER**:
> Now for the exciting part - let's start all ACGS-2 services with a single command.

**ACTION**: Type and execute:

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev up -d
```

**VOICEOVER**:
> Docker Compose is now pulling images and starting containers. This might take a minute on first run.

**ACTION**: Wait for completion, show output:

```
[+] Running 6/6
 ✔ Container acgs2-zookeeper-1  Started
 ✔ Container acgs2-redis-1      Started
 ✔ Container acgs2-opa-1        Started
 ✔ Container acgs2-kafka-1      Started
 ✔ Container acgs2-agent-bus-1  Started
```

**VOICEOVER**:
> All services are now running. Let's verify they're healthy.

**ACTION**: Type and execute:

```bash
docker compose -f docker-compose.dev.yml ps
```

**CALLOUT**: Highlight "running" status for each service

---

### [03:45] Verify OPA Health (30 seconds)

**VISUAL**: Terminal window

**VOICEOVER**:
> The Open Policy Agent is the heart of ACGS-2's policy evaluation. Let's check it's responding.

**ACTION**: Type and execute:

```bash
curl -s http://localhost:8181/health | python3 -m json.tool
```

**VOICEOVER**:
> An empty JSON response means OPA is healthy and ready to evaluate policies.

**ACTION**: Show the output `{}`

---

### [04:15] Your First Policy Query (1.5 minutes)

**VISUAL**: Terminal window with command and output

**VOICEOVER**:
> Now let's evaluate your first governance policy. We'll query the constitutional policy, which is the foundation of ACGS-2 governance.

**ACTION**: Type and execute:

```bash
curl -s -X POST http://localhost:8181/v1/data/acgs/constitutional/allow \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "constitutional_hash": "cdd01ef066bc6cf2",
      "tenant_id": "my-tenant",
      "features": []
    }
  }' | python3 -m json.tool
```

**VOICEOVER**:
> We're sending a POST request to OPA with our input data. The key fields are:
> - constitutional_hash: the cryptographic fingerprint of our governance rules
> - tenant_id: for multi-tenant isolation
> - features: list of features being used

**ACTION**: Show output:

```json
{
    "result": true
}
```

**VOICEOVER**:
> Result is true - our request passed constitutional validation!

**CALLOUT**: Add "SUCCESS!" annotation

---

### [05:45] Test a Policy Violation (1 minute)

**VISUAL**: Terminal window

**VOICEOVER**:
> What happens when we violate the policy? Let's try with a wrong constitutional hash.

**ACTION**: Type and execute:

```bash
curl -s -X POST http://localhost:8181/v1/data/acgs/constitutional/allow \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "constitutional_hash": "wrong_hash",
      "tenant_id": "my-tenant",
      "features": []
    }
  }' | python3 -m json.tool
```

**ACTION**: Show output:

```json
{
    "result": false
}
```

**VOICEOVER**:
> Result is false - the policy denied our request because the hash doesn't match.

**ACTION**: Query for violation details:

```bash
curl -s -X POST http://localhost:8181/v1/data/acgs/constitutional/violation \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "constitutional_hash": "wrong_hash",
      "tenant_id": "my-tenant",
      "features": []
    }
  }' | python3 -m json.tool
```

**ACTION**: Show output:

```json
{
    "result": [
        "Constitutional hash mismatch or deprecated features detected"
    ]
}
```

**VOICEOVER**:
> The violation rule tells us exactly why the request was denied. This is crucial for debugging policy issues.

---

### [06:45] Python Client Example (1 minute)

**VISUAL**: Split screen - code editor and terminal

**VOICEOVER**:
> For real applications, you'll query OPA from code. Here's a simple Python example.

**ACTION**: Show the Python code:

```python
import requests

OPA_URL = "http://localhost:8181"

def evaluate_policy(policy_path, input_data):
    response = requests.post(
        f"{OPA_URL}/v1/data/{policy_path}",
        json={"input": input_data}
    )
    return response.json()

result = evaluate_policy("acgs/constitutional/allow", {
    "constitutional_hash": "cdd01ef066bc6cf2",
    "tenant_id": "demo-tenant",
    "features": []
})

print(f"Decision: {'ALLOW' if result.get('result') else 'DENY'}")
```

**VOICEOVER**:
> The pattern is simple: POST to OPA with your input wrapped in an "input" key, and check the result.

---

### [07:45] Next Steps (45 seconds)

**VISUAL**: Documentation pages and example directories

**VOICEOVER**:
> Congratulations! You've just completed your first ACGS-2 policy evaluation. Here's what to explore next:

**ACTION**: Show file browser navigating to:

1. `examples/01-basic-policy-evaluation/` - Simple RBAC example
2. `examples/02-ai-model-approval/` - AI governance workflow
3. `notebooks/01-policy-experimentation.ipynb` - Interactive Jupyter notebook

**VOICEOVER**:
> Check out the example projects in the examples folder. Each one demonstrates a different governance scenario.
>
> The Jupyter notebooks let you experiment with policies interactively and visualize governance decisions.

---

### [08:30] Cleanup and Closing (30 seconds)

**VISUAL**: Terminal window, then ACGS-2 logo

**VOICEOVER**:
> When you're done experimenting, you can stop the services with:

**ACTION**: Type:

```bash
docker compose -f docker-compose.dev.yml down
```

**VOICEOVER**:
> Thanks for watching! Check out the documentation at docs/quickstart for the full written guide, and don't forget to share your feedback.
>
> Happy governing!

**VISUAL**: End screen with:
- Link to documentation
- Link to feedback form
- ACGS-2 logo

---

## Chapter Markers

For YouTube or video platforms that support chapters:

```
0:00 Introduction
0:30 Prerequisites Check
1:30 Clone Repository
2:15 Configure Environment
2:45 Start Services
3:45 Verify OPA Health
4:15 Your First Policy Query
5:45 Test a Policy Violation
6:45 Python Client Example
7:45 Next Steps
8:30 Cleanup and Closing
```

---

## Post-Production Checklist

- [ ] Add ACGS-2 intro/outro branding
- [ ] Add chapter markers
- [ ] Add captions/subtitles
- [ ] Add on-screen annotations for key commands
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
- `docs/quickstart/README.md` - Video Tutorials section
- `README.md` - Add video badge

---

*Script Version: 1.0.0*
*Last Updated: 2025-01-03*
*Constitutional Hash: cdd01ef066bc6cf2*
