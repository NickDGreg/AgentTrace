# New User Onboarding

Goal: run one task end-to-end against your own agent command.

## Steps

1. Sync dependencies.
- `uv sync`

2. Verify harness health.
- `uv run pytest -q`

3. Run one benchmark task.
- `uv run python -m agenttrace.run --tasks-file tasks/tasks.yaml --task-id simple-static-btc --agent-cmd "python tools/dummy_agent.py"`

4. Inspect machine-readable output.
- `cat results/latest.json`

5. Integrate your own agent command.
- Replace `python tools/dummy_agent.py` with your executable.
- Ensure your process reads `AGENTTRACE_START_URL` and prints valid JSON only.

6. For parallel execution on shared hosts, use isolated mode.
- `uv run python -m agenttrace.run_isolated --tasks-file tasks/tasks.yaml --task-id simple-static-btc --agent-cmd "<your-agent-cmd>"`
