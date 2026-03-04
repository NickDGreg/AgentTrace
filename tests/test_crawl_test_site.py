import sqlite3
from pathlib import Path

from sites.crawl_test import app as site_app


def _init_seed(tmp_path: Path) -> Path:
    db_path = tmp_path / "crawl_test.db"
    site_app.DB_PATH = db_path
    site_app._init_db()
    site_app._seed_db()
    return db_path


def test_index_is_accessible_without_login(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()

    response = client.get("/index")

    assert response.status_code == 200
    assert b"Portfolio" in response.data


def test_account_is_accessible_without_login(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()

    response = client.get("/account")

    assert response.status_code == 200
    body = response.data.decode("utf-8", errors="replace")
    assert "GoldenTradr | Account" in body
    assert "Unauthorized" not in body


def test_deposit_panel_is_accessible_without_login_and_contains_addresses(
    tmp_path: Path,
):
    db_path = _init_seed(tmp_path)
    client = site_app.app.test_client()

    response = client.get("/account/deposit-panel")

    assert response.status_code == 200
    body = response.data.decode("utf-8", errors="replace")

    with sqlite3.connect(db_path) as db:
        rows = db.execute(
            "SELECT asset, address FROM deposit_addresses",
        ).fetchall()

    for asset, address in rows:
        assert address in body
        assert f'value="{asset}"' in body

