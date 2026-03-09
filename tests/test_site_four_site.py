import sqlite3
from pathlib import Path

from sites.site_four import app as site_app


def _init_seed(tmp_path: Path) -> Path:
    db_path = tmp_path / "site_four.db"
    site_app.DB_PATH = db_path
    site_app._init_db()
    site_app._seed_db()
    return db_path


def _login_seed_user(client):
    response = client.post(
        "/en/login",
        data={"account": site_app.SEED_EMAIL, "password": site_app.SEED_PASSWORD},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/en/trade" in response.headers.get("Location", "")


def _address_map(db_path: Path, email: str) -> dict[tuple[str, str], str]:
    with sqlite3.connect(db_path) as db:
        db.row_factory = sqlite3.Row
        user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        assert user is not None
        rows = db.execute(
            """
            SELECT coin, network, address
            FROM deposit_addresses
            WHERE user_id = ?
            ORDER BY coin, network
            """,
            (user["id"],),
        ).fetchall()
    return {(row["coin"], row["network"]): row["address"] for row in rows}


def test_home_page_is_public(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()

    response = client.get("/en")
    body = response.data.decode("utf-8", errors="replace")

    assert response.status_code == 200
    assert "Champions Endorse, Intelligence Leads" in body
    assert "Why Choose BitradeX" in body
    assert "Invest Now" in body


def test_public_pages_are_accessible(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()

    pages = [
        ("/en/aibot", "Your Intelligent Trading Co-Pilot"),
        ("/en/markets", "Track spot and perpetual market performance"),
        ("/en/futures", "Manage leverage products"),
        ("/en/trade", "Execute spot and derivatives orders"),
        ("/en/invite-friend", "Share your referral link"),
        ("/en/about", "BitradeX is a global crypto trading platform"),
        ("/en/contact", "Reach support for account, trading, and transfer inquiries"),
    ]
    for path, expected in pages:
        response = client.get(path)
        body = response.data.decode("utf-8", errors="replace")
        assert response.status_code == 200
        assert expected in body


def test_balance_deposit_requires_auth(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()

    response = client.get("/en/balance/deposit", follow_redirects=False)

    assert response.status_code == 302
    assert "/en/login" in response.headers.get("Location", "")


def test_spot_account_requires_auth(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()

    response = client.get("/en/balance/spot-account", follow_redirects=False)

    assert response.status_code == 302
    assert "/en/login" in response.headers.get("Location", "")


def test_deposit_page_excludes_wallet_addresses(tmp_path: Path):
    db_path = _init_seed(tmp_path)
    addresses = _address_map(db_path, site_app.SEED_EMAIL)
    client = site_app.app.test_client()
    _login_seed_user(client)

    response = client.get("/en/balance/deposit")
    body = response.data.decode("utf-8", errors="replace")

    assert response.status_code == 200
    assert "Cryptocurrency Deposit" in body
    for address in addresses.values():
        assert address not in body


def test_spot_account_page_contains_deposit_and_withdraw_actions(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()
    _login_seed_user(client)

    response = client.get("/en/balance/spot-account")
    body = response.data.decode("utf-8", errors="replace")

    assert response.status_code == 200
    assert "Spot Account" in body
    assert 'href="/en/balance/deposit"' in body
    assert 'href="/en/balance/withdraw"' in body


def test_private_api_requires_auth(tmp_path: Path):
    _init_seed(tmp_path)
    client = site_app.app.test_client()

    response = client.get("/v1/spot/wallet/deposit/hot/coin")
    payload = response.get_json()

    assert response.status_code == 401
    assert payload["code"] == 401
    assert payload["message"] == "Unauthorized"


def test_deposit_api_returns_selected_network_address(tmp_path: Path):
    db_path = _init_seed(tmp_path)
    expected = _address_map(db_path, site_app.SEED_EMAIL)
    client = site_app.app.test_client()
    _login_seed_user(client)

    networks_resp = client.get("/v1/spot/wallet/deposit/network?coin=USDT")
    networks_payload = networks_resp.get_json()
    assert networks_resp.status_code == 200
    assert [item["network"] for item in networks_payload["data"]] == ["TRC20", "ERC20"]

    btc_resp = client.get("/v1/spot/wallet/deposit/address?coin=BTC&network=BTC")
    btc_payload = btc_resp.get_json()["data"]
    assert btc_resp.status_code == 200
    assert btc_payload["address"] == expected[("BTC", "BTC")]

    usdt_trc = client.get("/v1/spot/wallet/deposit/address?coin=USDT&network=TRC20")
    usdt_erc = client.get("/v1/spot/wallet/deposit/address?coin=USDT&network=ERC20")
    trc_payload = usdt_trc.get_json()["data"]
    erc_payload = usdt_erc.get_json()["data"]

    assert usdt_trc.status_code == 200
    assert usdt_erc.status_code == 200
    assert trc_payload["address"] == expected[("USDT", "TRC20")]
    assert erc_payload["address"] == expected[("USDT", "ERC20")]
    assert trc_payload["address"] != erc_payload["address"]


def test_addresses_are_deterministic_per_user_and_different_across_users(tmp_path: Path):
    db_path = _init_seed(tmp_path)
    client = site_app.app.test_client()

    register = client.post(
        "/en/register",
        data={
            "display_name": "alice",
            "email": "alice@example.com",
            "password": "pass1",
            "password_confirm": "pass1",
        },
        follow_redirects=False,
    )
    assert register.status_code == 302

    seed_map = _address_map(db_path, site_app.SEED_EMAIL)
    alice_map = _address_map(db_path, "alice@example.com")

    assert seed_map.keys() == alice_map.keys()
    assert seed_map != alice_map
    assert ("BTC", "BTC") in seed_map
    assert ("ETH", "ERC20") in seed_map
    assert ("USDT", "TRC20") in seed_map
    assert ("USDT", "ERC20") in seed_map
