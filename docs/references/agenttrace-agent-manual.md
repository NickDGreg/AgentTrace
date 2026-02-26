# AgentTrace Agent Manual (Detailed)

This document preserves the detailed, long-form guidance previously stored in `AGENTS.md`.
`AGENTS.md` is now intentionally concise and serves as a navigation/control file.

## Project purpose

AgentTrace provides a reproducible way to evaluate whether an automated agent can:
- interact with deceptive online platforms
- navigate realistic login and navigation flows
- extract hidden financial endpoints (for example deposit addresses)
- do so reliably across site variants

The benchmark exists to support:
- regression testing of crawlers or agents
- controlled experimentation
- future public benchmarking

## What this repository contains

Agents should assume this repository will contain:
- synthetic websites
- containerized environments (for example Docker Compose)
- intentionally scam-pattern-like flows
- deterministic/reproducible behavior
- task definitions as declarative data
- evaluation logic that compares agent output to ground truth

## What this repository does not contain

Agents should not assume this repository includes:
- an agent implementation
- a crawler implementation
- LLM prompts or policies
- production scraping logic
- real scam-site data

External agents interact with AgentTrace as black-box environments.

## Core principles

When modifying or adding to this repository:
1. Environment-first: define websites and tasks independently of any agent design.
2. Determinism: synthetic sites and tasks must behave predictably across runs.
3. TDD: tests are the primary specification for schema, scoring, runner behavior, and site stability.
4. Implementation agnosticism: do not require a specific automation stack (Playwright, Selenium, BrowserGym, etc.).
5. No side channels: agents should not obtain ground truth via source/back-end shortcuts.
6. Minimal realism: include only complexity that reflects benchmark-relevant failure modes.

## Agent interaction model

Agents are expected to:
- receive a start URL (and credentials when required)
- interact with the site using browser automation or equivalent tooling
- decide when they are finished
- output extracted artifacts in structured JSON

AgentTrace evaluates only final output, not internal reasoning.

## Agent output contract

Success payload:

```json
{
  "artifacts": {
    "BTC": "bc1qexampleaddress"
  }
}
```

Failure payload:

```json
{
  "error": {
    "message": "Page timed out before login"
  }
}
```

Rules:
- output cannot include both `artifacts` and `error`
- validate with `agenttrace.validate_agent_output`

## Task definitions

AgentTrace exposes tasks as data in `tasks/tasks.yaml`. Each entry specifies:
- `id`
- `site`
- `compose_file`
- `start_url`
- `expected_artifacts`

The runner loads tasks, launches the site, passes URL/credentials context, and scores extracted artifacts.

## Runner interface

Canonical execution:

```bash
python -m agenttrace.run --tasks-file tasks/tasks.yaml --agent-cmd "<your agent command>"
```

The runner:
- starts/stops site stacks via Docker Compose
- sets `AGENTTRACE_START_URL` and `AGENTTRACE_TASK_ID`
- passes credentials via `AGENTTRACE_EMAIL` and `AGENTTRACE_PASSWORD` when present
- captures stdout, validates JSON contract, and reports PASS/FAIL/ERROR

Isolated parallel execution:

```bash
python -m agenttrace.run_isolated --tasks-file tasks/tasks.yaml --task-id <id> --agent-cmd "<your agent command>"
```

This mode rewrites compose host ports to ephemeral ports and runs tasks against temporary isolated compose files.

## Dummy agent

For quick harness checks:

```bash
python tools/dummy_agent.py
```

It fetches the provided URL, extracts a BTC address, and prints a compliant JSON payload.

## Scope boundaries

AgentTrace focuses on:
- web-based interaction
- post-login navigation
- extraction after interaction

AgentTrace does not aim to cover:
- CAPTCHA solving
- social engineering
- off-platform communication
- real-time fraud detection

## Future compatibility

The repository may later include:
- adapters for standard agent interfaces
- richer metrics beyond binary success/failure
- additional site families and task classes

Agents should avoid hard-coded assumptions that block these extensions.

## If unsure

If uncertain whether a change belongs here:
- keep the benchmark smaller and cleaner
- push agent-specific logic outside this repository

## Python conventions

- Use Python 3.11+ and `uv`.
- Keep benchmark logic in `agenttrace/`, environments in `sites/`, tasks in `tasks/`.
- Prefer small, typed functions and clear dataclass/Pydantic models where appropriate.
- Write or extend tests first for schemas, scoring, and runner behavior.
- Keep the harness lightweight and deterministic.
- Run `python -m agenttrace.scaffolding_checks` for structural guardrails.
- Use `python tools/ui_snapshot.py --url <url> --out <path>` for screenshot artifacts.
- Use `python tools/compose_logs.py --compose-file <compose.yaml> --out <path>` for trace logs.

## Approved no-approval commands

- `uv run pytest`
- `uv lock`
- `uv sync`
- `make test`
- `make check`
- `docker compose`
- `curl`
