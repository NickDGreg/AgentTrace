"""Task loading helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class Task:
    id: str
    site: str
    compose_file: Path
    start_url: str
    expected_artifacts: dict[str, str]


def load_tasks(path: str | Path) -> list[Task]:
    """Load task definitions from YAML."""
    data = _read_yaml(Path(path))
    if not isinstance(data, dict):
        raise ValueError("tasks file must define a mapping with a 'tasks' key.")

    raw_tasks = data.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise ValueError("'tasks' must be a non-empty list.")

    tasks: list[Task] = []
    for entry in raw_tasks:
        tasks.append(_parse_task(entry))
    return tasks


def _read_yaml(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text)


def _parse_task(entry: Any) -> Task:
    if not isinstance(entry, dict):
        raise ValueError("each task must be a mapping.")

    try:
        task_id = entry["id"]
        site = entry["site"]
        compose_file = Path(entry["compose_file"]).resolve()
        start_url = entry["start_url"]
        expected_artifacts = entry["expected_artifacts"]
    except KeyError as exc:
        raise ValueError(f"missing required task field: {exc.args[0]}") from exc

    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("task id must be a non-empty string.")
    if not isinstance(site, str) or not site.strip():
        raise ValueError("site must be a non-empty string.")
    if not compose_file.exists():
        raise ValueError(f"compose file does not exist: {compose_file}")
    if not isinstance(start_url, str) or not start_url.startswith("http"):
        raise ValueError("start_url must be an http/https URL.")
    if not isinstance(expected_artifacts, dict) or not expected_artifacts:
        raise ValueError("expected_artifacts must be a non-empty mapping.")
    for key, value in expected_artifacts.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("expected artifact keys and values must be strings.")

    return Task(
        id=task_id,
        site=site,
        compose_file=compose_file,
        start_url=start_url,
        expected_artifacts=dict(expected_artifacts),
    )
