# Interactive Jupyter Notebooks

Hands-on Jupyter notebooks for learning AI governance with ACGS-2. These notebooks provide interactive policy experimentation, visualization tools, and guided tutorials for understanding OPA policy evaluation.

## Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
# From project root
docker compose up jupyter -d

# Access Jupyter at http://localhost:8888
# Default: No token required (development mode)
```

### Option 2: Local Python Environment

```bash
cd notebooks

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Start Jupyter Notebook
jupyter notebook
```

## Available Notebooks

| Notebook | Description | Prerequisites |
|----------|-------------|---------------|
| `01-policy-experimentation.ipynb` | Interactive policy queries with OPA | OPA running on port 8181 |
| `02-governance-visualization.ipynb` | Visualize policy decisions and approval rates | OPA + matplotlib |

## Prerequisites

Before running the notebooks, ensure:

1. **OPA is running** - Either via Docker Compose or locally on port 8181
2. **Python dependencies installed** - See `requirements.txt`

### Verify OPA is Running

```bash
curl http://localhost:8181/health
# Expected: {"status":"ok"}
```

## Environment Configuration

### Docker Environment Variables

When running via Docker Compose, these environment variables are pre-configured:

| Variable | Value | Description |
|----------|-------|-------------|
| `OPA_URL` | `http://opa:8181` | OPA service URL (Docker network) |
| `MPLBACKEND` | `Agg` | Headless matplotlib backend |
| `JUPYTER_ENABLE_LAB` | `yes` | Enable JupyterLab interface |

### Local Environment Variables

For local development, configure:

```bash
export OPA_URL="http://localhost:8181"
export MPLBACKEND="Agg"  # Optional: for headless rendering
```

## Notebook Structure

Each notebook follows a consistent structure:

```python
# Cell 1: Setup and imports
import os
os.environ["MPLBACKEND"] = "Agg"  # Headless matplotlib (Docker)
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import requests
%matplotlib inline

# Cell 2: OPA connection
OPA_URL = os.getenv("OPA_URL", "http://localhost:8181")

def evaluate_policy(policy_path: str, input_data: dict) -> dict:
    """Query OPA policy with input data."""
    response = requests.post(
        f"{OPA_URL}/v1/data/{policy_path}",
        json={"input": input_data}
    )
    response.raise_for_status()
    return response.json()

# Cell 3: Define policy inputs
input_data = {
    "user": {"role": "admin"},
    "action": "read",
    "resource": "policy"
}

# Cell 4: Evaluate and visualize
result = evaluate_policy("hello/allow", input_data)
print(f"Decision: {'Allowed' if result.get('result') else 'Denied'}")

# Always close figures to prevent memory leaks
plt.close()
```

## Key Patterns

### Querying OPA Policies

```python
import requests

OPA_URL = "http://localhost:8181"  # or "http://opa:8181" in Docker

def evaluate_policy(policy_path: str, input_data: dict) -> dict:
    """Query OPA policy with input data."""
    response = requests.post(
        f"{OPA_URL}/v1/data/{policy_path}",
        json={"input": input_data}
    )
    response.raise_for_status()
    return response.json()

# Example usage
result = evaluate_policy("hello/allow", {"user": {"role": "admin"}})
```

### Visualization Best Practices

```python
import matplotlib.pyplot as plt
import seaborn as sns

# Create visualizations
fig, ax = plt.subplots(figsize=(10, 6))
sns.barplot(x=categories, y=values, ax=ax)
ax.set_title("Policy Decision Distribution")
plt.tight_layout()
plt.show()

# IMPORTANT: Close figures to prevent memory leaks in Docker
plt.close(fig)
```

### Error Handling

```python
from requests.exceptions import RequestException

def safe_evaluate(policy_path: str, input_data: dict) -> dict | None:
    """Evaluate policy with error handling."""
    try:
        return evaluate_policy(policy_path, input_data)
    except RequestException as e:
        print(f"OPA connection error: {e}")
        print("Ensure OPA is running: docker compose up opa -d")
        return None
```

## Troubleshooting

### Jupyter Won't Start

```bash
# Check if port 8888 is in use
lsof -i :8888

# Use alternative port
jupyter notebook --port=8889
# Or via Docker: JUPYTER_PORT=8889 docker compose up jupyter
```

### OPA Connection Refused

```bash
# Verify OPA is running
docker compose ps opa
# Expected: opa service running (healthy)

# Restart OPA service
docker compose restart opa
```

### Matplotlib Display Issues

```python
# In Docker, ensure headless backend is set
import os
os.environ["MPLBACKEND"] = "Agg"
import matplotlib.pyplot as plt
%matplotlib inline  # Required for inline display
```

### Memory Issues with Large Visualizations

```python
# Always close figures after displaying
plt.close('all')  # Close all figures

# Or close specific figure
fig, ax = plt.subplots()
# ... plotting code ...
plt.show()
plt.close(fig)  # Close this figure
```

### Kernel Dies Unexpectedly

```bash
# Increase Docker memory limit
# In Docker Desktop: Settings > Resources > Memory > 4GB+

# Or run notebooks locally with sufficient RAM
```

## Dependencies

See `requirements.txt` for the full list. Key dependencies:

- **notebook>=7.0.0** - Jupyter Notebook server (v7.x for modern features)
- **ipykernel>=6.0.0** - Python kernel for Jupyter
- **matplotlib>=3.0.0** - Plotting and visualization
- **seaborn>=0.12.0** - Statistical visualizations
- **pandas>=2.0.0** - Data manipulation
- **requests>=2.31.0** - HTTP client for OPA queries
- **ipywidgets>=8.0.0** - Interactive widgets (optional)

## Related Resources

- [Quickstart Guide](../docs/quickstart/README.md) - Get started with ACGS-2 in under 30 minutes
- [Example Projects](../examples/) - Working examples of AI governance scenarios
- [OPA Documentation](https://www.openpolicyagent.org/docs/) - Official OPA docs
- [Rego Language Reference](https://www.openpolicyagent.org/docs/latest/policy-language/) - Rego syntax and features

## Contributing

When adding new notebooks:

1. Follow the notebook structure outlined above
2. Include markdown cells explaining each step
3. Add error handling for OPA connections
4. Close all matplotlib figures to prevent memory leaks
5. Test in Docker environment before committing
6. Update this README with notebook description

---

## Video Tutorial

Learn to use the Jupyter notebooks with our step-by-step video tutorial.

### Available Video

| Video | Duration | Description |
|-------|----------|-------------|
| [Interactive Policy Experimentation](#video-placeholder) | 8-10 min | Complete walkthrough of both notebooks |

<!-- VIDEO_PLACEHOLDER: Replace with actual video embed after recording
<iframe width="560" height="315" src="https://www.youtube.com/embed/VIDEO_ID"
        title="ACGS-2 Jupyter Notebooks Tutorial" frameborder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen></iframe>
-->

### What You'll Learn

1. **Starting Jupyter** - Launch notebooks via Docker Compose
2. **Policy Queries** - Query OPA policies interactively from Python
3. **Debugging** - Use denial reasons to troubleshoot policy issues
4. **Visualization** - Create heatmaps and dashboards of governance data
5. **Experimentation** - Modify inputs and see results in real-time
6. **Best Practices** - Memory management and Docker compatibility

### Video Production Status

| Video | Script | Status |
|-------|--------|--------|
| Jupyter Notebook Tutorial | [View Script](../docs/quickstart/video-scripts/03-jupyter-notebook-tutorial.md) | Pending Recording |

> **Note**: The video script is complete and ready. Actual recording requires screen capture, voiceover, and post-production. See the [Video Production Guide](../docs/quickstart/video-scripts/README.md) for recording instructions.

### Quick Preview

While the video is being produced, here's what to expect:

```python
# Query OPA policies interactively
result = evaluate_policy("hello/allow", {
    "user": {"role": "admin"},
    "action": "delete",
    "resource": "policy"
})
print(f"Decision: {'ALLOWED' if result.get('result') else 'DENIED'}")

# Visualize policy decisions with matplotlib
fig, ax = plt.subplots()
sns.heatmap(policy_matrix, annot=True, cmap="RdYlGn", ax=ax)
ax.set_title("Role vs Action Access Matrix")
plt.show()
plt.close(fig)  # Always close to prevent memory leaks!
```
