"""AgentTrace benchmark package skeleton."""

from __future__ import annotations

from .output import validate_agent_output
from .scoring import score_artifacts
from .tasks import Task, load_suite_ids, load_tasks

__all__ = [
    "__version__",
    "validate_agent_output",
    "score_artifacts",
    "Task",
    "load_tasks",
    "load_suite_ids",
]

__version__ = "0.1.0"
