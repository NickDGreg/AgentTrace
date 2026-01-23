import sqlite3
from pathlib import Path

from sites.site_one import app as site_app


def _init_seed(tmp_path: Path) -> Path:
    db_path = tmp_path / "site_one.db"
    site_app.DB_PATH = db_path
    site_app._init_db()
    site_app._seed_db()
    return db_path


def _login_seed_user(client):
    response = client.post(
        "/login",
        data={"account": site_app.SEED_EMAIL, "password": site_app.SEED_PASSWORD},
        follow_redirects=False,
    )
    assert response.status_code == 302


def test_account_page_excludes_deposit_addresses(tmp_path: Path):
    db_path = _init_seed(tmp_path)
    client = site_app.app.test_client()
    _login_seed_user(client)

    response = client.get("/account")
    assert response.status_code == 200
    body = response.data.decode("utf-8", errors="replace")

    with sqlite3.connect(db_path) as db:
        rows = db.execute(
            "SELECT address FROM deposit_addresses",
        ).fetchall()
    for (address,) in rows:
        assert address not in body


def test_account_deposit_panel_requires_auth(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()

    response = client.get("/account/deposit-panel")

    assert response.status_code == 401
    assert response.data.decode("utf-8", errors="replace") == "Unauthorized"


def test_account_deposit_panel_contains_addresses_after_login(tmp_path: Path):
    db_path = _init_seed(tmp_path)
    client = site_app.app.test_client()
    _login_seed_user(client)

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
