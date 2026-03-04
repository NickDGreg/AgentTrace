# AgentTrace Architecture

## Bird's-Eye Overview

AgentTrace solves one problem: evaluate external web agents against deterministic, synthetic scam-like websites using a stable input/output contract.

The benchmark has three responsibilities:
- define tasks as data
- run those tasks against an external agent process
- score the returned artifacts against deterministic ground truth

AgentTrace intentionally does not implement an agent. It provides reproducible environments and a harness.

## Runtime Flow

1. Task definitions are loaded from `tasks/tasks.yaml`.
2. The runner starts one synthetic site stack at a time with Docker Compose.
3. The runner invokes an external agent command with task context in environment variables.
4. The agent returns JSON on stdout.
5. AgentTrace validates output, loads expected artifacts, scores results, and writes machine-readable output to `results/*.json`.

## Layered Model

The repository enforces a lightweight layer contract for benchmark code:
- Types
- Config
- Repo
- Service
- Runtime
- UI

Current mapping in the Python harness:
- `agenttrace.tasks`, `agenttrace.output`, `agenttrace.scoring`: Types
- `agenttrace.ground_truth`: Repo
- `agenttrace.run`, `agenttrace.run_isolated`: Runtime

Dependency direction is checked mechanically by `agenttrace.scaffolding_checks`.

## Codemap: Where Is X?

### Core harness package

- `agenttrace/tasks.py`
  - Loads and validates task and suite YAML.
  - Owns the `Task` schema used by the runner.

- `agenttrace/output.py`
  - Validates agent stdout against the output contract.

- `agenttrace/scoring.py`
  - Compares expected artifacts to extracted artifacts.

- `agenttrace/ground_truth.py`
  - Loads expected artifacts from site SQLite databases.

- `agenttrace/run.py`
  - Primary CLI runner (`python -m agenttrace.run`).
  - Starts/stops Docker Compose stacks, executes agents, writes results.

- `agenttrace/run_isolated.py`
  - Isolation wrapper runner (`python -m agenttrace.run_isolated`).
  - Rewrites compose host ports to ephemeral values for parallel isolated runs.

- `agenttrace/scaffolding_checks.py`
  - Custom structural checks: layer import direction, file size limits, dataclass naming, print restrictions.

### Sites (synthetic environments)

- `sites/simple_static/`
  - Minimal static HTML benchmark site.

- `sites/login_deposit_basic/`
  - Deterministic login flow with deposit address extraction.

- `sites/register_basic/`
  - Registration + login + deposit navigation flow.

- `sites/site_one/`
  - Multi-page scam-style UX with richer templates and generated addresses.

- `sites/crawl_test/`
  - `site_one`-derived flow for crawler development where pages remain accessible without login gating.

Each site family includes a `compose.yaml` and image build files for reproducible startup.

### Tasks and suites

- `tasks/tasks.yaml`
  - Canonical task catalog.

- `tasks/suites/*.yaml`
  - Named subsets for smoke/regression runs.

### Tests

- `tests/test_output_contract.py`
  - Output validation contract tests.

- `tests/test_tasks_suites.py`
  - Task/suite schema tests.

- `tests/test_runner.py`, `tests/test_runner_results_json.py`
  - Runner behavior and results serialization tests.

- `tests/test_*_site.py`
  - Synthetic site behavior tests.

- `tests/test_scaffolding_checks.py`
  - Mechanical architecture/scaffolding guard test.

### Tools

- `tools/dummy_agent.py`
  - HTTP-only dummy extractor for quick harness verification.

- `tools/dummy_agent_login.py`
  - Login-capable dummy extractor.

- `tools/ui_snapshot.py`
  - Playwright-based screenshot probe for UI visibility in agent workflows.

- `Makefile`
  - Standardized developer and agent commands (`test`, `check`, `run-isolated`, `ui-snapshot`).

### Project knowledge base

- `docs/`
  - Design docs, product specs, reliability/security standards, exec plans, generated schema notes.

- `AGENTS.md`
  - Agent navigation guide and operating instructions.

## Module Relationships

- `run.py` orchestrates task loading (`tasks.py`), output parsing (`output.py`), artifact scoring (`scoring.py`), and optional DB truth loading (`ground_truth.py`).
- `run_isolated.py` is an orchestration wrapper around `run.py`; it does not alter scoring logic.
- Synthetic sites are black-box targets for external agents and are referenced only by task metadata.

## Non-Goals in Architecture

- No internal browser automation engine in core harness.
- No dependency on a specific external agent framework.
- No runtime shortcuts to reveal ground truth to the external agent.
