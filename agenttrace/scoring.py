"""Artifact scoring utilities."""

from __future__ import annotations

from typing import Mapping, Tuple


ScoreResult = Tuple[bool, str]


def score_artifacts(expected: Mapping[str, str], actual: Mapping[str, str]) -> ScoreResult:
    """Compare expected artifacts with agent output.

    Returns (pass_bool, diff_text).
    """
    expected_dict = dict(expected)
    actual_dict = dict(actual)

    missing = sorted(key for key in expected_dict if key not in actual_dict)
    mismatched = sorted(
        (key, expected_dict[key], actual_dict[key])
        for key in expected_dict.keys() & actual_dict.keys()
        if expected_dict[key] != actual_dict[key]
    )
    extra = sorted(key for key in actual_dict if key not in expected_dict)

    if not missing and not mismatched and not extra:
        return True, "artifacts match expected output."

    parts: list[str] = []
    if missing:
        parts.append(f"missing keys: {', '.join(missing)}")
    if mismatched:
        formatted = ", ".join(f"{key} (expected {exp!r}, got {got!r})" for key, exp, got in mismatched)
        parts.append(f"mismatched values: {formatted}")
    if extra:
        parts.append(f"extra keys: {', '.join(extra)}")

    diff = "; ".join(parts)
    return False, diff
