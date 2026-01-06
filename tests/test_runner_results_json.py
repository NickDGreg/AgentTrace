import json
import subprocess
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from agenttrace import run as runner


@contextmanager
def _no_op_site(_compose_file):
    yield


def test_runner_writes_results_json(tmp_path: Path, monkeypatch):
    compose = tmp_path / "compose.yaml"
    compose.write_text("services: {}", encoding="utf-8")

    task_yaml = tmp_path / "tasks.yaml"
    task_yaml.write_text(
        f"""
tasks:
  - id: example
    site: demo
    compose_file: {compose}
    start_url: http://localhost
    expected_artifacts:
      BTC: "addr"
""",
        encoding="utf-8",
    )

    results_path = tmp_path / "results.json"

    completed = subprocess.CompletedProcess(
        args="cmd", returncode=0, stdout='{"artifacts":{"BTC":"addr"}}', stderr=""
    )
    monkeypatch.setattr(runner, "_running_site", _no_op_site)
    monkeypatch.setattr(runner, "_wait_for_site", mock.Mock())
    monkeypatch.setattr(runner.subprocess, "run", mock.Mock(return_value=completed))

    exit_code = runner.main(
        [
            "--tasks-file",
            str(task_yaml),
            "--agent-cmd",
            "dummy",
            "--results-file",
            str(results_path),
        ]
    )

    assert exit_code == 0
    assert results_path.exists()

    payload = json.loads(results_path.read_text(encoding="utf-8"))
    assert set(payload.keys()) == {"metadata", "results", "summary"}
    assert payload["metadata"]["selection"]["tasks_file"] == str(task_yaml)

    results = payload["results"]
    assert isinstance(results, list)
    assert len(results) == 1
    result = results[0]
    assert result["task_id"] == "example"
    assert result["status"] in {"pass", "fail", "error"}
    assert isinstance(result["passed"], bool)
    assert "timings" in result

    summary = payload["summary"]
    assert summary == {"total": 1, "passed": 1, "failed": 0, "errored": 0}
