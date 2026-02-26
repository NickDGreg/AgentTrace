"""Run AgentTrace tasks against isolated Docker Compose stacks."""

from __future__ import annotations

import argparse
import json
import socket
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import yaml

from . import Task, load_tasks
from .run import _load_suite_ids, _select_tasks, main as run_main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run AgentTrace tasks using rewritten Compose files with ephemeral host ports. "
            "This enables multiple runs in parallel on the same machine."
        )
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
        help="Agent command executed by the standard AgentTrace runner.",
    )
    parser.add_argument(
        "--agent-timeout",
        type=int,
        default=120,
        help="Timeout (seconds) before aborting the agent process.",
    )
    parser.add_argument(
        "--results-file",
        default="results/latest-isolated.json",
        help="Path to write results JSON.",
    )
    parser.add_argument(
        "--manifest-file",
        default="results/isolation/latest.json",
        help="Path to write the isolation manifest (ports + compose mapping).",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep generated temporary files for debugging.",
    )
    args = parser.parse_args(argv)

    try:
        tasks = load_tasks(args.tasks_file)
        suite_ids = _load_suite_ids(args.tasks_file, args.suite)
        selected = _select_tasks(tasks, args.task_id, suite_ids)
    except ValueError as exc:
        print(f"Failed to load tasks: {exc}")
        return 1

    if args.keep_temp:
        isolated_root = Path(
            tempfile.mkdtemp(prefix="agenttrace-isolated-", dir=None)
        ).resolve()
        return _run_with_isolated_files(
            selected,
            isolated_root,
            args.agent_cmd,
            args.agent_timeout,
            args.results_file,
            args.manifest_file,
        )

    with tempfile.TemporaryDirectory(prefix="agenttrace-isolated-") as tmp_dir:
        isolated_root = Path(tmp_dir).resolve()
        return _run_with_isolated_files(
            selected,
            isolated_root,
            args.agent_cmd,
            args.agent_timeout,
            args.results_file,
            args.manifest_file,
        )


def _run_with_isolated_files(
    tasks: list[Task],
    isolated_root: Path,
    agent_cmd: str,
    agent_timeout: int,
    results_file: str,
    manifest_file: str,
) -> int:
    isolated_tasks, manifest = build_isolated_tasks(tasks, isolated_root)
    isolated_tasks_file = isolated_root / "tasks.isolated.yaml"
    write_tasks_yaml(isolated_tasks, isolated_tasks_file)
    _write_manifest(manifest, manifest_file)
    return run_main(
        [
            "--tasks-file",
            str(isolated_tasks_file),
            "--agent-cmd",
            agent_cmd,
            "--agent-timeout",
            str(agent_timeout),
            "--results-file",
            results_file,
        ]
    )


def build_isolated_tasks(
    tasks: list[Task], isolated_root: Path
) -> tuple[list[Task], dict[str, Any]]:
    isolated_root.mkdir(parents=True, exist_ok=True)
    compose_map: dict[Path, tuple[Path, dict[int, int]]] = {}
    compose_manifest: list[dict[str, Any]] = []
    used_ports: set[int] = set()

    for index, compose_path in enumerate({task.compose_file for task in tasks}, start=1):
        rewritten_compose = isolated_root / f"{compose_path.stem}.isolated.{index}.yaml"
        port_map = rewrite_compose_with_ephemeral_ports(
            compose_path, rewritten_compose, used_ports
        )
        compose_map[compose_path] = (rewritten_compose, port_map)
        compose_manifest.append(
            {
                "original_compose_file": str(compose_path),
                "isolated_compose_file": str(rewritten_compose),
                "port_map": {str(k): v for k, v in sorted(port_map.items())},
            }
        )

    rewritten_tasks: list[Task] = []
    for task in tasks:
        rewritten_compose, port_map = compose_map[task.compose_file]
        rewritten_tasks.append(
            Task(
                id=task.id,
                site=task.site,
                compose_file=rewritten_compose,
                start_url=rewrite_start_url_port(task.start_url, port_map),
                expected_artifacts=dict(task.expected_artifacts),
                credentials=dict(task.credentials) if task.credentials else None,
                ground_truth_db=task.ground_truth_db,
                ground_truth_user_email=task.ground_truth_user_email,
            )
        )

    manifest = {
        "isolated_root": str(isolated_root),
        "compose_files": compose_manifest,
        "tasks": [
            {
                "id": task.id,
                "original_start_url": original.start_url,
                "isolated_start_url": task.start_url,
            }
            for original, task in zip(tasks, rewritten_tasks, strict=True)
        ],
    }
    return rewritten_tasks, manifest


def rewrite_compose_with_ephemeral_ports(
    compose_path: Path, output_path: Path, used_ports: set[int] | None = None
) -> dict[int, int]:
    payload = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"compose file is not a mapping: {compose_path}")

    services = payload.get("services")
    if not isinstance(services, dict):
        raise ValueError(f"compose file has no services mapping: {compose_path}")

    used_ports = used_ports if used_ports is not None else set()
    port_map: dict[int, int] = {}

    for service_def in services.values():
        if not isinstance(service_def, dict):
            continue
        ports = service_def.get("ports")
        if not isinstance(ports, list):
            continue
        rewritten_ports: list[Any] = []
        for entry in ports:
            if isinstance(entry, str):
                rewritten_ports.append(
                    _rewrite_port_mapping_string(entry, port_map, used_ports)
                )
            elif isinstance(entry, dict):
                rewritten_ports.append(
                    _rewrite_port_mapping_object(entry, port_map, used_ports)
                )
            else:
                rewritten_ports.append(entry)
        service_def["ports"] = rewritten_ports

    output_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    return port_map


def rewrite_start_url_port(start_url: str, port_map: dict[int, int]) -> str:
    parsed = urlparse(start_url)
    if parsed.port is None or parsed.port not in port_map:
        return start_url

    host = parsed.hostname or "localhost"
    replacement = f"{host}:{port_map[parsed.port]}"
    return urlunparse(parsed._replace(netloc=replacement))


def write_tasks_yaml(tasks: list[Task], output_path: Path) -> None:
    payload = {"tasks": [_task_to_yaml_dict(task) for task in tasks]}
    output_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def _task_to_yaml_dict(task: Task) -> dict[str, Any]:
    payload = asdict(task)
    payload["compose_file"] = str(task.compose_file)
    payload["expected_artifacts"] = dict(task.expected_artifacts)
    if task.ground_truth_db is not None:
        payload["ground_truth_db"] = str(task.ground_truth_db)
    return payload


def _rewrite_port_mapping_string(
    mapping: str, port_map: dict[int, int], used_ports: set[int]
) -> str:
    protocol = ""
    body = mapping
    if "/" in mapping:
        body, protocol_suffix = mapping.rsplit("/", 1)
        protocol = f"/{protocol_suffix}"

    parts = body.split(":")
    if len(parts) < 2:
        return mapping

    if len(parts) == 2:
        prefix_parts: list[str] = []
        host_port_text = parts[0]
        target = parts[1]
    else:
        prefix_parts = parts[:-2]
        host_port_text = parts[-2]
        target = parts[-1]

    if not host_port_text.isdigit():
        return mapping

    host_port = int(host_port_text)
    replacement = port_map.get(host_port)
    if replacement is None:
        replacement = _reserve_ephemeral_port(used_ports)
        port_map[host_port] = replacement

    rewritten_parts = [*prefix_parts, str(replacement), target]
    return ":".join(rewritten_parts) + protocol


def _rewrite_port_mapping_object(
    mapping: dict[str, Any], port_map: dict[int, int], used_ports: set[int]
) -> dict[str, Any]:
    published = mapping.get("published")
    if isinstance(published, str) and published.isdigit():
        old_port = int(published)
    elif isinstance(published, int):
        old_port = published
    else:
        return mapping

    replacement = port_map.get(old_port)
    if replacement is None:
        replacement = _reserve_ephemeral_port(used_ports)
        port_map[old_port] = replacement

    rewritten = dict(mapping)
    rewritten["published"] = replacement
    return rewritten


def _reserve_ephemeral_port(used_ports: set[int]) -> int:
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        if port not in used_ports:
            used_ports.add(port)
            return port


def _write_manifest(manifest: dict[str, Any], manifest_file: str) -> None:
    path = Path(manifest_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

