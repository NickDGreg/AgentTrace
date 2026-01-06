import sqlite3
from pathlib import Path

from sites.login_deposit_basic import app as site_app


def _init_seed(tmp_path: Path):
    db_path = tmp_path / "site.db"
    site_app.DB_PATH = db_path
    site_app._init_db()
    site_app._seed_db()
    return db_path


def test_login_page_serves(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()

    response = client.get("/login")

    assert response.status_code == 200
    assert b"<form" in response.data


def test_deposit_redirects_without_auth(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()

    response = client.get("/deposit")

    assert response.status_code == 302
    assert "/login" in response.headers.get("Location", "")


def test_seed_user_and_addresses_exist(tmp_path: Path):
    db_path = _init_seed(tmp_path)
    with sqlite3.connect(db_path) as db:
        user = db.execute(
            "SELECT email FROM users WHERE email = ?",
            (site_app.SEED_EMAIL,),
        ).fetchone()
        assert user is not None

        rows = db.execute(
            """
            SELECT chain, address
            FROM deposit_addresses
            WHERE user_id = (SELECT id FROM users WHERE email = ?)
            """,
            (site_app.SEED_EMAIL,),
        ).fetchall()
        assert {row[0] for row in rows} == set(site_app.SEED_ADDRESSES.keys())


def test_deposit_contains_addresses_after_login(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()

    response = client.post(
        "/login",
        data={"email": site_app.SEED_EMAIL, "password": site_app.SEED_PASSWORD},
        follow_redirects=False,
    )
    assert response.status_code == 302

    response = client.get("/deposit")
    body = response.data.decode("utf-8", errors="replace")

    assert "BTC" in body
    assert "ETH" in body
    assert site_app.SEED_ADDRESSES["BTC"] in body
    assert site_app.SEED_ADDRESSES["ETH"] in body
