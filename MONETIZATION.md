# Monetization Strategy

## Goals

- Keep `kfix` easy to adopt as an open-source CLI.
- Monetize team workflows where organizations need control, safety, and compliance.
- Optimize for measurable outcomes: faster MTTR, safer fixes, and better on-call consistency.

## Pricing Tiers

### Free (OSS CLI)

- Local CLI diagnosis (`diagnose`, `scan`, `explain`)
- Local config and local-only usage
- Manual fix execution and basic auto-fix controls

Primary objective:
- Maximize adoption and community trust.

### Pro (Individual)

- Higher usage/model limits
- Advanced scan profiles and richer diagnostics output
- Personal diagnosis history and exports

Primary objective:
- Monetize power users while staying self-serve.

### Team

- Shared diagnosis history
- Team runbooks and approved fix templates
- Approval workflows for risky fix commands
- Slack/Jira integration for incident workflows
- Team-level audit logs and retention controls

Primary objective:
- Land and expand in platform/on-call teams.

### Enterprise

- SSO/SAML, SCIM, and granular RBAC
- Private deployment options (VPC/on-prem)
- Data governance and compliance controls
- SLA and premium support

Primary objective:
- Close high-ACV contracts with security-conscious organizations.

## Packaging Principles

- Free tier should solve real problems, not be crippled.
- Paid tiers should map to organizational needs, not arbitrary lockouts.
- Charge for collaboration, governance, and workflow automation.

## Core Value Proposition

`kfix` should be framed as:
- Incident response acceleration for Kubernetes teams.
- A safer path from diagnosis to action.
- A source of operational consistency across engineers and clusters.

## Success Metrics

- Activation: install to first successful diagnosis.
- Utility: diagnosis-to-fix conversion rate.
- Outcome: MTTR reduction versus team baseline.
- Retention: weekly active on-call usage.
- Expansion: Free/Pro to Team conversion.
- Revenue quality: annual contract growth and churn rate.

## 90-Day Execution Plan

1. Ship Team MVP:
- Shared history
- Team runbooks
- Audit log foundation
- Basic approval gates

2. Run design-partner pilots:
- 5-10 Kubernetes platform teams
- Capture incident case studies with before/after MTTR

3. Convert pilots:
- Publish clear pricing and packaging
- Prioritize enterprise blockers from pilot feedback

## Messaging Pillars

- "From kubectl noise to clear fixes in seconds."
- "Safer AI-assisted troubleshooting for production Kubernetes."
- "Built for on-call teams that need speed and control."
