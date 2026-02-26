from __future__ import annotations

from pathlib import Path

from agenttrace.scaffolding_checks import run_all_checks


def test_scaffolding_checks_pass_for_repository() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    violations = run_all_checks(repo_root)
    assert violations == []

