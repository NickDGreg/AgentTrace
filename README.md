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
