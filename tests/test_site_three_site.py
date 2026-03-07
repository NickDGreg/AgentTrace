import sqlite3
from pathlib import Path

from sites.site_three import app as site_app


def _init_seed(tmp_path: Path) -> Path:
    db_path = tmp_path / "site_three.db"
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


def _all_static_addresses() -> list[str]:
    return list(site_app.STATIC_ADDRESSES.values())


def test_home_page_is_public(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()

    response = client.get("/")
    body = response.data.decode("utf-8", errors="replace")

    assert response.status_code == 200
    assert "Trade &amp; enter" in body
    assert "the $1M" in body
    assert "Open Trading Account" in body


def test_public_information_pages_are_accessible(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()

    pages = [
        ("/about-us", "About us"),
        ("/price", "Price"),
        ("/information", "Information"),
        ("/trade-view", "Trade view"),
        ("/contact-us", "Contact us"),
    ]
    for path, expected_text in pages:
        response = client.get(path)
        body = response.data.decode("utf-8", errors="replace")
        assert response.status_code == 200
        assert expected_text in body

    submitted = client.post(
        "/contact-us",
        data={"name": "Agent", "email": "agent@example.com", "message": "hello"},
    )
    submitted_body = submitted.data.decode("utf-8", errors="replace")
    assert submitted.status_code == 200
    assert "Message submitted." in submitted_body


def test_addresses_are_constant_for_all_users(tmp_path: Path):
    db_path = _init_seed(tmp_path)
    client = site_app.app.test_client()

    register = client.post(
        "/register",
        data={
            "display_name": "alice",
            "email": "alice@example.com",
            "country": "UK",
            "phone": "07000000000",
            "password": "pass1",
            "password_confirm": "pass1",
        },
        follow_redirects=False,
    )
    assert register.status_code == 302

    with sqlite3.connect(db_path) as db:
        db.row_factory = sqlite3.Row
        seed_id = db.execute(
            "SELECT id FROM users WHERE email = ?",
            (site_app.SEED_EMAIL,),
        ).fetchone()["id"]
        alice_id = db.execute(
            "SELECT id FROM users WHERE email = ?",
            ("alice@example.com",),
        ).fetchone()["id"]

        seed_rows = db.execute(
            "SELECT chain, address FROM deposit_addresses WHERE user_id = ? ORDER BY chain",
            (seed_id,),
        ).fetchall()
        alice_rows = db.execute(
            "SELECT chain, address FROM deposit_addresses WHERE user_id = ? ORDER BY chain",
            (alice_id,),
        ).fetchall()

    seed_map = {row["chain"]: row["address"] for row in seed_rows}
    alice_map = {row["chain"]: row["address"] for row in alice_rows}

    assert seed_map == site_app.STATIC_ADDRESSES
    assert alice_map == site_app.STATIC_ADDRESSES


def test_deposit_page_excludes_wallet_addresses(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()
    _login_seed_user(client)

    response = client.get("/deposit")
    body = response.data.decode("utf-8", errors="replace")

    assert response.status_code == 200
    for address in _all_static_addresses():
        assert address not in body


def test_deposit_address_api_requires_auth(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()

    response = client.get("/api/deposit/address?asset=Bitcoin&amount=100")
    payload = response.get_json()

    assert response.status_code == 401
    assert payload == {"error": "Unauthorized"}


def test_deposit_address_api_returns_selected_wallet(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()
    _login_seed_user(client)

    response = client.get("/api/deposit/address?asset=Bitcoin&amount=100")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["asset"] == "Bitcoin"
    assert payload["chain"] == "BTC"
    assert payload["address"] == site_app.STATIC_ADDRESSES["BTC"]
    assert payload["amount"] == 100.0


def test_cfd_routes_return_app_shell(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()
    _login_seed_user(client)

    pages = [
        "/dashboard",
        "/deposit",
        "/wallet-overview?modal=withdraw",
        "/staking",
        "/live-chat",
        "/trade",
        "/news",
        "/auto-trader",
    ]

    for path in pages:
        response = client.get(path)
        body = response.data.decode("utf-8", errors="replace")
        assert response.status_code == 200
        assert 'id="root"' in body
        assert "initial-state" in body
