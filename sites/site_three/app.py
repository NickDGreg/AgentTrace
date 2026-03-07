from __future__ import annotations

from datetime import datetime, timezone
from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
from pathlib import Path
import base64
import bcrypt
import hashlib
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "agenttrace-site-three"
app.url_map.strict_slashes = False

DB_PATH = Path("/app/data/site.db")
SEED_EMAIL = "user1@example.com"
SEED_PASSWORD = "pass1"
SEED_NAME = "john"
SEED_COUNTRY = "United Kingdom"
SEED_PHONE = "07446722733"

CRYPTO_ASSETS = ("Bitcoin", "Ethereum", "Bitcoin Cash")
ASSET_TO_CHAIN = {
    "Bitcoin": "BTC",
    "Ethereum": "ETH",
    "Bitcoin Cash": "BCH",
}
CHAIN_ORDER = ("BTC", "ETH", "BCH")
DEPOSIT_MIN_AMOUNT = 1.0
DEPOSIT_MAX_AMOUNT = 1_000_000.0
STATIC_ADDRESSES = {
    "BTC": "bc1qnhgc9vlhra74ay2yqlyrp5ppq9czpdylagqhq7",
    "ETH": "0x9a850f5a9f9634f8f5f0a7483d8f0f0c9cd19c2f",
    "BCH": "bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a",
}

TOP_NAV = (
    {"key": "deposit", "label": "Deposit", "href": "/deposit"},
    {
        "key": "withdrawal",
        "label": "Withdrawal",
        "href": "/wallet-overview?modal=withdraw",
    },
    {"key": "staking", "label": "Staking", "href": "/staking"},
    {"key": "live-chat", "label": "Live Chat", "href": "/live-chat"},
    {"key": "trade", "label": "Trade", "href": "/trade"},
    {"key": "news", "label": "News", "href": "/news"},
    {"key": "auto-trader", "label": "AUTO TRADER", "href": "/auto-trader"},
)

HOME_MENU = (
    {"label": "About us", "endpoint": "about_us"},
    {"label": "Price", "endpoint": "price"},
    {"label": "Information", "endpoint": "information"},
    {"label": "Trade view", "endpoint": "trade_view"},
    {"label": "Contact us", "endpoint": "contact_us"},
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
                country TEXT NOT NULL,
                phone TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS deposit_addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chain TEXT NOT NULL,
                address TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, chain),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                payment_method TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        db.commit()


def _generate_address(chain: str) -> str:
    return STATIC_ADDRESSES[chain]


def _ensure_user_addresses(db: sqlite3.Connection, user_id: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    for chain in CHAIN_ORDER:
        expected = _generate_address(chain)
        row = db.execute(
            """
            SELECT id, address
            FROM deposit_addresses
            WHERE user_id = ? AND chain = ?
            """,
            (user_id, chain),
        ).fetchone()
        if row is None:
            db.execute(
                """
                INSERT INTO deposit_addresses (user_id, chain, address, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, chain, expected, now),
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
                INSERT INTO users (email, password_hash, display_name, country, phone, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    SEED_EMAIL,
                    password_hash,
                    SEED_NAME,
                    SEED_COUNTRY,
                    SEED_PHONE,
                    now,
                ),
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
        SELECT id, email, display_name, country, phone, created_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()


def _require_user():
    auth = _require_auth()
    if auth is not None:
        return None, auth
    user = _current_user()
    if user is None:
        session.clear()
        return None, redirect(url_for("login"))
    return user, None


def _require_user_json():
    if not _is_authenticated():
        return None, (jsonify({"error": "Unauthorized"}), 401)
    user = _current_user()
    if user is None:
        session.clear()
        return None, (jsonify({"error": "Unauthorized"}), 401)
    return user, None


def _address_for_chain(db: sqlite3.Connection, user_id: int, chain: str) -> str:
    row = db.execute(
        """
        SELECT address
        FROM deposit_addresses
        WHERE user_id = ? AND chain = ?
        """,
        (user_id, chain),
    ).fetchone()
    if row is None:
        _ensure_user_addresses(db, user_id)
        row = db.execute(
            """
            SELECT address
            FROM deposit_addresses
            WHERE user_id = ? AND chain = ?
            """,
            (user_id, chain),
        ).fetchone()
    if row is None:
        raise ValueError(f"missing address for chain {chain}")
    return row["address"]


def _parse_amount(raw_value: str) -> float | None:
    try:
        amount = float(raw_value)
    except (TypeError, ValueError):
        return None
    if amount <= 0:
        return None
    return round(amount, 2)


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
    scale = 6
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
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' "
        f"height='{size}' viewBox='0 0 {size} {size}'>"
        "<rect width='100%' height='100%' fill='white'/>"
        "<g fill='black'>"
        + "".join(rects)
        + "</g></svg>"
    )
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _nav_items() -> list[dict[str, str]]:
    return [dict(item) for item in TOP_NAV]


def _render_cfd(page: str, user: sqlite3.Row, payload: dict):
    state = {
        "page": page,
        "user": {
            "display_name": user["display_name"],
            "email": user["email"],
            "country": user["country"],
        },
        "navItems": _nav_items(),
        "assetOptions": list(CRYPTO_ASSETS),
        "payload": payload,
    }
    return render_template("cfd_shell.html", title="Trading Platform", initial_state=state)


@app.get("/")
def index():
    return render_template(
        "home.html",
        title="Titan Trade Global LTD",
        menu_items=HOME_MENU,
    )


@app.get("/about-us")
def about_us():
    return render_template(
        "info_page.html",
        title="About us | Titan Trade",
        menu_items=HOME_MENU,
        page_title="About us",
        page_intro="Titan Trade Global LTD builds synthetic trading workflows for benchmark-driven automation testing.",
        bullets=(
            "Multi-asset execution environment with realistic UX patterns",
            "Identity verification and wallet flows available in account panel",
            "Operational support and account controls available 24/7",
        ),
    )


@app.get("/price")
def price():
    return render_template(
        "info_page.html",
        title="Price | Titan Trade",
        menu_items=HOME_MENU,
        page_title="Price",
        page_intro="Transparent cost model for market execution, wallet funding, and premium account services.",
        bullets=(
            "Entry funding from $100 to $1,000,000",
            "Tiered account plans and spread-sensitive execution",
            "Dedicated upgrade paths for higher-volume traders",
        ),
    )


@app.get("/information")
def information():
    return render_template(
        "info_page.html",
        title="Information | Titan Trade",
        menu_items=HOME_MENU,
        page_title="Information",
        page_intro="Core policies, account operation guidance, and trading process notes.",
        bullets=(
            "Onboarding and profile verification procedures",
            "Funding, withdrawal, and risk policy disclosures",
            "Security controls and account protection guidance",
        ),
    )


@app.get("/trade-view")
def trade_view():
    return render_template(
        "info_page.html",
        title="Trade view | Titan Trade",
        menu_items=HOME_MENU,
        page_title="Trade view",
        page_intro="Platform trade-view modules provide watchlists, charting context, and execution shortcuts.",
        bullets=(
            "Cross-market monitoring from one dashboard",
            "Fast handoff from signal to order workflow",
            "Integrated portfolio and exposure summaries",
        ),
    )


@app.route("/contact-us", methods=["GET", "POST"])
def contact_us():
    submitted = request.method == "POST"
    return render_template(
        "info_page.html",
        title="Contact us | Titan Trade",
        menu_items=HOME_MENU,
        page_title="Contact us",
        page_intro="Reach support for account verification, payments, and trade operations.",
        bullets=(
            "Live chat and ticketing assistance",
            "Wallet transfer and payment confirmation help",
            "Escalation path for account security events",
        ),
        submitted=submitted,
    )


@app.get("/about")
def about_alias():
    return redirect(url_for("about_us"))


@app.get("/contact")
def contact_alias():
    return redirect(url_for("contact_us"))


@app.get("/register")
def register():
    return render_template(
        "register.html",
        title="Register | Titan Trade",
        error=None,
        form={},
        registered=False,
    )


@app.post("/register")
def register_post():
    form = {
        "display_name": request.form.get("display_name", "").strip(),
        "email": request.form.get("email", "").strip().lower(),
        "country": request.form.get("country", "").strip(),
        "phone": request.form.get("phone", "").strip(),
    }
    password = request.form.get("password", "")
    password_confirm = request.form.get("password_confirm", "")

    errors = []
    if not form["display_name"]:
        errors.append("First name is required.")
    if not form["email"] or "@" not in form["email"]:
        errors.append("Valid email is required.")
    if not form["country"]:
        errors.append("Country is required.")
    if not form["phone"]:
        errors.append("Phone is required.")
    if not password:
        errors.append("Password is required.")
    if password != password_confirm:
        errors.append("Passwords do not match.")

    db = _get_db()
    if form["email"]:
        existing = db.execute(
            "SELECT id FROM users WHERE email = ?",
            (form["email"],),
        ).fetchone()
        if existing is not None:
            errors.append("An account with this email already exists.")

    if errors:
        return (
            render_template(
                "register.html",
                title="Register | Titan Trade",
                error=" ".join(errors),
                form=form,
                registered=False,
            ),
            400,
        )

    now = datetime.now(timezone.utc).isoformat()
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )
    db.execute(
        """
        INSERT INTO users (email, password_hash, display_name, country, phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            form["email"],
            password_hash,
            form["display_name"],
            form["country"],
            form["phone"],
            now,
        ),
    )
    user_id = db.execute(
        "SELECT id FROM users WHERE email = ?",
        (form["email"],),
    ).fetchone()["id"]
    _ensure_user_addresses(db, user_id)
    return redirect(url_for("login", registered="1"))


@app.get("/login")
def login():
    registered = request.args.get("registered") == "1"
    return render_template(
        "login.html",
        title="Log in | Titan Trade",
        error=None,
        registered=registered,
    )


@app.post("/login")
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
            return redirect(url_for("dashboard"))

    return (
        render_template(
            "login.html",
            title="Log in | Titan Trade",
            error="Invalid account or password.",
            registered=False,
        ),
        401,
    )


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/dashboard")
def dashboard():
    user, auth = _require_user()
    if auth is not None:
        return auth
    payload = {
        "activeNav": "trade",
        "headline": "Welcome back",
        "subline": "Monitor account status, wallet balance, and market activity from one panel.",
        "balance": "$0.00",
        "equity": "$0.00",
        "open_positions": 0,
    }
    return _render_cfd("dashboard", user, payload)


@app.get("/deposit")
def deposit():
    user, auth = _require_user()
    if auth is not None:
        return auth
    payload = {
        "activeNav": "deposit",
        "balance": "$0.00",
        "minAmount": DEPOSIT_MIN_AMOUNT,
        "maxAmount": DEPOSIT_MAX_AMOUNT,
    }
    return _render_cfd("deposit", user, payload)


@app.get("/wallet-overview")
def wallet_overview():
    user, auth = _require_user()
    if auth is not None:
        return auth
    payload = {
        "activeNav": "withdrawal",
        "balance": "$0.00",
        "equity": "$0.00",
        "modal": request.args.get("modal", "").strip().lower(),
    }
    return _render_cfd("wallet-overview", user, payload)


@app.get("/withdrawal")
def withdrawal():
    user, auth = _require_user()
    if auth is not None:
        return auth
    return redirect(url_for("wallet_overview", modal="withdraw"))


@app.get("/staking")
def staking():
    user, auth = _require_user()
    if auth is not None:
        return auth
    payload = {
        "activeNav": "staking",
        "headline": "Staking Center",
        "subline": "Allocate idle wallet funds to fixed-term staking pools.",
    }
    return _render_cfd("simple-page", user, payload)


@app.get("/live-chat")
def live_chat():
    user, auth = _require_user()
    if auth is not None:
        return auth
    payload = {
        "activeNav": "live-chat",
        "headline": "Live Chat",
        "subline": "Support agents are available for account and payment questions.",
    }
    return _render_cfd("simple-page", user, payload)


@app.get("/trade")
def trade():
    user, auth = _require_user()
    if auth is not None:
        return auth
    payload = {
        "activeNav": "trade",
        "headline": "Trade Console",
        "subline": "Execution queue, market watch, and quick order controls.",
    }
    return _render_cfd("simple-page", user, payload)


@app.get("/news")
def news():
    user, auth = _require_user()
    if auth is not None:
        return auth
    payload = {
        "activeNav": "news",
        "headline": "Market News",
        "subline": "Session-ready market updates and macro snapshots.",
    }
    return _render_cfd("simple-page", user, payload)


@app.get("/auto-trader")
def auto_trader():
    user, auth = _require_user()
    if auth is not None:
        return auth
    payload = {
        "activeNav": "auto-trader",
        "headline": "Auto Trader",
        "subline": "Manage strategy presets and risk limits for automated execution.",
    }
    return _render_cfd("simple-page", user, payload)


@app.get("/api/deposit/address")
def api_deposit_address():
    user, auth = _require_user_json()
    if auth is not None:
        return auth

    asset = request.args.get("asset", "Bitcoin").strip()
    amount = _parse_amount(request.args.get("amount", ""))
    if amount is None:
        return jsonify({"error": "Valid deposit amount is required."}), 400
    if amount < DEPOSIT_MIN_AMOUNT or amount > DEPOSIT_MAX_AMOUNT:
        return (
            jsonify(
                {
                    "error": (
                        f"Deposit amount must be between ${DEPOSIT_MIN_AMOUNT:.2f} "
                        f"and ${DEPOSIT_MAX_AMOUNT:,.2f}."
                    )
                }
            ),
            400,
        )
    if asset not in ASSET_TO_CHAIN:
        return jsonify({"error": "Unsupported crypto asset."}), 400

    db = _get_db()
    chain = ASSET_TO_CHAIN[asset]
    address = _address_for_chain(db, user["id"], chain)
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        """
        INSERT INTO deposits (user_id, amount, payment_method, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (user["id"], amount, asset, now),
    )
    db.commit()
    return jsonify(
        {
            "asset": asset,
            "chain": chain,
            "amount": amount,
            "address": address,
            "qr_data_uri": _qr_svg_data_uri(address),
        }
    )


if __name__ == "__main__":
    _init_db()
    _seed_db()
    _log_external_access()
    app.run(host="0.0.0.0", port=8000)
