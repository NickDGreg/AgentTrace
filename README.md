# AgentTrace
AgentTrace is a benchmark for evaluating whether automated agents can navigate deceptive online platforms and extract hidden financial endpoints.

It provides a suite of synthetic websites that mimic real scam-site patterns, along with ground-truth evaluation, so agents and crawlers can be tested deterministically and regressions can be detected reliably.

AgentTrace is designed to be:
	•	reproducible
	•	implementation-agnostic (any agent or crawler can be used)
	•	grounded in real-world scam behaviours
	•	extensible toward public benchmarking and research use

What AgentTrace is
	•	A collection of synthetic, containerised websites
	•	Declarative tasks describing what an agent must extract
	•	An evaluation harness that scores agent output against ground truth

What AgentTrace is not
	•	An agent or crawler implementation
	•	A dataset of real scam sites
	•	A production detection system

Intended use
	•	Testing and regression-checking scam-site crawlers or agents
	•	Evaluating generalisation across different deceptive site patterns
	•	Providing a controlled environment for research and benchmarking

### Agent output contract
Agents must emit JSON that either reports extracted artifacts or explains failure:

```json
{
  "artifacts": {
    "BTC": "bc1qexampleaddress",
    "ETH": "0xabc123..."
  }
}
```

On failure, return an error message instead of artifacts:

```json
{
  "error": {
    "message": "Login page never responded"
  }
}
```

`agenttrace.validate_agent_output` loads the JSON, enforces this contract, and returns either the artifacts dictionary or an error string.

### Repo structure (high level)
		•	sites/
Containerised synthetic websites (grouped by “site family” / pattern). Each family is runnable reproducibly (typically via Docker Compose) and seeded deterministically.

		•	tasks/
Declarative task specs (YAML/JSON). Tasks reference a site family plus start URL / credentials and define the expected extracted artifacts at a conceptual level.

	•	tests/
Contract tests that specify behaviour for:
	•	task schema + validation
	•	scoring correctness
	•	runner I/O (external agent invocation + output parsing)
	•	site determinism/health (boot + seeded truth exists)

		•	agenttrace/ (Python package)
Benchmark harness code:
		•	task loading + validation
		•	runner (spin up site, invoke an external agent/crawler, collect output)
		•	scoring (compare output to ground truth; emit clear diffs)

	•	scripts/ (optional)
Convenience commands to run common flows locally (bring up site(s), seed, run smoke suite).

### Simple static site (Stage 0)
The first synthetic site lives in `sites/simple_static/`. It serves a single HTML page containing a deterministic BTC deposit address (`bc1qagenttrace0static0stage000000000000000000`). Run it locally with:

```bash
docker compose -f sites/simple_static/compose.yaml up --build
```

The page becomes available at <http://localhost:18080/>. Tear it down with `docker compose -f sites/simple_static/compose.yaml down`.

### Login + deposit site (Stage 2)
The `sites/login_deposit_basic/` site provides a minimal login → dashboard → deposit flow backed by SQLite. It seeds a deterministic user and BTC/ETH addresses on startup.

Run it locally with:

```bash
docker compose -f sites/login_deposit_basic/compose.yaml up --build
```

The site is available at <http://localhost:18081/login>.

### Task definitions
Stage 0 ships with tasks stored in `tasks/tasks.yaml`. Tasks are declarative and include:
- `id`: unique identifier
- `site`: logical site name
- `compose_file`: path to the Docker Compose file for the site
- `start_url`: URL agents should hit
- `expected_artifacts`: mapping of artifact keys to ground truth values

Use `agenttrace.load_tasks("tasks/tasks.yaml")` to load them into `Task` objects.

### Task suites (smoke)
Suites are data files under `tasks/suites/`. The smoke suite lives at `tasks/suites/smoke.yaml` and lists task ids to run as a quick subset.

Run the smoke suite with:

```bash
uv run python -m agenttrace.run \
  --tasks-file tasks/tasks.yaml \
  --suite smoke \
  --agent-cmd "python tools/dummy_agent.py"
```

### Scoring contract
`agenttrace.score_artifacts(expected, actual)` compares the expected artifacts from a task with an agent’s reported output. It returns `(passed: bool, diff: str)` and highlights missing keys, mismatched values, and unexpected extras.

### Runner CLI
Use the runner to execute a task against any agent command:

```bash
uv run python -m agenttrace.run \
  --tasks-file tasks/tasks.yaml \
  --agent-cmd "python -c 'import json,os; print(json.dumps({\"artifacts\":{\"BTC\":\"bc1qagenttrace0static0stage000000000000000000\"}}))'"
```

The runner will:
- start the site defined in the selected task via Docker Compose
- pass `AGENTTRACE_START_URL` and `AGENTTRACE_TASK_ID` environment variables to the agent command
- capture the agent’s stdout, validate it via the contract, score it, and print PASS/FAIL
- tear the site down after execution

The runner also writes a machine-readable results JSON file. By default it goes to `results/latest.json`, or you can set a custom path:

```bash
uv run python -m agenttrace.run \
  --tasks-file tasks/tasks.yaml \
  --agent-cmd "python tools/dummy_agent.py" \
  --results-file results/smoke.json
```

Results include per-task status, artifacts, diffs/errors, timings, and summary counts.

### Dummy agent
For smoke tests without a full crawler, use `tools/dummy_agent.py`:

```bash
uv run python -m agenttrace.run \
  --tasks-file tasks/tasks.yaml \
  --agent-cmd "python tools/dummy_agent.py"
```

The dummy agent reads the start URL from `AGENTTRACE_START_URL`, fetches the HTML, extracts the first Bech32 BTC address, and prints JSON in the required format.

For login flows, use `tools/dummy_agent_login.py` with the `login-deposit-basic` task. The runner will export `AGENTTRACE_EMAIL` and `AGENTTRACE_PASSWORD` from task credentials.

### How to run on your own agent
AgentTrace treats your agent as a black box. The runner launches your agent as a subprocess and passes the task context via environment variables. Your agent must read the environment variables, drive the browser or HTTP client however it wants, and print a single JSON object to stdout that matches the AgentTrace output contract.

Required environment variables
- `AGENTTRACE_START_URL`: the URL the agent should start from.
- `AGENTTRACE_TASK_ID`: the task identifier (optional for logic but useful for logging).
- `AGENTTRACE_EMAIL` and `AGENTTRACE_PASSWORD`: only set for tasks that include credentials.

Output contract (stdout)
- Success: print a JSON object with `artifacts` only.
- Failure: print a JSON object with `error` only.
- Do not print extra text to stdout; use stderr for logs if needed.

Example success output:

```json
{"artifacts": {"BTC": "bc1qexampleaddress", "ETH": "0xabc123..."}}
```

Example failure output:

```json
{"error": {"message": "Login page never responded"}}
```

Basic invocation (agent in another repo)

```bash
uv run python -m agenttrace.run \
  --tasks-file tasks/tasks.yaml \
  --task-id login-deposit-basic \
  --agent-cmd "python /path/to/your-agent-repo/main.py"
```

If your agent uses its own venv, point at that interpreter:

```bash
uv run python -m agenttrace.run \
  --tasks-file tasks/tasks.yaml \
  --task-id login-deposit-basic \
  --agent-cmd "/path/to/your-agent-repo/.venv/bin/python /path/to/your-agent-repo/main.py"
```

Using a CLI wrapper script

```bash
uv run python -m agenttrace.run \
  --tasks-file tasks/tasks.yaml \
  --suite smoke \
  --agent-cmd "/path/to/your-agent-repo/run_agent.sh"
```

Exit codes
- The runner returns `0` if all tasks pass, `2` if any task fails, and `1` if any task errors.
- Your agent should return a non-zero exit code on failure; the runner will capture stdout and report it.
