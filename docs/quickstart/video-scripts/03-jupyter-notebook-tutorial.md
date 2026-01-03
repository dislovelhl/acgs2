# Video Script: Jupyter Notebook Tutorial

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

## Video Metadata

| Property | Value |
|----------|-------|
| **Title** | ACGS-2 Jupyter Notebooks: Interactive Policy Experimentation |
| **Duration** | 8-10 minutes |
| **Target Audience** | Data scientists and developers who want interactive policy exploration |
| **Prerequisites** | ACGS-2 running via Docker Compose |
| **Outcome** | Viewer can run notebooks, query OPA interactively, and create visualizations |

## Production Notes

### Recording Setup

- **Resolution**: 1920x1080 (1080p)
- **Frame Rate**: 30fps
- **Audio**: Clear voiceover with minimal background noise
- **Terminal Font**: 14pt minimum for readability
- **Browser**: Use Chrome or Firefox with clean profile
- **Jupyter Theme**: Default light theme for maximum readability

### Style Guidelines

- Keep Jupyter cells large and readable
- Show cell execution with visible output
- Pause after visualizations render to let viewers absorb
- Highlight key code patterns with callouts
- Use consistent pacing (not too fast)
- Add chapter markers for easy navigation
- Show both code and output side-by-side where helpful

---

## Script

### [00:00] Introduction (30 seconds)

**VISUAL**: ACGS-2 logo with title "Interactive Jupyter Notebooks"

**VOICEOVER**:
> Welcome to the ACGS-2 Jupyter Notebook Tutorial! In this video, you'll learn how to interactively experiment with governance policies using Jupyter notebooks.
>
> Jupyter notebooks are perfect for exploring OPA policies, visualizing governance decisions, and understanding how different inputs affect policy outcomes.
>
> By the end of this video, you'll be able to query policies, debug denial reasons, and create beautiful visualizations of governance data.

**ACTION**: Show quick preview of a colorful governance dashboard from Notebook 02

---

### [00:30] Starting Jupyter (1 minute)

**VISUAL**: Terminal window

**VOICEOVER**:
> Let's start by launching Jupyter. Make sure you're in the ACGS-2 project directory.

**ACTION**: Type and execute:

```bash
# Start OPA and Jupyter together
docker compose up opa jupyter -d

# Check services are running
docker compose ps
```

**VOICEOVER**:
> We're starting both OPA and Jupyter. OPA is our policy engine, and Jupyter provides the interactive notebook environment.

**ACTION**: Show output with both services running

**VOICEOVER**:
> Now let's open Jupyter in the browser.

**ACTION**: Open browser to `http://localhost:8888`

```bash
# Or use this command to open automatically
open http://localhost:8888  # macOS
# xdg-open http://localhost:8888  # Linux
```

**VISUAL**: Jupyter file browser showing notebooks directory

**CALLOUT**: Highlight the two notebooks:
- `01-policy-experimentation.ipynb`
- `02-governance-visualization.ipynb`

---

### [01:30] Notebook 01: Policy Experimentation (4 minutes)

**VISUAL**: Jupyter notebook interface

**VOICEOVER**:
> Let's open the first notebook - Policy Experimentation. This teaches you the fundamentals of querying OPA from Python.

**ACTION**: Click to open `01-policy-experimentation.ipynb`

#### Setup and Connection (1 minute)

**VOICEOVER**:
> The notebook starts with setup. Notice we set the matplotlib backend before importing - this is critical for Docker environments.

**ACTION**: Run cells 1-2 (setup and imports)

```python
# Cell 1: Environment setup
import os
os.environ["MPLBACKEND"] = "Agg"  # Required for Docker!
```

**CALLOUT**: Highlight `MPLBACKEND = "Agg"` with annotation: "Critical for Docker!"

**ACTION**: Run cell 3 (OPA connection check)

**VOICEOVER**:
> The notebook verifies OPA is healthy before we start querying. You'll see a green checkmark if everything is working.

**CALLOUT**: Highlight "OPA is healthy!" output

#### Basic Policy Queries (1 minute)

**VOICEOVER**:
> Now let's query some policies. The hello policy implements simple role-based access control.

**ACTION**: Run cells 4-6 (basic queries)

```python
# Admin can do anything
result = evaluate_policy("hello/allow", {
    "user": {"role": "admin"},
    "action": "delete",
    "resource": "policy"
})
```

**VOICEOVER**:
> We're querying the hello/allow rule with an admin user trying to delete a policy. The result is true - allowed!

**ACTION**: Show output: "Admin delete request: ALLOWED"

**ACTION**: Run the developer query

**VOICEOVER**:
> Now a developer trying to delete - denied! Developers can only read.

**ACTION**: Show output: "Developer delete request: DENIED"

**CALLOUT**: Highlight the difference between ALLOWED and DENIED

#### Debugging with Denial Reasons (1 minute)

**VOICEOVER**:
> When requests are denied, you need to know why. The explain_decision function shows us denial reasons.

**ACTION**: Run cells 7-9 (denial reasons)

```python
explain_decision({
    "user": {"role": "guest"},
    "action": "read",
    "resource": "data"
})
```

**VOICEOVER**:
> For a guest user, we see the decision is DENIED with a clear reason: "Unknown role or no permission for action."

**ACTION**: Show the denial reasons output

**CALLOUT**: Highlight "Reasons:" section

**VOICEOVER**:
> This is incredibly useful for debugging. Instead of just knowing something failed, you know exactly why.

#### Visualization (1 minute)

**VOICEOVER**:
> Now let's visualize policy decisions. We'll run batch evaluation across multiple scenarios and create a heatmap.

**ACTION**: Run cells 10-12 (batch evaluation and heatmap)

**VOICEOVER**:
> The heatmap shows role versus action. Green means allowed, red means denied. You can instantly see that admins have full access, developers can only read, and guests are denied everything.

**ACTION**: Pause on heatmap visualization

**CALLOUT**: Add annotations pointing to:
- "admin row - all green (full access)"
- "developer row - only read is green"
- "guest row - all red (no access)"

**VOICEOVER**:
> This visualization makes it easy to verify your policies are working as intended.

---

### [05:30] Notebook 02: Governance Visualization (2 minutes)

**VISUAL**: Jupyter notebook interface

**VOICEOVER**:
> Now let's look at the Governance Visualization notebook. This is where data science meets AI governance.

**ACTION**: Open `02-governance-visualization.ipynb`

#### Dashboard Overview (1 minute)

**VOICEOVER**:
> This notebook generates simulated governance data and creates a comprehensive dashboard.

**ACTION**: Run cells 1-6 (setup and data generation)

**VOICEOVER**:
> We generate 100 model approval records with realistic risk scores, compliance status, and environments.

**ACTION**: Run cell 7 (main dashboard)

**VOICEOVER**:
> Here's the governance dashboard. Six panels showing approval rates, risk distribution, decisions by environment, compliance heatmaps, and key metrics.

**ACTION**: Slowly pan across the dashboard, pausing on each panel

**CALLOUT**: Highlight key insights:
- "Pie chart: Overall approval rate"
- "Histogram: Risk score distribution with thresholds"
- "Heatmap: Risk vs Compliance correlation"

#### Risk and Compliance Analysis (30 seconds)

**ACTION**: Run cells 8-9 (risk distribution and compliance)

**VOICEOVER**:
> The risk analysis uses violin plots and box plots to show how risk varies by environment and model type.

**ACTION**: Pause on violin plot

**VOICEOVER**:
> Notice how production deployments tend to have lower risk - that's because high-risk models get filtered out earlier.

#### Audit Trail (30 seconds)

**ACTION**: Run cells 10-11 (time series)

**VOICEOVER**:
> The audit trail visualization tracks governance decisions over time. You can see daily volume, approval rate trends, and how risk categories change.

**ACTION**: Show time series chart

**VOICEOVER**:
> This is exactly what you'd use for compliance reporting and governance audits.

---

### [07:30] Interactive Experimentation (1 minute)

**VISUAL**: Jupyter notebook with exercise cells

**VOICEOVER**:
> Both notebooks include interactive cells where you can experiment with your own inputs.

**ACTION**: Navigate to the exercise section in Notebook 01

```python
# EXERCISE: Try different role/action combinations
my_input = {
    "user": {"role": "viewer"},  # Try different roles
    "action": "write",           # Try different actions
    "resource": "policy"
}
explain_decision(my_input)
```

**VOICEOVER**:
> Change the role to "viewer", the action to "write", and run the cell. You'll see the denial reason explains exactly why viewers can't write.

**ACTION**: Modify the cell and run it

**ACTION**: Show output with denial reason

**VOICEOVER**:
> This hands-on experimentation is the fastest way to understand how policies work.

---

### [08:30] Best Practices and Cleanup (30 seconds)

**VISUAL**: Code showing best practices

**VOICEOVER**:
> Before we wrap up, a few best practices for working with notebooks in Docker.

**ACTION**: Show the cleanup cell

```python
# Always close figures to prevent memory leaks
plt.close('all')
```

**VOICEOVER**:
> Always close matplotlib figures when you're done. In Docker, memory leaks can cause your kernel to crash.

**ACTION**: Run cleanup cell

**VOICEOVER**:
> Also remember to restart your kernel occasionally if you're running many visualizations.

---

### [09:00] Summary and Next Steps (1 minute)

**VISUAL**: Summary slide

**VOICEOVER**:
> Let's recap what you learned:
>
> Notebook 01 taught you how to query OPA policies, understand denial reasons, and visualize access control decisions.
>
> Notebook 02 showed advanced governance dashboards, risk analysis, and audit trail visualization.

**ACTION**: Show file browser with both notebooks

**VOICEOVER**:
> Use these notebooks as templates for your own governance analysis. You can modify the policies, add your own data sources, and create custom visualizations.

**ACTION**: Show links to resources

**VOICEOVER**:
> For more information, check out the example projects in the examples folder, and the OPA documentation for advanced Rego features.
>
> Thanks for watching! Don't forget to share your feedback.

**VISUAL**: End screen with:
- Link to notebooks/README.md
- Link to example projects
- Feedback form link
- ACGS-2 logo

---

## Chapter Markers

For YouTube or video platforms that support chapters:

```
0:00 Introduction
0:30 Starting Jupyter
1:30 Notebook 01: Policy Experimentation
2:30 Basic Policy Queries
3:30 Debugging with Denial Reasons
4:30 Visualization
5:30 Notebook 02: Governance Visualization
6:30 Risk and Compliance Analysis
7:30 Interactive Experimentation
8:30 Best Practices and Cleanup
9:00 Summary and Next Steps
```

---

## Post-Production Checklist

- [ ] Add ACGS-2 intro/outro branding
- [ ] Add chapter markers
- [ ] Add captions/subtitles
- [ ] Add on-screen annotations for key code patterns
- [ ] Highlight MPLBACKEND setting and plt.close() calls
- [ ] Zoom in on visualizations when they render
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
- `notebooks/README.md` - Video Tutorial section
- `docs/quickstart/README.md` - Link in Jupyter section

---

## Recording Preparation Checklist

Before recording this video:

- [ ] Docker environment is clean (`docker compose down -v && docker system prune -f`)
- [ ] OPA and Jupyter services tested and working
- [ ] Both notebooks run all cells without errors
- [ ] Example 01 policies loaded (for hello/allow queries)
- [ ] Browser zoom level appropriate for 1080p recording
- [ ] Jupyter theme is default light (for readability)
- [ ] Terminal theme consistent with other videos
- [ ] Audio levels tested
- [ ] Notifications disabled

---

## Key Points to Emphasize

1. **MPLBACKEND=Agg**: Critical for Docker - set BEFORE importing matplotlib
2. **plt.close()**: Always close figures to prevent memory leaks
3. **safe_evaluate()**: Use error handling for graceful OPA connection failures
4. **Denial reasons**: The key to debugging policy issues
5. **Interactive cells**: Modify inputs to experiment with policies

---

*Script Version: 1.0.0*
*Last Updated: 2026-01-03*
*Constitutional Hash: cdd01ef066bc6cf2*
