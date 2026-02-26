SHELL := /bin/zsh

PYTHON ?= .venv/bin/python
UV ?= uv

.PHONY: help sync test test-fast check lint typecheck coverage arch-check ui-snapshot run-isolated compose-logs

help:
	@echo "Available targets:"
	@echo "  make sync          - install dependencies with uv"
	@echo "  make test          - run full pytest suite"
	@echo "  make test-fast     - run pytest in quiet mode"
	@echo "  make lint          - run ruff checks"
	@echo "  make typecheck     - run mypy strict checks (agenttrace package)"
	@echo "  make arch-check    - run repository scaffolding checks"
	@echo "  make coverage      - run tests with coverage report"
	@echo "  make check         - run lint + typecheck + arch-check + tests"
	@echo "  make ui-snapshot   - capture screenshot (URL=<url> OUT=<png path>)"
	@echo "  make run-isolated  - run task with isolated compose ports"
	@echo "  make compose-logs  - export docker compose logs to trace files"

sync:
	$(UV) sync

test:
	@if command -v $(UV) >/dev/null 2>&1; then \
		$(UV) run pytest; \
	else \
		$(PYTHON) -m pytest; \
	fi

test-fast:
	@if command -v $(UV) >/dev/null 2>&1; then \
		$(UV) run pytest -q; \
	else \
		$(PYTHON) -m pytest -q; \
	fi

lint:
	@if command -v $(UV) >/dev/null 2>&1; then \
		$(UV) run ruff check .; \
	else \
		$(PYTHON) -m ruff check .; \
	fi

typecheck:
	@if command -v $(UV) >/dev/null 2>&1; then \
		$(UV) run mypy agenttrace; \
	else \
		$(PYTHON) -m mypy agenttrace; \
	fi

arch-check:
	@if command -v $(UV) >/dev/null 2>&1; then \
		$(UV) run python -m agenttrace.scaffolding_checks; \
	else \
		$(PYTHON) -m agenttrace.scaffolding_checks; \
	fi

coverage:
	@if command -v $(UV) >/dev/null 2>&1; then \
		$(UV) run pytest --cov=agenttrace --cov-report=term-missing; \
	else \
		$(PYTHON) -m pytest --cov=agenttrace --cov-report=term-missing; \
	fi

check: lint typecheck arch-check test-fast

ui-snapshot:
	@if [ -z "$$URL" ]; then \
		echo "URL must be provided. Example: make ui-snapshot URL=http://localhost:18080/ OUT=results/ui/simple.png"; \
		exit 1; \
	fi
	@if command -v $(UV) >/dev/null 2>&1; then \
		$(UV) run python tools/ui_snapshot.py --url "$$URL" --out "$${OUT:-results/ui/latest.png}" --full-page; \
	else \
		$(PYTHON) tools/ui_snapshot.py --url "$$URL" --out "$${OUT:-results/ui/latest.png}" --full-page; \
	fi

run-isolated:
	@if [ -z "$$AGENT_CMD" ]; then \
		echo "AGENT_CMD must be provided. Example: make run-isolated TASK_ID=simple-static-btc AGENT_CMD='python tools/dummy_agent.py'"; \
		exit 1; \
	fi

compose-logs:
	@if [ -z "$$COMPOSE_FILE" ]; then \
		echo "COMPOSE_FILE must be provided. Example: make compose-logs COMPOSE_FILE=sites/simple_static/compose.yaml OUT=results/traces/simple_static.log"; \
		exit 1; \
	fi
	@if command -v $(UV) >/dev/null 2>&1; then \
		$(UV) run python tools/compose_logs.py --compose-file "$$COMPOSE_FILE" --out "$${OUT:-results/traces/compose.log}" --tail "$${TAIL:-all}"; \
	else \
		$(PYTHON) tools/compose_logs.py --compose-file "$$COMPOSE_FILE" --out "$${OUT:-results/traces/compose.log}" --tail "$${TAIL:-all}"; \
	fi
	@if command -v $(UV) >/dev/null 2>&1; then \
		$(UV) run python -m agenttrace.run_isolated --tasks-file "$${TASKS_FILE:-tasks/tasks.yaml}" --task-id "$${TASK_ID:-simple-static-btc}" --agent-cmd "$$AGENT_CMD" --results-file "$${RESULTS_FILE:-results/latest-isolated.json}"; \
	else \
		$(PYTHON) -m agenttrace.run_isolated --tasks-file "$${TASKS_FILE:-tasks/tasks.yaml}" --task-id "$${TASK_ID:-simple-static-btc}" --agent-cmd "$$AGENT_CMD" --results-file "$${RESULTS_FILE:-results/latest-isolated.json}"; \
	fi
