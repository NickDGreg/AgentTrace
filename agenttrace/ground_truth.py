"""Ground truth loaders for benchmark tasks."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def load_expected_artifacts_from_db(db_path: Path, user_email: str) -> dict[str, str]:
    """Load deposit addresses for a user from the site SQLite database."""
    if not db_path.exists():
        raise ValueError(f"ground truth db not found: {db_path}")

    with sqlite3.connect(db_path) as db:
        db.row_factory = sqlite3.Row
        user = db.execute(
            "SELECT id FROM users WHERE email = ?",
            (user_email,),
        ).fetchone()
        if user is None:
            raise ValueError(f"ground truth user not found: {user_email}")

        rows = db.execute(
            "SELECT chain, address FROM deposit_addresses WHERE user_id = ?",
            (user["id"],),
        ).fetchall()
        if not rows:
            raise ValueError(f"no deposit addresses found for user: {user_email}")

        return {row["chain"]: row["address"] for row in rows}
