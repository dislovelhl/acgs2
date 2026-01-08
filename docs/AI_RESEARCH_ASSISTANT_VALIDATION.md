# AI Research Assistant Validation & Verification Guide

> **Constitutional Hash**: `cdd01ef066bc6cf2`
> **Last Updated**: 2026-01-04

## TL;DR

Use this guide to make research assistance reliable, transparent, and auditable. Validation ensures inputs and outputs meet quality standards; verification ensures claims match authoritative evidence. Always cite sources, separate facts from hypotheses, and include confidence levels.

## Scope

This guidance applies to research-oriented agent workflows, including literature reviews, data synthesis, research overviews, and gap analysis.

## Definitions

| Term | Meaning | Outcome |
| --- | --- | --- |
| **Validation** | Ensure inputs, methods, and outputs meet defined quality standards | Consistent, high-quality responses |
| **Verification** | Confirm claims against authoritative evidence | Trustworthy, evidence-backed conclusions |

## Core Principles for Research Assistance

1. **Accuracy over speed**: Prefer fewer, higher-quality sources over a large, unverified set.
2. **Authoritative sources first**: Prioritize peer-reviewed papers, official datasets, and standards bodies.
3. **Bias-aware synthesis**: Identify sampling bias, publication bias, and conflicts of interest.
4. **Transparency**: Distinguish established facts, plausible hypotheses, and open questions.
5. **Confidence signaling**: Provide confidence levels for key claims.
6. **Limitations upfront**: State data gaps, design limitations, and uncertainty.
7. **Continuous updates**: Revalidate conclusions when new evidence emerges.
8. **Cross-referencing**: Use multiple independent sources for high-impact claims.
9. **Contextual awareness**: Tailor scope to user goals, constraints, and domain.
10. **Feedback loops**: Capture user corrections and integrate into future guidance.

## Evidence Quality Ladder

| Tier | Evidence Type | Example Use | Verification Notes |
| --- | --- | --- | --- |
| **Tier 1** | Peer-reviewed studies, official datasets | Primary claims | Require multiple sources and methods review |
| **Tier 2** | Government/standards publications | Regulatory or safety claims | Prefer latest versions |
| **Tier 3** | Reputable preprints, reputable labs | Emerging findings | Label as preliminary and re-check later |
| **Tier 4** | Blogs, opinion pieces | Background context | Use only for framing, not for core claims |

## Validation Workflow

### 1. Intake Validation

- Confirm the research question, scope, and domain.
- Capture constraints (time window, region, population, modality).
- Define output format (summary, table, annotated bibliography).

### 2. Search and Retrieval Validation

- Use **customizable search parameters**:
  - Time window (e.g., 2019–2026)
  - Study type (RCTs, meta-analyses, longitudinal)
  - Population or region
  - Source type (peer-reviewed, dataset, standards)
- Log search parameters for reproducibility.

### 3. Study Design Validation

Check for:
- Study type (RCT, cohort, case-control, simulation).
- Sample size and power considerations.
- Confounders, controls, and selection bias.
- Statistical methods appropriateness (e.g., regression assumptions, p-hacking risk).

### 4. Synthesis Validation

- Group findings by methodology and outcome.
- Note divergent findings and potential causes (measurement differences, demographics).
- Identify consensus vs. controversy.

## Verification Workflow

### 1. Claim-to-Source Mapping

For each key claim:
- Attach at least one **authoritative citation**.
- Cross-check with an independent source when stakes are high.

### 2. Fact vs. Hypothesis Labeling

| Label | Use When | Example |
| --- | --- | --- |
| **Established Fact** | Replicated evidence or strong consensus | “Multiple meta-analyses show…” |
| **Supported Hypothesis** | Limited but credible evidence | “Early trials suggest…” |
| **Open Question** | Evidence insufficient or contradictory | “No conclusive evidence on…” |

### 3. Confidence Levels

| Level | Criteria | Guidance to Users |
| --- | --- | --- |
| **High** | Multiple independent sources, robust methods | Safe to act on with minimal risk |
| **Medium** | Some evidence, minor limitations | Use with caution; monitor updates |
| **Low** | Sparse or conflicting evidence | Treat as exploratory |

### 4. Cross-Verification Checklist

- Verify dataset provenance and version.
- Confirm statistical claims (effect sizes, confidence intervals).
- Validate that conclusions align with reported results.
- Check for retractions or corrections.

## Output Requirements

Every research response should include:

1. **Summary** of findings.
2. **Evidence table** with citations.
3. **Confidence levels** for key claims.
4. **Limitations** and open questions.
5. **Next steps** for deeper verification if needed.

## Evidence Table Template

| Claim | Evidence | Source Type | Confidence | Notes |
| --- | --- | --- | --- | --- |
| | | | | |

## Communicating Limitations

- Specify data gaps or missing populations.
- Call out assumptions and proxy measures.
- Highlight statistical or methodological constraints.

## Update and Revalidation Cadence

- **Critical domains** (health, safety, policy): revalidate quarterly.
- **Fast-moving domains** (LLM evals, cybersecurity): revalidate monthly.
- **Stable domains**: revalidate annually or when new benchmarks appear.

## User Feedback and Continuous Improvement

- Track user corrections and resolved disputes.
- Update source lists when new authoritative datasets appear.
- Maintain a changelog of updates to findings.

## Quick Checklists

### Validation Checklist

- [ ] Scope and constraints captured
- [ ] Search parameters recorded
- [ ] Study design assessed
- [ ] Synthesis grouped by methodology

### Verification Checklist

- [ ] Every key claim has citations
- [ ] Facts and hypotheses labeled
- [ ] Confidence levels assigned
- [ ] Limitations documented
- [ ] Cross-verification completed for high-impact claims
