from pathlib import Path

import pytest

from agenttrace import load_suite_ids, load_tasks
from agenttrace import run as runner


def test_tasks_duplicate_id_fails(tmp_path: Path):
    temp_compose = tmp_path / "compose.yaml"
    temp_compose.write_text("services: {}", encoding="utf-8")

    task_yaml = tmp_path / "tasks.yaml"
    task_yaml.write_text(
        f"""
tasks:
  - id: dup
    site: demo
    compose_file: {temp_compose}
    start_url: http://localhost
    expected_artifacts:
      BTC: "123"
  - id: dup
    site: demo
    compose_file: {temp_compose}
    start_url: http://localhost
    expected_artifacts:
      BTC: "456"
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate task id"):
        load_tasks(task_yaml)


def test_suite_selects_expected_task_ids(tmp_path: Path):
    temp_compose = tmp_path / "compose.yaml"
    temp_compose.write_text("services: {}", encoding="utf-8")

    task_yaml = tmp_path / "tasks.yaml"
    task_yaml.write_text(
        f"""
tasks:
  - id: a
    site: demo
    compose_file: {temp_compose}
    start_url: http://localhost
    expected_artifacts:
      BTC: "123"
  - id: b
    site: demo
    compose_file: {temp_compose}
    start_url: http://localhost
    expected_artifacts:
      BTC: "456"
  - id: c
    site: demo
    compose_file: {temp_compose}
    start_url: http://localhost
    expected_artifacts:
      BTC: "789"
""",
        encoding="utf-8",
    )

    suites_dir = tmp_path / "suites"
    suites_dir.mkdir()
    suite_yaml = suites_dir / "smoke.yaml"
    suite_yaml.write_text(
        """
tasks:
  - c
  - a
""",
        encoding="utf-8",
    )

    tasks = load_tasks(task_yaml)
    suite_ids = load_suite_ids(suite_yaml)
    selected = runner._select_tasks(tasks, None, suite_ids)

    assert [task.id for task in selected] == ["c", "a"]


def test_missing_suite_fails_cleanly(tmp_path: Path):
    tasks_file = tmp_path / "tasks.yaml"
    tasks_file.write_text("tasks: []", encoding="utf-8")

    with pytest.raises(ValueError, match="suite file not found"):
        runner._load_suite_ids(str(tasks_file), "smoke")
