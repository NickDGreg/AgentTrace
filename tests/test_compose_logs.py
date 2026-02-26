from __future__ import annotations

import subprocess
from pathlib import Path
from unittest import mock

from tools import compose_logs


def test_compose_logs_writes_stdout_file(tmp_path: Path) -> None:
    output_path = tmp_path / "compose.log"
    completed = subprocess.CompletedProcess(
        args=["docker"],
        returncode=0,
        stdout="service | ready\n",
        stderr="",
    )
    with mock.patch.object(compose_logs.subprocess, "run", return_value=completed):
        exit_code = compose_logs.main(
            [
                "--compose-file",
                "sites/simple_static/compose.yaml",
                "--out",
                str(output_path),
            ]
        )
    assert exit_code == 0
    assert output_path.read_text(encoding="utf-8") == "service | ready\n"

