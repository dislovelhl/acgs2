# Policy Watch Setup Guide

This toolkit provides everything you need to monitor AI regulations across the US and EU.

## 1. Make.com Automation

Set up a scenario to fetch, analyze, and store policy updates.

### Workflow:

1.  **RSS Feed**: Monitor sites like `eur-lex.europa.eu` or `whitehouse.gov`.
2.  **LLM (OpenAI/Claude)**: Use content from `prompts.yaml` to extract structured JSON.
3.  **Database**: Push to Notion or Airtable (see sections below).
4.  **Notifications**: Send `Critical` alerts to Slack/Teams.
5.  **Task Management**: Create Jira tickets for items with deadlines < 30 days.

---

## 2. Notion Setup

1.  Create a new Database.
2.  Import `import_template.csv` to automatically set up all properties (Title, Authority, Jurisdiction, etc.).
3.  Create a "Urgent" view filtered by `Deadline ≤ 7 days` or `Severity = Critical`.

---

## 3. Airtable Setup

1.  Create a new Base.
2.  Import `import_template.csv`.
3.  Configure **Interfaces** for an executive dashboard.
4.  Set up an automation to color records red when `Severity` is `Critical`.

---

## 4. Jira Ticket Templates

When a policy requires action, use these templates for Jira issues:

### High-Priority Action Item

**Summary**: `REGULATORY ACTION REQUIRED: [Title] - [Authority]`
**Description**:

- **Jurisdiction**: {Jurisdiction}
- **Deadline**: {Deadline}
- **Impact Summary**: {Impact Notes}
- **Source**: {Source URL}

**Task Checklist**:

- [ ] Perform impact assessment on core services.
- [ ] Update Policy Registry with new rules.
- [ ] Verify constitutional compliance with new constraints.

---

## 5. Programmatic Usage

You can load the prompts in your research experiments:

```python
import yaml

with open('policy-watch/prompts.yaml', 'r') as f:
    prompts = yaml.safe_load(f)

# Use prompts['eu_ai_act']['user'].replace('{{ARTICLE_BODY}}', body)
```
