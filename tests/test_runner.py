import subprocess
from pathlib import Path
from unittest import mock

import pytest

from agenttrace import Task
from agenttrace.run import RunnerError, _run_task, _select_task


@pytest.fixture
def sample_task(tmp_path: Path) -> Task:
    compose = tmp_path / "compose.yaml"
    compose.write_text("services: {}", encoding="utf-8")
    return Task(
        id="example",
        site="demo",
        compose_file=compose,
        start_url="http://localhost",
        expected_artifacts={"BTC": "addr"},
    )


def test_select_task_single(sample_task: Task):
    task = _select_task([sample_task], None)
    assert task.id == "example"


def test_select_task_missing():
    with pytest.raises(ValueError):
        _select_task([], None)


def test_select_task_by_id(sample_task: Task):
    task = _select_task([sample_task], "example")
    assert task is sample_task


def test_run_task_success(sample_task: Task):
    completed = subprocess.CompletedProcess(args="cmd", returncode=0, stdout='{"artifacts":{"BTC":"addr"}}', stderr="")
    with mock.patch("subprocess.run", return_value=completed):
        exit_code = _run_task(sample_task, "cmd", timeout=5)
    assert exit_code == 0


def test_run_task_validation_error(sample_task: Task):
    completed = subprocess.CompletedProcess(args="cmd", returncode=0, stdout="{}", stderr="")
    with mock.patch("subprocess.run", return_value=completed):
        with pytest.raises(RunnerError):
            _run_task(sample_task, "cmd", timeout=5)
