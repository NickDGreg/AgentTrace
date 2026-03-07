import sqlite3
from pathlib import Path

from sites.site_two import app as site_app


def _init_seed(tmp_path: Path) -> Path:
    db_path = tmp_path / "site_two.db"
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


def _seed_addresses(db_path: Path) -> dict[str, str]:
    with sqlite3.connect(db_path) as db:
        rows = db.execute(
            """
            SELECT chain, address
            FROM deposit_addresses
            WHERE user_id = (SELECT id FROM users WHERE email = ?)
            """,
            (site_app.SEED_EMAIL,),
        ).fetchall()
    return {chain: address for chain, address in rows}


def test_home_page_is_public(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()

    response = client.get("/")
    body = response.data.decode("utf-8", errors="replace")

    assert response.status_code == 200
    assert "Get more freedom in the markets." in body
    assert 'href="/login"' in body
    assert 'href="/register"' in body


def test_public_info_pages_are_accessible(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()

    pages = [
        ("/about", "About Equity Axis"),
        ("/contact", "Contact"),
        ("/faq", "Frequently Asked Questions"),
    ]
    for path, expected_text in pages:
        response = client.get(path)
        body = response.data.decode("utf-8", errors="replace")
        assert response.status_code == 200
        assert expected_text in body

    post_response = client.post(
        "/contact",
        data={"name": "Agent", "email": "agent@example.com", "message": "Hi"},
    )
    post_body = post_response.data.decode("utf-8", errors="replace")
    assert post_response.status_code == 200
    assert "Message submitted." in post_body


def test_addresses_are_deterministic_per_user_and_different_across_users(tmp_path: Path):
    db_path = _init_seed(tmp_path)
    client = site_app.app.test_client()

    register_response = client.post(
        "/register",
        data={
            "display_name": "alice",
            "email": "alice@example.com",
            "country": "United Kingdom",
            "phone": "07000000000",
            "password": "pass1",
            "password_confirm": "pass1",
        },
        follow_redirects=False,
    )
    assert register_response.status_code == 302

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
    assert set(seed_map.keys()) == {"BCH", "BTC", "ETH"}
    assert set(alice_map.keys()) == {"BCH", "BTC", "ETH"}
    assert seed_map != alice_map


def test_deposit_page_excludes_wallet_addresses(tmp_path: Path):
    db_path = _init_seed(tmp_path)
    addresses = _seed_addresses(db_path)

    client = site_app.app.test_client()
    _login_seed_user(client)
    response = client.get("/dashboard/deposits")

    assert response.status_code == 200
    body = response.data.decode("utf-8", errors="replace")
    for address in addresses.values():
        assert address not in body


def test_payment_route_requires_deposit_id(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()
    _login_seed_user(client)

    response = client.get("/dashboard/payment")

    assert response.status_code == 302
    assert "/dashboard/deposits" in response.headers.get("Location", "")


def test_deposit_checkout_reveals_only_selected_chain_address(tmp_path: Path):
    db_path = _init_seed(tmp_path)
    addresses = _seed_addresses(db_path)
    client = site_app.app.test_client()
    _login_seed_user(client)

    response = client.post(
        "/dashboard/newdeposit",
        data={"amount": "100", "payment_mode": "Bitcoin"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    location = response.headers.get("Location", "")
    assert "/dashboard/payment?deposit_id=" in location

    payment = client.get(location)
    body = payment.data.decode("utf-8", errors="replace")

    assert payment.status_code == 200
    assert addresses["BTC"] in body
    assert addresses["ETH"] not in body
    assert addresses["BCH"] not in body


def test_signal_checkout_reveals_selected_payment_chain_address(tmp_path: Path):
    db_path = _init_seed(tmp_path)
    addresses = _seed_addresses(db_path)
    client = site_app.app.test_client()
    _login_seed_user(client)

    response = client.post(
        "/dashboard/signalnewdeposit",
        data={"signal": "Momentum Signals", "paymethod": "Ethereum"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    location = response.headers.get("Location", "")
    assert "/dashboard/singnalpayment?order_id=" in location

    payment = client.get(location)
    body = payment.data.decode("utf-8", errors="replace")

    assert payment.status_code == 200
    assert "Momentum Signals" in body
    assert addresses["ETH"] in body
    assert addresses["BTC"] not in body


def test_secondary_dashboard_pages_have_real_content(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()
    _login_seed_user(client)

    pages = [
        ("/dashboard/withdrawals", "Withdraw Funds"),
        ("/dashboard/accounthistory", "Account Trading History"),
        ("/dashboard/deposit_hist", "Transaction Records"),
        ("/dashboard/buy-plan", "Account Upgrade Plans"),
        ("/dashboard/verify-account", "KYC Verification"),
    ]
    for path, expected_text in pages:
        response = client.get(path)
        body = response.data.decode("utf-8", errors="replace")
        assert response.status_code == 200
        assert expected_text in body
        assert "intentionally lightweight" not in body
