from __future__ import annotations

from datetime import datetime, timezone
from flask import (
    Flask,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from pathlib import Path
import base64
import bcrypt
import hashlib
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "agenttrace-site-four"
app.url_map.strict_slashes = False

DB_PATH = Path("/app/data/site.db")
SEED_EMAIL = "user1@example.com"
SEED_PASSWORD = "pass1"
SEED_NAME = "alex"
SEED_UID = "10243871"

COIN_LIST = (
    {"coin": "BTC", "name": "Bitcoin", "hot": True, "networks": ("BTC",)},
    {"coin": "ETH", "name": "Ethereum", "hot": True, "networks": ("ERC20",)},
    {
        "coin": "USDT",
        "name": "Tether USDT",
        "hot": True,
        "networks": ("TRC20", "ERC20"),
    },
    {"coin": "XRP", "name": "XRP", "hot": False, "networks": ()},
    {"coin": "EIGEN", "name": "EigenLayer", "hot": False, "networks": ()},
    {"coin": "SUSHI", "name": "SushiSwap", "hot": False, "networks": ()},
    {"coin": "TRUMP", "name": "OFFICIAL TRUMP", "hot": False, "networks": ()},
    {"coin": "IO", "name": "io.net", "hot": False, "networks": ()},
    {"coin": "AUDIO", "name": "Audius", "hot": False, "networks": ()},
    {"coin": "1INCH", "name": "1inch Network", "hot": False, "networks": ()},
    {"coin": "DOT", "name": "Polkadot", "hot": False, "networks": ()},
    {"coin": "BOME", "name": "BOOK OF MEME", "hot": False, "networks": ()},
    {"coin": "BERA", "name": "Berachain", "hot": False, "networks": ()},
    {"coin": "BTX", "name": "BitradeX Token", "hot": False, "networks": ()},
)
COIN_INDEX = {item["coin"]: item for item in COIN_LIST}

DEPOSIT_FAQ = (
    "How to top up your BitradeX Account (Web)",
    "How to top up your BitradeX Account (App)",
    "Frequently Asked Questions about Recharge",
    "recharge and withdrawal rates",
    "Why hasn't my recharge arrived?",
)


def _is_authenticated() -> bool:
    return session.get("user_id") is not None


def _require_auth():
    if not _is_authenticated():
        return redirect(url_for("login"))
    return None


def _get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def _close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                uid TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS deposit_addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                coin TEXT NOT NULL,
                network TEXT NOT NULL,
                address TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, coin, network),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS deposit_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                coin TEXT NOT NULL,
                network TEXT NOT NULL,
                address TEXT NOT NULL,
                txid TEXT NOT NULL,
                amount TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        db.commit()


def _hash_bits(seed: str, length: int) -> str:
    bits = ""
    counter = 0
    while len(bits) < length:
        digest = hashlib.sha256(f"{seed}:{counter}".encode("utf-8")).digest()
        bits += "".join(f"{byte:08b}" for byte in digest)
        counter += 1
    return bits[:length]


def _qr_svg_data_uri(text: str) -> str:
    grid = 21
    scale = 5
    margin = 6
    bits = _hash_bits(text, grid * grid)
    matrix = [
        [int(bits[row * grid + col]) for col in range(grid)]
        for row in range(grid)
    ]

    def apply_finder(x: int, y: int) -> None:
        for dy in range(7):
            for dx in range(7):
                on = dx in (0, 6) or dy in (0, 6) or (2 <= dx <= 4 and 2 <= dy <= 4)
                matrix[y + dy][x + dx] = 1 if on else 0

    apply_finder(0, 0)
    apply_finder(grid - 7, 0)
    apply_finder(0, grid - 7)

    size = grid * scale + margin * 2
    rects = []
    for y in range(grid):
        for x in range(grid):
            if matrix[y][x]:
                rects.append(
                    f"<rect x='{margin + x * scale}' y='{margin + y * scale}' "
                    f"width='{scale}' height='{scale}' />"
                )
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' "
        f"viewBox='0 0 {size} {size}'>"
        "<rect width='100%' height='100%' fill='white'/>"
        "<g fill='black'>"
        + "".join(rects)
        + "</g></svg>"
    )
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _select_chars(seed: bytes, alphabet: str, length: int) -> str:
    result = []
    counter = 0
    state = seed
    while len(result) < length:
        state = hashlib.sha256(state + counter.to_bytes(2, "big")).digest()
        for byte in state:
            result.append(alphabet[byte % len(alphabet)])
            if len(result) >= length:
                break
        counter += 1
    return "".join(result)


def _generate_address(user_id: int, coin: str, network: str) -> str:
    seed = hashlib.sha256(f"{user_id}:{coin}:{network}:site-four".encode("utf-8")).digest()
    if coin == "BTC":
        alphabet = "023456789acdefghjklmnpqrstuvwxyz"
        return "bc1" + _select_chars(seed, alphabet, 39)
    if network == "TRC20":
        alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        return "T" + _select_chars(seed, alphabet, 33)
    return "0x" + hashlib.sha256(seed).hexdigest()[:40]


def _ensure_user_addresses(db: sqlite3.Connection, user_id: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    for item in COIN_LIST:
        for network in item["networks"]:
            expected = _generate_address(user_id, item["coin"], network)
            row = db.execute(
                """
                SELECT id, address
                FROM deposit_addresses
                WHERE user_id = ? AND coin = ? AND network = ?
                """,
                (user_id, item["coin"], network),
            ).fetchone()
            if row is None:
                db.execute(
                    """
                    INSERT INTO deposit_addresses (user_id, coin, network, address, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, item["coin"], network, expected, now),
                )
            elif row["address"] != expected:
                db.execute(
                    """
                    UPDATE deposit_addresses
                    SET address = ?, created_at = ?
                    WHERE id = ?
                    """,
                    (expected, now, row["id"]),
                )
    db.commit()


def _seed_db() -> None:
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        row = db.execute(
            "SELECT id FROM users WHERE email = ?",
            (SEED_EMAIL,),
        ).fetchone()
        if row is None:
            password_hash = bcrypt.hashpw(
                SEED_PASSWORD.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")
            db.execute(
                """
                INSERT INTO users (email, password_hash, display_name, uid, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (SEED_EMAIL, password_hash, SEED_NAME, SEED_UID, now),
            )
            user_id = db.execute(
                "SELECT id FROM users WHERE email = ?",
                (SEED_EMAIL,),
            ).fetchone()["id"]
        else:
            user_id = row["id"]
        _ensure_user_addresses(db, user_id)


def _log_external_access() -> None:
    external_url = os.environ.get("AGENTTRACE_EXTERNAL_URL")
    if external_url:
        print(f"[agenttrace] external URL: {external_url}")
    else:
        print("[agenttrace] external URL not set; access via docker port mapping.")


def _current_user() -> sqlite3.Row | None:
    user_id = session.get("user_id")
    if user_id is None:
        return None
    db = _get_db()
    return db.execute(
        """
        SELECT id, email, display_name, uid, created_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()


@app.context_processor
def _inject_user():
    return {"user": _current_user()}


def _require_user():
    auth = _require_auth()
    if auth is not None:
        return None, auth
    user = _current_user()
    if user is None:
        session.clear()
        return None, redirect(url_for("login"))
    return user, None


def _require_user_api():
    if not _is_authenticated():
        return None, _api_error(401, "Unauthorized", 401)
    user = _current_user()
    if user is None:
        session.clear()
        return None, _api_error(401, "Unauthorized", 401)
    return user, None


def _api_ok(data):
    return jsonify({"code": 0, "message": "success", "data": data})


def _api_error(code: int, message: str, http_status: int = 400):
    return jsonify({"code": code, "message": message, "data": None}), http_status


def _coin_payloads() -> list[dict[str, object]]:
    return [
        {
            "coin": item["coin"],
            "name": item["name"],
            "hot": item["hot"],
            "available": bool(item["networks"]),
        }
        for item in COIN_LIST
    ]


def _address_for_coin_network(db: sqlite3.Connection, user_id: int, coin: str, network: str):
    row = db.execute(
        """
        SELECT address
        FROM deposit_addresses
        WHERE user_id = ? AND coin = ? AND network = ?
        """,
        (user_id, coin, network),
    ).fetchone()
    if row is None:
        _ensure_user_addresses(db, user_id)
        row = db.execute(
            """
            SELECT address
            FROM deposit_addresses
            WHERE user_id = ? AND coin = ? AND network = ?
            """,
            (user_id, coin, network),
        ).fetchone()
    if row is None:
        raise ValueError(f"missing address for {coin}:{network}")
    return row["address"]


def _uid_from_email(email: str) -> str:
    digest = hashlib.sha256(email.encode("utf-8")).hexdigest()
    numeric = int(digest[:8], 16) % 90_000_000 + 10_000_000
    return str(numeric)


@app.get("/")
def root():
    return redirect(url_for("home"))


@app.get("/en")
def home():
    return render_template("home.html", title="BitradeX-The Leading Global AI-Powered Crypto Trading Platform")


@app.get("/en/aibot")
def aibot():
    user = _current_user()
    return render_template(
        "aibot.html",
        title="BitradeX AiBot",
        user=user,
    )


@app.get("/en/markets")
def markets():
    return render_template(
        "generic_page.html",
        title="Markets | BitradeX",
        page_title="Markets",
        page_lead="Track spot and perpetual market performance across major crypto pairs.",
        bullets=(
            "24h leaders, losers, and volume shifts",
            "Cross-market sentiment and spread visibility",
            "Fast access to pairs for spot and futures execution",
        ),
    )


@app.get("/en/futures")
def futures():
    return render_template(
        "generic_page.html",
        title="Futures | BitradeX",
        page_title="Futures",
        page_lead="Manage leverage products with unified margin monitoring and risk controls.",
        bullets=(
            "USDT-margined and coin-margined contracts",
            "Position insights with mark price monitoring",
            "Risk tier and liquidation threshold guidance",
        ),
    )


@app.get("/en/trade")
def trade():
    return render_template(
        "generic_page.html",
        title="Trade | BitradeX",
        page_title="Trade",
        page_lead="Execute spot and derivatives orders with streamlined routing and depth insights.",
        bullets=(
            "Limit, market, and stop order support",
            "Order lifecycle visibility from submit to fill",
            "Integrated account and asset controls",
        ),
    )


@app.get("/en/invite-friend")
def invite_friend():
    return render_template(
        "generic_page.html",
        title="Invite Friend | BitradeX",
        page_title="Invite Friend",
        page_lead="Share your referral link and track invited account activity from one dashboard.",
        bullets=(
            "Referral payout snapshots",
            "Tiered invite rewards by completed volume",
            "Export-ready invite history",
        ),
    )


@app.get("/en/about")
def about():
    return render_template(
        "generic_page.html",
        title="About Us | BitradeX",
        page_title="About Us",
        page_lead="BitradeX is a global crypto trading platform focused on AI-assisted trading tools.",
        bullets=(
            "Multi-region product operations and support",
            "Centralized spot/futures/account experience",
            "Continuous platform and security improvements",
        ),
    )


@app.get("/en/contact")
def contact():
    return render_template(
        "generic_page.html",
        title="Contact Us | BitradeX",
        page_title="Contact Us",
        page_lead="Reach support for account, trading, and transfer inquiries across web and app.",
        bullets=(
            "24/7 ticket and live chat escalation paths",
            "Deposit and withdrawal troubleshooting",
            "Account security and verification support",
        ),
    )


@app.get("/en/login")
def login():
    registered = request.args.get("registered") == "1"
    return render_template("login.html", title="Login | BitradeX", error=None, registered=registered)


@app.post("/en/login")
def login_post():
    account = request.form.get("account", "").strip().lower()
    password = request.form.get("password", "")
    db = _get_db()
    row = db.execute(
        """
        SELECT id, email, password_hash
        FROM users
        WHERE lower(email) = ? OR lower(display_name) = ?
        """,
        (account, account),
    ).fetchone()
    if row is not None and password:
        stored_hash = row["password_hash"].encode("utf-8")
        if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            session["user_id"] = row["id"]
            session["user_email"] = row["email"]
            return redirect(url_for("trade"))
    return (
        render_template("login.html", title="Login | BitradeX", error="Invalid account or password.", registered=False),
        401,
    )


@app.get("/en/register")
def register():
    return render_template("register.html", title="Register | BitradeX", error=None, form={})


@app.post("/en/register")
def register_post():
    form = {
        "display_name": request.form.get("display_name", "").strip(),
        "email": request.form.get("email", "").strip().lower(),
    }
    password = request.form.get("password", "")
    confirm = request.form.get("password_confirm", "")
    errors = []
    if not form["display_name"]:
        errors.append("Display name is required.")
    if not form["email"] or "@" not in form["email"]:
        errors.append("Valid email is required.")
    if not password:
        errors.append("Password is required.")
    if password != confirm:
        errors.append("Passwords do not match.")

    db = _get_db()
    if form["email"]:
        exists = db.execute("SELECT id FROM users WHERE email = ?", (form["email"],)).fetchone()
        if exists is not None:
            errors.append("Email already exists.")

    if errors:
        return (
            render_template("register.html", title="Register | BitradeX", error=" ".join(errors), form=form),
            400,
        )

    now = datetime.now(timezone.utc).isoformat()
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    uid = _uid_from_email(form["email"])
    db.execute(
        """
        INSERT INTO users (email, password_hash, display_name, uid, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (form["email"], password_hash, form["display_name"], uid, now),
    )
    user_id = db.execute("SELECT id FROM users WHERE email = ?", (form["email"],)).fetchone()["id"]
    _ensure_user_addresses(db, user_id)
    return redirect(url_for("login", registered="1"))


@app.get("/en/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.get("/en/balance/overview")
def balance_overview():
    user, auth = _require_user()
    if auth is not None:
        return auth
    return render_template("balance_overview.html", title="Assets | BitradeX", user=user)


@app.get("/en/balance/spot-account")
def spot_account():
    user, auth = _require_user()
    if auth is not None:
        return auth
    return render_template("spot_account.html", title="Spot Account | BitradeX", user=user)


@app.get("/en/balance/deposit")
def deposit_page():
    user, auth = _require_user()
    if auth is not None:
        return auth
    return render_template(
        "deposit.html",
        title="BitradeX-The Leading Global AI-Powered Crypto Trading Platform",
        user=user,
        faq_items=DEPOSIT_FAQ,
    )


@app.get("/en/balance/withdraw")
def withdraw_page():
    user, auth = _require_user()
    if auth is not None:
        return auth
    return render_template("withdraw.html", title="Withdrawal | BitradeX", user=user)


@app.get("/en/balance/bills")
def balance_bills():
    user, auth = _require_user()
    if auth is not None:
        return auth
    return render_template("bills.html", title="Fund Flow | BitradeX", user=user)


@app.get("/v1/user/getUserInfo")
def api_user_info():
    user, auth = _require_user_api()
    if auth is not None:
        return auth
    return _api_ok(
        {
            "uid": user["uid"],
            "email": user["email"],
            "nickName": user["display_name"],
            "kycStatus": "UNVERIFIED",
        }
    )


@app.get("/v1/spot/wallet/deposit/hot/coin")
def api_hot_coin():
    user, auth = _require_user_api()
    if auth is not None:
        return auth
    return _api_ok(_coin_payloads())


@app.get("/v1/spot/wallet/deposit/network")
def api_networks():
    user, auth = _require_user_api()
    if auth is not None:
        return auth
    coin = request.args.get("coin", "").strip().upper()
    item = COIN_INDEX.get(coin)
    if item is None:
        return _api_error(4001, "Unknown coin.")
    networks = list(item["networks"])
    return _api_ok(
        [
            {
                "network": network,
                "busy": False,
                "confirmations": 12 if network == "BTC" else 24,
            }
            for network in networks
        ]
    )


@app.get("/v1/spot/wallet/deposit/address")
def api_deposit_address():
    user, auth = _require_user_api()
    if auth is not None:
        return auth
    coin = request.args.get("coin", "").strip().upper()
    network = request.args.get("network", "").strip().upper()
    item = COIN_INDEX.get(coin)
    if item is None:
        return _api_error(4001, "Unknown coin.")
    if network not in item["networks"]:
        return _api_error(4002, "Unknown transfer network.")
    db = _get_db()
    address = _address_for_coin_network(db, user["id"], coin, network)
    return _api_ok(
        {
            "coin": coin,
            "network": network,
            "address": address,
            "memo": "",
            "depositTip": "Please choose the same network as the coin charging platform to avoid loss of funds",
            "qrDataUri": _qr_svg_data_uri(address),
        }
    )


@app.get("/v1/spot/wallet/deposit/history")
def api_deposit_history():
    user, auth = _require_user_api()
    if auth is not None:
        return auth
    page = request.args.get("page", "1")
    size = request.args.get("size", "10")
    _ = (page, size)
    db = _get_db()
    rows = db.execute(
        """
        SELECT created_at, coin, amount, network, address, txid, status
        FROM deposit_history
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 10
        """,
        (user["id"],),
    ).fetchall()
    data = [
        {
            "time": row["created_at"],
            "assetName": row["coin"],
            "amt": row["amount"],
            "network": row["network"],
            "address": row["address"],
            "txid": row["txid"],
            "status": row["status"],
        }
        for row in rows
    ]
    return _api_ok({"list": data, "total": len(data)})


@app.get("/v1/spot/balance/public/currencies")
def api_currencies():
    return _api_ok(
        [
            {"currency": "USD", "symbol": "$"},
            {"currency": "EUR", "symbol": "€"},
        ]
    )


@app.get("/v1/spot/balance/public/price/currency/country-currency")
def api_country_currency():
    return _api_ok({"countryCode": "GB", "currency": "USD"})


@app.get("/v1/app/public/app/country")
def api_country():
    return _api_ok({"country": "GB", "lang": "en"})


@app.get("/v1/future-u/user/user/collection/list")
def api_user_collection():
    user, auth = _require_user_api()
    if auth is not None:
        return auth
    return _api_ok([])


@app.get("/v1/spot/market/public/ticker/24h")
def api_spot_ticker():
    return _api_ok(
        [
            {"symbol": "BTC_USDT", "price": "68400.20"},
            {"symbol": "ETH_USDT", "price": "3540.10"},
        ]
    )


@app.get("/v1/future-u/market/public/q/tickers")
def api_futures_ticker():
    return _api_ok(
        [
            {"symbol": "BTCUSDT_PERP", "price": "68420.00"},
            {"symbol": "ETHUSDT_PERP", "price": "3541.20"},
        ]
    )


@app.get("/v1/user/kyc/getRealAuthInfo")
def api_kyc_info():
    user, auth = _require_user_api()
    if auth is not None:
        return auth
    return _api_ok({"status": "UNVERIFIED"})


@app.get("/v1/message/private/user-letter/list")
def api_user_letters():
    user, auth = _require_user_api()
    if auth is not None:
        return auth
    return _api_ok({"list": [], "unread": 0})


@app.get("/v1/spot/balance/public/price/currency/convert")
def api_currency_convert():
    converts = request.args.get("converts", "usd,btc")
    _ = converts
    return _api_ok({"usd": "1.00", "btc": "0.0000146"})


@app.get("/v1/spot/account/symbol-star/list")
def api_symbol_star():
    user, auth = _require_user_api()
    if auth is not None:
        return auth
    return _api_ok([])


if __name__ == "__main__":
    _init_db()
    _seed_db()
    _log_external_access()
    app.run(host="0.0.0.0", port=8000)
