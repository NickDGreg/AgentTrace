from pathlib import Path

import pytest

from agenttrace import Task, load_tasks, validate_agent_output


def test_validate_agent_output_success():
    payload = '{"artifacts": {"BTC": "bc1qexample"}}'
    artifacts, error = validate_agent_output(payload)

    assert error is None
    assert artifacts == {"BTC": "bc1qexample"}


def test_validate_agent_output_error_message_dict():
    payload = {"error": {"message": "Page failed"}}
    artifacts, error = validate_agent_output(payload)

    assert artifacts is None
    assert error == "Page failed"


def test_validate_agent_output_schema_error():
    payload = '{"artifacts": ["bad"]}'
    artifacts, error = validate_agent_output(payload)

    assert artifacts is None
    assert "object" in error


def test_load_tasks_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    temp_compose = tmp_path / "compose.yaml"
    temp_compose.write_text("services: {}", encoding="utf-8")

    task_yaml = tmp_path / "tasks.yaml"
    task_yaml.write_text(
        f"""
tasks:
  - id: example
    site: demo
    compose_file: {temp_compose}
    start_url: http://localhost
    expected_artifacts:
      BTC: "123"
""",
        encoding="utf-8",
    )

    tasks = load_tasks(task_yaml)

    assert len(tasks) == 1
    task = tasks[0]
    assert isinstance(task, Task)
    assert task.id == "example"
    assert task.compose_file == temp_compose.resolve()


def test_load_tasks_multiple_entries(tmp_path: Path):
    temp_compose = tmp_path / "compose.yaml"
    temp_compose.write_text("services: {}", encoding="utf-8")

    task_yaml = tmp_path / "tasks.yaml"
    task_yaml.write_text(
        f"""
tasks:
  - id: example-a
    site: demo
    compose_file: {temp_compose}
    start_url: http://localhost
    expected_artifacts:
      BTC: "123"
  - id: example-b
    site: demo
    compose_file: {temp_compose}
    start_url: http://localhost
    expected_artifacts:
      BTC: "456"
""",
        encoding="utf-8",
    )

    tasks = load_tasks(task_yaml)

    assert [task.id for task in tasks] == ["example-a", "example-b"]
