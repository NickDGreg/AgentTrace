AgentTrace is a benchmark, not an agent.
This repository defines environments, tasks, and evaluation used to test external agents or crawlers.

Project purpose

AgentTrace provides a reproducible way to evaluate whether an automated agent can:
	•	interact with deceptive online platforms
	•	navigate realistic login and navigation flows
	•	extract hidden financial endpoints (e.g. deposit addresses)
	•	do so reliably across site variants

The benchmark exists to support:
	•	regression testing of crawlers or agents
	•	controlled experimentation
	•	future public benchmarking

⸻

What this repository contains

Agents should assume this repository will contain:
	•	Synthetic websites
	•	containerised (e.g. Docker)
	•	intentionally designed to mimic scam-site patterns
	•	deterministic and reproducible
	•	Task definitions
	•	declarative (data, not code)
	•	specify start URLs, credentials, and expected artifacts
	•	Evaluation logic
	•	compares agent output to ground truth
	•	produces deterministic success/failure signals

⸻

What this repository does NOT contain

Agents should NOT assume this repository includes:
	•	an agent implementation
	•	a crawler implementation
	•	LLM prompts or policies
	•	production scraping logic
	•	real scam-site data

External agents interact with AgentTrace as black-box environments.

⸻

Core principles to follow

When modifying or adding to this repository:
	1.	Environment-first
	•	Define websites and tasks independently of any agent design.
	2.	Determinism
	•	Synthetic sites and tasks must behave predictably across runs.
	3.	Test-driven development (TDD)
	•	Use tests as the primary specification of behaviour.
	•	Add or update tests before implementing benchmark logic.
	•	Tests should define contracts for schemas, scoring, runner behaviour, and site stability.
	4.	Implementation agnosticism
	•	Do not assume Playwright, Selenium, BrowserGym, or any specific toolchain.
	•	Any agent capable of browser interaction should be able to run tasks.
	5.	No side channels
	•	Agents should not be able to access ground truth via source inspection or backend shortcuts.
	6.	Minimal realism, not maximal fidelity
	•	Include only complexity that reflects real scam-site failure modes.

⸻

Agent interaction model (conceptual)

Agents interacting with AgentTrace are expected to:
	•	receive a start URL (and credentials, if required)
	•	interact with the site using browser automation of their choice
	•	decide when they are finished
	•	output extracted artifacts in a structured format

AgentTrace evaluates only the final output, not internal reasoning.

⸻

Scope boundaries

AgentTrace explicitly focuses on:
	•	web-based interaction
	•	post-login navigation
	•	extraction after interaction

It explicitly does not attempt to cover:
	•	CAPTCHA solving
	•	social engineering
	•	off-platform communication
	•	real-time fraud detection

⸻

Future compatibility

This repository may later include:
	•	adapters for standard agent interfaces (e.g. BrowserGym-style)
	•	richer metrics beyond binary success
	•	additional site families and task classes

Agents should not hard-code assumptions that prevent such extensions.

⸻

If unsure

If an agent is uncertain whether a change belongs here, default to:
	•	keeping the benchmark smaller and cleaner
	•	pushing agent-specific logic outside this repository

⸻

Python conventions
	•	Use Python 3.11+ and uv for dependency management and running commands.
	•	Keep benchmark logic in the agenttrace package; keep environments in sites/; keep tasks as data in tasks/.
	•	Prefer small, typed functions and clear dataclasses/Pydantic models for task schemas.
	•	Write/extend tests first for schema, scoring, and runner behaviour (contract-driven development).
	•	Avoid adding heavy frameworks unless necessary; keep the harness lightweight and deterministic.
