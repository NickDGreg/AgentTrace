"""Export Docker Compose logs to a deterministic artifact file."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture `docker compose logs` output to a file."
    )
    parser.add_argument(
        "--compose-file",
        required=True,
        help="Path to docker compose YAML file.",
    )
    parser.add_argument(
        "--out",
        default="results/traces/compose.log",
        help="Output path for logs.",
    )
    parser.add_argument(
        "--tail",
        default="all",
        help="Tail value passed to docker compose logs (default: all).",
    )
    args = parser.parse_args(argv)

    command = [
        "docker",
        "compose",
        "-f",
        args.compose_file,
        "logs",
        "--timestamps",
        "--no-color",
        "--tail",
        args.tail,
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(completed.stdout, encoding="utf-8")

    if completed.returncode != 0:
        if completed.stderr:
            output_path.with_suffix(".stderr.log").write_text(
                completed.stderr, encoding="utf-8"
            )
        return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

