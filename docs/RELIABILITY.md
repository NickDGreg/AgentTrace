# RELIABILITY

Reliability standards for AgentTrace:
- deterministic site startup and seed data
- deterministic task parsing and scoring
- stable machine-readable results format
- hermetic isolated runs for parallelization

Operational controls:
- `python -m agenttrace.run` for canonical execution
- `python -m agenttrace.run_isolated` for parallel isolated execution
- `python -m agenttrace.scaffolding_checks` for structural safety checks
- `pytest` suite as regression gate

Failure triage sources:
- runner stderr output
- `results/*.json`
- Docker Compose logs via `python tools/compose_logs.py --compose-file <compose.yaml> --out results/traces/<name>.log`
- screenshot artifacts from `tools/ui_snapshot.py`
