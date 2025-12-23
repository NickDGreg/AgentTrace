# Development Log

## Stage 0
- **Step 0.1**: Bootstrapped the Python/uv scaffold, added package metadata, and ensured `uv run python -c "print('ok')"` works using `.venv`.
- **Step 0.2**: Defined the agent-output JSON contract, wired up `validate_agent_output`, documented the schema, and added tests.
- **Step 0.3**: Built the `sites/simple_static` synthetic site with Docker Compose; verified it serves the deterministic BTC address.
- **Step 0.4**: Created `tasks/tasks.yaml`, introduced the `Task` loader, and documented the declarative task format.
- **Step 0.5**: Implemented `score_artifacts` and contract tests for pass/fail diffs.
- **Step 0.6**: Added the runner CLI (`python -m agenttrace.run`) that orchestrates Docker, agent execution, validation, and scoring.
- **Step 0.7**: Built `tools/dummy_agent.py` plus tests, enabling smoke runs without a real crawler.
- **Step 0.8**: Ensured contract-focused pytest suite (validator, tasks, scorer, runner helpers, dummy agent) runs quickly via `uv run pytest`.

## Stage 1
- **Step 1.1**: Hardened task loading for multi-task files (duplicate-id validation + clearer errors) and added multi-task fixture data.
- **Step 1.2**: Added suite data files (`tasks/suites/*.yaml`) and CLI `--suite` selection; documented smoke usage.
- **Step 1.3**: Updated the runner to execute multiple tasks in a single invocation, grouped by compose file, with per-task status and summary counts.
- **Step 1.4**: Added results JSON output (`--results-file`) with metadata, per-task results, timings, and summary counts.
- **Step 1.5**: Standardized stdout task lines (`PASS|FAIL|ERROR <task_id>`) with a final totals line.
- **Step 1.6**: Added tests for multi-task loading, duplicate-id failures, and suite selection/missing suite errors.
- **Step 1.7**: Added a runner contract test that validates results JSON output without Docker.

## Stage 2
- **Step 2.1**: Added `login_deposit_basic` site scaffold (Flask app + Docker compose) on port 18081.
- **Step 2.2**: Implemented login, dashboard, and deposit routes with session auth and redirects.
- **Step 2.3**: Introduced SQLite persistence with user and deposit address tables.
- **Step 2.4**: Added deterministic seeding (bcrypt user + BTC/ETH addresses) and idempotent startup.
- **Step 2.5**: Rendered deposit addresses from the DB for authenticated users.
- **Step 2.6**: Added DB-backed ground truth loading and exposed the DB via a host-mounted volume.
- **Step 2.7**: Added the `login-deposit-basic` task entry with credentials and DB ground truth metadata.
- **Step 2.8**: Added `tools/dummy_agent_login.py` for login-capable extraction and improved agent error reporting.
- **Step 2.9**: Added fast site stability tests for login/deposit flow and seed validation.
