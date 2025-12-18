AgentTrace Build Plan (Zero → V1)

End goal (V1)

AgentTrace provides:
	•	multiple synthetic site families (starting with one)
	•	declarative task definitions (multiple tasks)
	•	a reproducible runner that spins up the target site(s)
	•	a scorer that validates an external agent/crawler’s output against ground truth
	•	deterministic, CI-friendly execution
	•	optional later: BrowserGym compatibility layer (not required for V1)

⸻

Stage 0 — Minimal end-to-end scaffold (setup as quickly and simply as possible)

Objective: have something runnable to test the benchmark setup even if the “site” is trivial.

Deliverables:
	•	a single ultra-simple synthetic “site” that serves one page containing a crypto address in plain HTML
	•	a deterministic “task” definition for this site
	•	a runner that:
	•	starts the site (Docker)
	•	exposes the URL to an external agent/crawler
	•	collects a structured output file/JSON from that agent
	•	a scorer that:
	•	compares extracted output to expected value (ground truth)
	•	returns pass/fail and a useful diff

Notes:
	•	no login, no navigation, no JS
	•	focus is scaffolding: “site runs + task spec + run + score”

⸻

Stage 1 — Make the scaffold benchmark-shaped (still simple)

Objective: move from “one-off test” to “benchmark harness” without increasing site complexity much.

Deliverables:
	•	task schema that supports multiple tasks (even if all point to the same site)
	•	ability to run:
	•	one task by ID
	•	a small suite (“smoke”)
	•	consistent results output (JSON) capturing:
	•	task id
	•	success/failure
	•	extracted artifacts
	•	error messages (if any)
	•	basic contract tests for:
	•	schema parsing/validation
	•	scoring correctness
	•	runner output parsing

Notes:
	•	still only one simple site
	•	goal is repeatability + structure

⸻

Stage 2 — Introduce a “realistic” site flow (login + deposit page)

Objective: add the first meaningful interaction pattern while preserving determinism.

Deliverables:
	•	a synthetic site with:
	•	login page
	•	post-login dashboard
	•	deposit page containing one or more addresses
	•	deterministic seeding of:
	•	user credentials
	•	deposit addresses (ground truth)
	•	scorer reads ground truth from a reliable source:
	•	ideally the site’s DB (preferred)
	•	otherwise a protected truth endpoint only accessible to the harness

Notes:
	•	keep UI basic (server-rendered is fine)
	•	avoid advanced anti-bot features at this stage

⸻

Stage 3 — Support multiple tasks on the same site family

Objective: make tasks vary while the environment remains stable.

Deliverables:
	•	multiple task definitions covering variations like:
	•	different users (different addresses)
	•	different chains (BTC/ETH)
	•	different navigation routes to deposit page (e.g. menu vs direct link)
	•	scorer supports “expected artifacts” as a set/map, not a single string
	•	suites (“smoke”, “full”) that run multiple tasks reproducibly

Notes:
	•	still one site family
	•	task diversity comes from seeded state + minor flow changes

⸻

Stage 4 — Add site family #2 (different build style)

Objective: begin generalisation across “how the site is built”.

Deliverables:
	•	a second synthetic site family that differs structurally, e.g.:
	•	SPA/client-rendered vs server-rendered
	•	“Generate address” button vs static address
	•	address shown via copy-widget vs plain text
	•	tasks that target both families
	•	runner can start the correct site family based on task metadata

Notes:
	•	don’t add many families; add one strong contrast

⸻

Stage 5 — Hardening for public benchmark quality

Objective: reliability, clean boundaries, and preventing accidental shortcuts.

Deliverables:
	•	clear benchmark boundaries:
	•	agent has only normal web access to sites
	•	ground truth is not exposed to the agent
	•	stable setup instructions and deterministic seeding
	•	CI that runs at least the smoke suite on every change
	•	documentation that explains:
	•	what AgentTrace measures
	•	what it doesn’t
	•	how to plug in an external agent/crawler

⸻

Stage 6 — Optional interoperability layer (later)

Objective: enable standard agent interfaces without changing the core benchmark.

Deliverables:
	•	optional adapter for a standard interface style (e.g., BrowserGym-like reset/step)
	•	same sites, same tasks, same scoring
	•	kept separate so it doesn’t constrain benchmark evolution

⸻

Guiding principle throughout

Build the benchmark as: environments + tasks + scoring + runner.
External agents/crawlers are treated as black boxes that accept a URL/creds and return structured extracted artifacts.
