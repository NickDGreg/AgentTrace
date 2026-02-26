# SECURITY

AgentTrace security model is benchmark-focused.

In-scope controls:
- synthetic-only content and data
- no production credentials or real scam-site data
- explicit task schemas and output contract validation
- no hidden backend channel for external agents to read ground truth

Operational guidance:
- keep secrets out of repository
- avoid adding side-channel endpoints to synthetic sites
- validate all task and output shapes before scoring
- use isolated Compose runs when parallelizing multi-agent experiments

Out-of-scope:
- CAPTCHA solving
- social-engineering resistance
- real-world fraud detection pipelines
