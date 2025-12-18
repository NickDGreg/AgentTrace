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

### Task definitions
Stage 0 ships with a single task stored in `tasks/tasks.yaml`. Tasks are declarative and include:
- `id`: unique identifier
- `site`: logical site name
- `compose_file`: path to the Docker Compose file for the site
- `start_url`: URL agents should hit
- `expected_artifacts`: mapping of artifact keys to ground truth values

Use `agenttrace.load_tasks("tasks/tasks.yaml")` to load them into `Task` objects.

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

### Dummy agent
For smoke tests without a full crawler, use `tools/dummy_agent.py`:

```bash
uv run python -m agenttrace.run \
  --tasks-file tasks/tasks.yaml \
  --agent-cmd "python tools/dummy_agent.py"
```

The dummy agent reads the start URL from `AGENTTRACE_START_URL`, fetches the HTML, extracts the first Bech32 BTC address, and prints JSON in the required format.
