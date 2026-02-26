# AGENTS

This file is intentionally short.
Its job is to route agents to the right source of truth, not to duplicate all project docs.

## Identity and boundaries

AgentTrace is a benchmark harness, not an agent implementation.

Hard boundaries:
- do not add agent-specific crawling logic to this repo
- preserve determinism in sites, tasks, and scoring
- treat synthetic sites as black-box environments for external agents
- avoid side channels that leak ground truth

## First commands

From repository root:
- `make check`
- `make test-fast`
- `python -m agenttrace.run --tasks-file tasks/tasks.yaml --task-id simple-static-btc --agent-cmd "python tools/dummy_agent.py"`

For isolated parallel runs:
- `python -m agenttrace.run_isolated --tasks-file tasks/tasks.yaml --task-id simple-static-btc --agent-cmd "python tools/dummy_agent.py"`

For UI and traces:
- `python tools/ui_snapshot.py --url <url> --out results/ui/<name>.png --full-page`
- `python tools/compose_logs.py --compose-file <compose.yaml> --out results/traces/<name>.log`

## Docs map

Read in this order:
1. `ARCHITECTURE.md` (bird's-eye overview and codemap)
2. `docs/index.md` (docs table of contents)
3. `docs/DESIGN.md` and `docs/design-docs/*` (design intent)
4. `docs/product-specs/*` (workflow and product expectations)
5. `docs/RELIABILITY.md`, `docs/SECURITY.md`, `docs/QUALITY_SCORE.md` (operational standards)
6. `docs/PLANS.md` + `docs/exec-plans/*` (complex work planning and history)
7. `docs/generated/*` and `docs/references/*` (generated facts and implementation references)

Detailed legacy guidance moved here:
- `docs/references/agenttrace-agent-manual.md`

## Planning rule

If work is complex or a significant refactor, create/update an ExecPlan in:
- `docs/exec-plans/active/`

And keep it aligned with:
- `docs/PLANS.md`

## Quality gates

Before finishing substantial changes, run:
- `make check`
- `python -m agenttrace.scaffolding_checks`

## Approved no-approval commands

- `uv run pytest`
- `uv lock`
- `uv sync`
- `make test`
- `make check`
- `docker compose`
- `curl`
