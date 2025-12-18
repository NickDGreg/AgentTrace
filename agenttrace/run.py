"""Command-line runner for AgentTrace tasks."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from contextlib import contextmanager
from typing import Iterable

from . import Task, load_tasks, score_artifacts, validate_agent_output


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run AgentTrace tasks against an external agent.")
    parser.add_argument("--tasks-file", default="tasks/tasks.yaml", help="Path to tasks YAML file.")
    parser.add_argument("--task-id", help="Specific task id to run (optional if single task).")
    parser.add_argument(
        "--agent-cmd",
        required=True,
        help="Command to execute the external agent. Receives env vars AGENTTRACE_START_URL and AGENTTRACE_TASK_ID.",
    )
    parser.add_argument(
        "--agent-timeout",
        type=int,
        default=120,
        help="Timeout (seconds) before aborting the agent process.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        tasks = load_tasks(args.tasks_file)
        task = _select_task(tasks, args.task_id)
    except ValueError as exc:
        print(f"Failed to load tasks: {exc}", file=sys.stderr)
        return 1

    try:
        with _running_site(task.compose_file):
            return _run_task(task, args.agent_cmd, args.agent_timeout)
    except RunnerError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


def _run_task(task: Task, agent_cmd: str, timeout: int) -> int:
    env = os.environ.copy()
    env["AGENTTRACE_START_URL"] = task.start_url
    env["AGENTTRACE_TASK_ID"] = task.id

    completed = subprocess.run(
        agent_cmd,
        shell=True,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )

    if completed.returncode != 0:
        raise RunnerError(
            f"agent command exited with {completed.returncode}. stderr: {completed.stderr.strip()}"
        )

    artifacts, validation_error = validate_agent_output(completed.stdout)
    if validation_error:
        raise RunnerError(f"invalid agent output: {validation_error}")
    if artifacts is None:
        raise RunnerError("agent output is empty.")

    passed, diff = score_artifacts(task.expected_artifacts, artifacts)
    status = "PASS" if passed else "FAIL"
    print(f"{status}: {diff}")
    return 0 if passed else 2


def _select_task(tasks: list[Task], task_id: str | None) -> Task:
    if task_id:
        for task in tasks:
            if task.id == task_id:
                return task
        raise ValueError(f"task id not found: {task_id}")
    if len(tasks) == 1:
        return tasks[0]
    raise ValueError("task id is required when multiple tasks are defined.")


@contextmanager
def _running_site(compose_file):
    compose_path = str(compose_file)
    up_cmd = ["docker", "compose", "-f", compose_path, "up", "-d"]
    down_cmd = ["docker", "compose", "-f", compose_path, "down"]
    try:
        subprocess.run(up_cmd, check=True)
    except subprocess.CalledProcessError as exc:
        raise RunnerError(f"failed to start site via docker compose: {exc}") from exc

    try:
        yield
    finally:
        subprocess.run(down_cmd, check=False)


class RunnerError(RuntimeError):
    """Raised when the runner cannot complete the task."""


if __name__ == "__main__":
    raise SystemExit(main())
