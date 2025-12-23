import subprocess
import urllib.error
from pathlib import Path
from unittest import mock

import pytest

from agenttrace import Task
from agenttrace.run import (
    SITE_READY_TIMEOUT_SECONDS,
    RunnerError,
    _run_task,
    _select_task,
    _wait_for_site,
)


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
    completed = subprocess.CompletedProcess(
        args="cmd", returncode=0, stdout='{"artifacts":{"BTC":"addr"}}', stderr=""
    )
    with mock.patch("agenttrace.run._wait_for_site") as wait_for_site:
        with mock.patch("subprocess.run", return_value=completed):
            exit_code = _run_task(sample_task, "cmd", timeout=5)
    wait_for_site.assert_called_once_with(
        sample_task.start_url, timeout=min(5, SITE_READY_TIMEOUT_SECONDS)
    )
    assert exit_code == 0


def test_run_task_validation_error(sample_task: Task):
    completed = subprocess.CompletedProcess(
        args="cmd", returncode=0, stdout="{}", stderr=""
    )
    with mock.patch("agenttrace.run._wait_for_site") as wait_for_site:
        with mock.patch("subprocess.run", return_value=completed):
            with pytest.raises(RunnerError):
                _run_task(sample_task, "cmd", timeout=5)
    wait_for_site.assert_called_once_with(
        sample_task.start_url, timeout=min(5, SITE_READY_TIMEOUT_SECONDS)
    )


def test_wait_for_site_success():
    response = mock.MagicMock()
    response.read.return_value = b"ok"
    context_manager = mock.MagicMock()
    context_manager.__enter__.return_value = response
    context_manager.__exit__.return_value = False

    with mock.patch(
        "agenttrace.run.urllib.request.urlopen", return_value=context_manager
    ) as urlopen:
        _wait_for_site("http://localhost", timeout=0, interval=0)
    assert urlopen.call_count == 1


def test_wait_for_site_timeout():
    with mock.patch(
        "agenttrace.run.urllib.request.urlopen",
        side_effect=urllib.error.URLError("nope"),
    ) as urlopen:
        with pytest.raises(RunnerError, match="site did not become ready"):
            _wait_for_site("http://localhost", timeout=0, interval=0)
    assert urlopen.call_count == 1
