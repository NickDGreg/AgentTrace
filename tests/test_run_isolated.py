from __future__ import annotations

from pathlib import Path

import yaml

from agenttrace.run_isolated import (
    build_isolated_tasks,
    rewrite_compose_with_ephemeral_ports,
)
from agenttrace.tasks import Task


def test_rewrite_compose_with_ephemeral_ports_updates_host_ports(tmp_path: Path) -> None:
    compose_path = tmp_path / "compose.yaml"
    compose_path.write_text(
        """
services:
  web:
    image: demo
    environment:
      AGENTTRACE_EXTERNAL_URL: http://localhost:18080/login
    ports:
      - "18080:8000"
      - "127.0.0.1:18081:8001/tcp"
""",
        encoding="utf-8",
    )
    output_path = tmp_path / "compose.isolated.yaml"

    port_map = rewrite_compose_with_ephemeral_ports(compose_path, output_path)

    assert set(port_map.keys()) == {18080, 18081}
    assert all(new_port != old_port for old_port, new_port in port_map.items())

    rewritten = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    ports = rewritten["services"]["web"]["ports"]
    assert isinstance(ports[0], str)
    assert str(port_map[18080]) in ports[0]
    assert isinstance(ports[1], str)
    assert str(port_map[18081]) in ports[1]
    external_url = rewritten["services"]["web"]["environment"]["AGENTTRACE_EXTERNAL_URL"]
    assert f"localhost:{port_map[18080]}" in external_url


def test_build_isolated_tasks_updates_compose_and_start_url(tmp_path: Path) -> None:
    compose_path = tmp_path / "compose.yaml"
    compose_path.write_text(
        """
services:
  web:
    image: demo
    ports:
      - "18080:8000"
""",
        encoding="utf-8",
    )
    task = Task(
        id="demo",
        site="demo",
        compose_file=compose_path,
        start_url="http://localhost:18080/login",
        expected_artifacts={"BTC": "addr"},
    )
    isolated_dir = tmp_path / "isolated"
    isolated_tasks, manifest = build_isolated_tasks([task], isolated_dir)

    assert len(isolated_tasks) == 1
    rewritten = isolated_tasks[0]
    assert rewritten.compose_file != compose_path
    assert rewritten.compose_file.exists()
    assert rewritten.start_url != task.start_url
    assert rewritten.start_url.startswith("http://localhost:")
    assert rewritten.start_url.endswith("/login")

    assert "compose_files" in manifest
    assert len(manifest["compose_files"]) == 1
