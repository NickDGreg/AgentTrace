"""Agent output contract and validation helpers."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Tuple

ValidationResult = Tuple[dict[str, str] | None, str | None]


def validate_agent_output(payload: str | bytes | Mapping[str, Any]) -> ValidationResult:
    """Validate agent output and return (artifacts, error_message)."""
    data, error = _coerce_mapping(payload)
    if error:
        return None, error

    artifacts_raw = data.get("artifacts")
    error_raw = data.get("error")

    normalized_artifacts: dict[str, str] | None = None
    normalized_error: str | None = None

    if artifacts_raw is not None:
        if not isinstance(artifacts_raw, Mapping):
            return None, "artifacts must be an object mapping strings to strings."
        normalized_artifacts = {}
        for key, value in artifacts_raw.items():
            if not isinstance(key, str) or not isinstance(value, str):
                return None, "artifact keys and values must be strings."
            normalized_artifacts[key] = value

    if error_raw is not None:
        if isinstance(error_raw, str):
            normalized_error = error_raw
        elif isinstance(error_raw, Mapping):
            message = error_raw.get("message")
            if not isinstance(message, str) or not message.strip():
                return None, 'error.message must be a non-empty string.'
            normalized_error = message
        else:
            return None, 'error must be a string or an object with a "message" field.'

    if normalized_artifacts is not None and normalized_error is not None:
        return None, "output must not include both artifacts and error."

    if normalized_artifacts is not None:
        return normalized_artifacts, None

    if normalized_error is not None:
        return None, normalized_error

    return None, "output must include either artifacts or an error."


def _coerce_mapping(payload: str | bytes | Mapping[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    if isinstance(payload, Mapping):
        return dict(payload), None

    if isinstance(payload, (bytes, bytearray)):
        try:
            payload = payload.decode()
        except UnicodeDecodeError as exc:
            return None, f"output is not valid UTF-8: {exc}"

    if isinstance(payload, str):
        try:
            loaded = json.loads(payload)
        except json.JSONDecodeError as exc:
            return None, f"output is not valid JSON: {exc}"
        if not isinstance(loaded, Mapping):
            return None, "top-level JSON value must be an object."
        return dict(loaded), None

    return None, "output format is not understood."
