"""Command-line runner for AgentTrace tasks."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from . import Task, load_tasks, load_suite_ids, score_artifacts, validate_agent_output
from .ground_truth import load_expected_artifacts_from_db

SITE_READY_TIMEOUT_SECONDS = 30
SITE_READY_POLL_INTERVAL_SECONDS = 0.5
SITE_READY_REQUEST_TIMEOUT_SECONDS = 2.0


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run AgentTrace tasks against an external agent."
    )
    parser.add_argument(
        "--tasks-file", default="tasks/tasks.yaml", help="Path to tasks YAML file."
    )
    parser.add_argument(
        "--task-id", help="Specific task id to run (optional if single task)."
    )
    parser.add_argument(
        "--suite",
        help="Name of a task suite to run (loads tasks/suites/<suite>.yaml).",
    )
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
    parser.add_argument(
        "--results-file",
        default="results/latest.json",
        help="Path to write results JSON.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        tasks = load_tasks(args.tasks_file)
        suite_ids = _load_suite_ids(args.tasks_file, args.suite)
        selected = _select_tasks(tasks, args.task_id, suite_ids)
    except ValueError as exc:
        print(f"Failed to load tasks: {exc}", file=sys.stderr)
        return 1
    return _run_tasks(
        selected,
        args.agent_cmd,
        args.agent_timeout,
        args.results_file,
        args.task_id,
        args.suite,
        args.tasks_file,
    )


def _run_tasks(
    tasks: list[Task],
    agent_cmd: str,
    timeout: int,
    results_file: str,
    task_id: str | None,
    suite_name: str | None,
    tasks_file: str,
) -> int:
    total = len(tasks)
    passed = 0
    failed = 0
    errored = 0
    results: list[dict[str, object]] = []

    for compose_file, grouped in _group_by_compose_file(tasks):
        try:
            with _running_site(compose_file):
                for task in grouped:
                    status, result = _run_task(task, agent_cmd, timeout)
                    detail = result.get("diff") or result.get("error") or ""
                    _print_task_status(status, task.id, str(detail))
                    results.append(result)
                    if status == "PASS":
                        passed += 1
                    elif status == "FAIL":
                        failed += 1
                    else:
                        errored += 1
        except RunnerError as exc:
            for task in grouped:
                result = _error_result(task.id, str(exc))
                _print_task_status("ERROR", task.id, str(exc))
                results.append(result)
                errored += 1

    summary = {"total": total, "passed": passed, "failed": failed, "errored": errored}
    _write_results(
        results_file,
        _build_metadata(task_id, suite_name, tasks_file),
        results,
        summary,
    )

    print(f"TOTAL {total} | PASS {passed} | FAIL {failed} | ERROR {errored}")
    if errored:
        return 1
    if failed:
        return 2
    return 0


def _run_task(task: Task, agent_cmd: str, timeout: int) -> tuple[str, dict[str, object]]:
    start_time = time.time()
    start_monotonic = time.monotonic()
    start_iso = datetime.now(timezone.utc).isoformat()

    site_timeout = min(timeout, SITE_READY_TIMEOUT_SECONDS)
    try:
        _wait_for_site(task.start_url, timeout=site_timeout)
    except RunnerError as exc:
        return "ERROR", _error_result(task.id, str(exc), start_time, start_monotonic, start_iso)

    env = os.environ.copy()
    env["AGENTTRACE_START_URL"] = task.start_url
    env["AGENTTRACE_TASK_ID"] = task.id
    if task.credentials:
        if "email" in task.credentials:
            env["AGENTTRACE_EMAIL"] = task.credentials["email"]
        if "password" in task.credentials:
            env["AGENTTRACE_PASSWORD"] = task.credentials["password"]

    try:
        completed = subprocess.run(
            agent_cmd,
            shell=True,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return "ERROR", _error_result(
            task.id,
            f"agent command timed out after {timeout}s",
            start_time,
            start_monotonic,
            start_iso,
        )

    if completed.returncode != 0:
        return "ERROR", _error_result(
            task.id,
            f"agent command exited with {completed.returncode}. stderr: {completed.stderr.strip()}",
            start_time,
            start_monotonic,
            start_iso,
        )

    artifacts, validation_error = validate_agent_output(completed.stdout)
    if validation_error:
        return "ERROR", _error_result(
            task.id,
            f"invalid agent output: {validation_error}",
            start_time,
            start_monotonic,
            start_iso,
        )
    if artifacts is None:
        return "ERROR", _error_result(
            task.id,
            "agent output is empty.",
            start_time,
            start_monotonic,
            start_iso,
        )

    try:
        expected = _get_expected_artifacts(task)
    except ValueError as exc:
        return "ERROR", _error_result(
            task.id,
            f"failed to load ground truth: {exc}",
            start_time,
            start_monotonic,
            start_iso,
        )

    passed, diff = score_artifacts(expected, artifacts)
    status = "PASS" if passed else "FAIL"
    return status, _finalize_result(
        task.id,
        status,
        artifacts,
        diff,
        None,
        start_time,
        start_monotonic,
        start_iso,
    )


def _wait_for_site(
    url: str, timeout: int, interval: float = SITE_READY_POLL_INTERVAL_SECONDS
) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None

    while True:
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "AgentTraceRunner/0.1"}
            )
            request_timeout = min(SITE_READY_REQUEST_TIMEOUT_SECONDS, max(0.1, timeout))
            with urllib.request.urlopen(req, timeout=request_timeout) as response:
                response.read(1)
            return
        except Exception as exc:
            last_error = exc

        if time.monotonic() >= deadline:
            break
        time.sleep(interval)

    raise RunnerError(
        f"site did not become ready at {url} within {timeout}s: {last_error}"
    )


def _select_tasks(
    tasks: list[Task], task_id: str | None, suite_ids: list[str] | None
) -> list[Task]:
    if task_id and suite_ids:
        raise ValueError("cannot use --task-id and --suite together.")

    if suite_ids:
        tasks_by_id = {task.id: task for task in tasks}
        missing = [suite_id for suite_id in suite_ids if suite_id not in tasks_by_id]
        if missing:
            raise ValueError(f"suite includes unknown task ids: {', '.join(missing)}")
        return [tasks_by_id[suite_id] for suite_id in suite_ids]

    if task_id:
        for task in tasks:
            if task.id == task_id:
                return [task]
        raise ValueError(f"task id not found: {task_id}")
    if len(tasks) == 1:
        return [tasks[0]]
    raise ValueError("task id is required when multiple tasks are defined.")


def _load_suite_ids(tasks_file: str, suite_name: str | None) -> list[str] | None:
    if not suite_name:
        return None
    suites_dir = Path(tasks_file).resolve().parent / "suites"
    suite_path = suites_dir / f"{suite_name}.yaml"
    if not suite_path.exists():
        raise ValueError(f"suite file not found: {suite_path}")
    return load_suite_ids(suite_path)


def _group_by_compose_file(tasks: list[Task]) -> list[tuple[Path, list[Task]]]:
    grouped: dict[Path, list[Task]] = {}
    for task in tasks:
        grouped.setdefault(task.compose_file, []).append(task)
    return list(grouped.items())


def _print_task_status(status: str, task_id: str, detail: str) -> None:
    if status == "PASS":
        print(f"PASS {task_id}")
    elif status == "FAIL":
        print(f"FAIL {task_id}: {detail}")
    else:
        print(f"ERROR {task_id}: {detail}")


def _get_expected_artifacts(task: Task) -> dict[str, str]:
    if task.ground_truth_db and task.ground_truth_user_email:
        return load_expected_artifacts_from_db(
            task.ground_truth_db, task.ground_truth_user_email
        )
    return dict(task.expected_artifacts)


def _build_metadata(
    task_id: str | None, suite_name: str | None, tasks_file: str
) -> dict[str, object]:
    selection: dict[str, object] = {"tasks_file": tasks_file}
    if task_id:
        selection["task_id"] = task_id
    if suite_name:
        selection["suite"] = suite_name
    return {"timestamp": datetime.now(timezone.utc).isoformat(), "selection": selection}


def _write_results(
    results_file: str,
    metadata: dict[str, object],
    results: list[dict[str, object]],
    summary: dict[str, int],
) -> None:
    path = Path(results_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"metadata": metadata, "results": results, "summary": summary}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _finalize_result(
    task_id: str,
    status: str,
    artifacts: dict[str, str] | None,
    diff: str | None,
    error: str | None,
    start_time: float,
    start_monotonic: float,
    start_iso: str,
) -> dict[str, object]:
    end_iso = datetime.now(timezone.utc).isoformat()
    duration = time.monotonic() - start_monotonic
    status_lower = status.lower()
    return {
        "task_id": task_id,
        "status": status_lower,
        "passed": status_lower == "pass",
        "artifacts": artifacts,
        "diff": diff if status_lower == "fail" else None,
        "error": error if status_lower == "error" else None,
        "timings": {
            "start": start_iso,
            "end": end_iso,
            "duration_seconds": round(duration, 3),
            "start_epoch_seconds": start_time,
        },
    }


def _error_result(
    task_id: str,
    message: str,
    start_time: float | None = None,
    start_monotonic: float | None = None,
    start_iso: str | None = None,
) -> dict[str, object]:
    start_time = start_time if start_time is not None else time.time()
    start_monotonic = (
        start_monotonic if start_monotonic is not None else time.monotonic()
    )
    start_iso = start_iso or datetime.now(timezone.utc).isoformat()
    return _finalize_result(
        task_id,
        "ERROR",
        None,
        None,
        message,
        start_time,
        start_monotonic,
        start_iso,
    )


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
