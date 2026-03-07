from __future__ import annotations

from datetime import datetime, timezone
from flask import Flask, g, redirect, render_template, request, session, url_for
from pathlib import Path
import base64
import bcrypt
import hashlib
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "agenttrace-site-two"
app.url_map.strict_slashes = False

DB_PATH = Path("/app/data/site.db")
SEED_EMAIL = "user1@example.com"
SEED_PASSWORD = "pass1"
SEED_NAME = "john"
SEED_COUNTRY = "United Kingdom"
SEED_PHONE = "07446722733"

PAYMENT_OPTIONS = ("Bitcoin Cash", "Ethereum", "Bitcoin")
PAYMENT_TO_CHAIN = {
    "Bitcoin Cash": "BCH",
    "Ethereum": "ETH",
    "Bitcoin": "BTC",
}

SIGNAL_PLANS = {
    "Momentum Signals": 1500,
    "Breakout Signals": 3000,
    "Buying Oversold": 3600,
    "Trend Signal": 7000,
}

UPGRADE_PLANS = (
    {
        "name": "Starter Account",
        "min_deposit": 500,
        "profit_range": "3,500 - 5,000",
        "features": (
            "Low minimum entry",
            "Dedicated onboarding",
            "Basic risk controls",
        ),
    },
    {
        "name": "Classic Account",
        "min_deposit": 5000,
        "profit_range": "45,000 - 50,000",
        "features": (
            "Priority execution",
            "Advanced tools",
            "Expert analysis feed",
        ),
    },
    {
        "name": "Platinum Account",
        "min_deposit": 10000,
        "profit_range": "99,999+",
        "features": (
            "Full executive tier",
            "High-touch support",
            "Portfolio coordination",
        ),
    },
)

HISTORY_ROWS = (
    ("2026-03-06 10:40", "EURUSD", "Buy", "0.20", "+210.00"),
    ("2026-03-05 15:11", "BTCUSD", "Sell", "0.05", "-84.20"),
    ("2026-03-04 09:27", "XAUUSD", "Buy", "0.15", "+125.40"),
)

TRANSACTION_ROWS = (
    ("TX-22031", "Deposit", "Bitcoin", "$100.00", "Pending"),
    ("TX-22028", "Signal", "Ethereum", "$1,500.00", "Processing"),
    ("TX-22013", "Withdrawal", "Bank Transfer", "$50.00", "Rejected"),
)

DEPOSIT_MINIMUM = 10.0
CHAIN_ORDER = ("BTC", "ETH", "BCH")


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
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS signal_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                signal_name TEXT NOT NULL,
                amount REAL NOT NULL,
                payment_method TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        db.commit()


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


def _generate_address(user_id: int, chain: str) -> str:
    seed = hashlib.sha256(f"{user_id}:{chain}:site-two".encode("utf-8")).digest()
    if chain == "BTC":
        alphabet = "023456789acdefghjklmnpqrstuvwxyz"
        return "bc1" + _select_chars(seed, alphabet, 39)
    if chain == "ETH":
        return "0x" + hashlib.sha256(seed).hexdigest()[:40]
    alphabet = "023456789acdefghjklmnpqrstuvwxyz"
    return "bitcoincash:q" + _select_chars(seed, alphabet, 41)


def _ensure_user_addresses(db: sqlite3.Connection, user_id: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    for chain in CHAIN_ORDER:
        expected_address = _generate_address(user_id, chain)
        row = db.execute(
            """
            SELECT id, address FROM deposit_addresses
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
                (user_id, chain, expected_address, now),
            )
        elif row["address"] != expected_address:
            db.execute(
                """
                UPDATE deposit_addresses
                SET address = ?, created_at = ?
                WHERE id = ?
                """,
                (expected_address, now, row["id"]),
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


def _dashboard_time() -> str:
    return datetime.now().strftime("%A %d %B %Y %I:%M:%S %p")


def _format_registration(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return value
    return dt.strftime("%a, %b %d, %Y %I:%M %p")


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


def _render_dashboard(template: str, user: sqlite3.Row, active_page: str, **kwargs):
    return render_template(
        template,
        user=user,
        active_page=active_page,
        now_display=_dashboard_time(),
        registration_date=_format_registration(user["created_at"]),
        payment_options=PAYMENT_OPTIONS,
        **kwargs,
    )


def _parse_amount(raw_value: str) -> float | None:
    try:
        amount = float(raw_value)
    except (TypeError, ValueError):
        return None
    if amount <= 0:
        return None
    return round(amount, 2)


@app.get("/")
def index():
    return render_template(
        "home.html",
        title="site_two | Home",
    )


@app.get("/about")
def about():
    return render_template(
        "about.html",
        title="site_two | About",
    )


@app.route("/contact", methods=["GET", "POST"])
def contact():
    submitted = request.method == "POST"
    return render_template(
        "contact.html",
        title="site_two | Contact",
        submitted=submitted,
    )


@app.get("/faq")
def faq():
    return render_template(
        "faq.html",
        title="site_two | FAQ",
    )


@app.get("/register")
def register():
    return render_template(
        "register.html",
        title="Create Account | site_two",
        error=None,
        form={},
        show_notice=False,
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
    if not form["email"]:
        errors.append("Email is required.")
    if "@" not in form["email"]:
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
                title="Create Account | site_two",
                error=" ".join(errors),
                form=form,
                show_notice=False,
            ),
            400,
        )

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )
    now = datetime.now(timezone.utc).isoformat()
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
    show_registered = request.args.get("registered") == "1"
    return render_template(
        "login.html",
        title="Sign In | site_two",
        error=None,
        registered=show_registered,
        show_notice=True,
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
            title="Sign In | site_two",
            error="Invalid account or password.",
            registered=False,
            show_notice=True,
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
    return _render_dashboard("dashboard.html", user, active_page="account")


@app.get("/dashboard/account-settings")
def account_settings():
    user, auth = _require_user()
    if auth is not None:
        return auth
    return _render_dashboard("account_settings.html", user, active_page="account-settings")


@app.get("/dashboard/deposits")
def deposits():
    user, auth = _require_user()
    if auth is not None:
        return auth
    return _render_dashboard("deposits.html", user, active_page="deposit", error=None)


@app.post("/dashboard/newdeposit")
def new_deposit():
    user, auth = _require_user()
    if auth is not None:
        return auth

    amount = _parse_amount(request.form.get("amount", ""))
    payment_method = request.form.get("payment_mode", "").strip()

    if amount is None or amount < DEPOSIT_MINIMUM:
        return (
            _render_dashboard(
                "deposits.html",
                user,
                active_page="deposit",
                error=f"Minimum deposit is ${DEPOSIT_MINIMUM:.0f}.",
            ),
            400,
        )
    if payment_method not in PAYMENT_TO_CHAIN:
        return (
            _render_dashboard(
                "deposits.html",
                user,
                active_page="deposit",
                error="Select a valid payment method.",
            ),
            400,
        )

    db = _get_db()
    now = datetime.now(timezone.utc).isoformat()
    cursor = db.execute(
        """
        INSERT INTO deposits (user_id, amount, payment_method, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (user["id"], amount, payment_method, now),
    )
    db.commit()
    return redirect(url_for("payment", deposit_id=cursor.lastrowid))


@app.get("/dashboard/payment")
def payment():
    user, auth = _require_user()
    if auth is not None:
        return auth

    deposit_id = request.args.get("deposit_id", type=int)
    if deposit_id is None:
        return redirect(url_for("deposits"))

    db = _get_db()
    deposit = db.execute(
        """
        SELECT id, amount, payment_method
        FROM deposits
        WHERE id = ? AND user_id = ?
        """,
        (deposit_id, user["id"]),
    ).fetchone()
    if deposit is None:
        return redirect(url_for("deposits"))

    chain = PAYMENT_TO_CHAIN[deposit["payment_method"]]
    address = _address_for_chain(db, user["id"], chain)
    submitted = request.args.get("submitted") == "1"
    return _render_dashboard(
        "payment.html",
        user,
        active_page="deposit",
        deposit=deposit,
        chain=chain,
        address=address,
        qr_data_uri=_qr_svg_data_uri(address),
        proof_submitted=submitted,
    )


@app.post("/dashboard/savedeposit")
def save_deposit():
    user, auth = _require_user()
    if auth is not None:
        return auth
    deposit_id = request.form.get("deposit_id", type=int)
    if deposit_id is None:
        return redirect(url_for("deposits"))

    db = _get_db()
    row = db.execute(
        "SELECT id FROM deposits WHERE id = ? AND user_id = ?",
        (deposit_id, user["id"]),
    ).fetchone()
    if row is None:
        return redirect(url_for("deposits"))
    return redirect(url_for("payment", deposit_id=deposit_id, submitted="1"))


@app.get("/dashboard/signal")
def signal():
    user, auth = _require_user()
    if auth is not None:
        return auth
    return _render_dashboard(
        "signal.html",
        user,
        active_page="signal",
        signal_plans=SIGNAL_PLANS,
        error=None,
    )


@app.post("/dashboard/signalnewdeposit")
def signal_new_deposit():
    user, auth = _require_user()
    if auth is not None:
        return auth

    signal_name = request.form.get("signal", "").strip()
    payment_method = request.form.get("paymethod", "").strip()
    if signal_name not in SIGNAL_PLANS:
        return (
            _render_dashboard(
                "signal.html",
                user,
                active_page="signal",
                signal_plans=SIGNAL_PLANS,
                error="Select a valid signal plan.",
            ),
            400,
        )
    if payment_method not in PAYMENT_TO_CHAIN:
        return (
            _render_dashboard(
                "signal.html",
                user,
                active_page="signal",
                signal_plans=SIGNAL_PLANS,
                error="Select a valid payment method.",
            ),
            400,
        )

    amount = float(SIGNAL_PLANS[signal_name])
    db = _get_db()
    now = datetime.now(timezone.utc).isoformat()
    cursor = db.execute(
        """
        INSERT INTO signal_orders (user_id, signal_name, amount, payment_method, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user["id"], signal_name, amount, payment_method, now),
    )
    db.commit()
    return redirect(url_for("signal_payment", order_id=cursor.lastrowid))


@app.get("/dashboard/singnalpayment")
def signal_payment():
    user, auth = _require_user()
    if auth is not None:
        return auth

    order_id = request.args.get("order_id", type=int)
    if order_id is None:
        return redirect(url_for("signal"))

    db = _get_db()
    order = db.execute(
        """
        SELECT id, signal_name, amount, payment_method
        FROM signal_orders
        WHERE id = ? AND user_id = ?
        """,
        (order_id, user["id"]),
    ).fetchone()
    if order is None:
        return redirect(url_for("signal"))

    chain = PAYMENT_TO_CHAIN[order["payment_method"]]
    address = _address_for_chain(db, user["id"], chain)
    submitted = request.args.get("submitted") == "1"
    return _render_dashboard(
        "signal_payment.html",
        user,
        active_page="signal",
        order=order,
        chain=chain,
        address=address,
        qr_data_uri=_qr_svg_data_uri(address),
        proof_submitted=submitted,
    )


@app.post("/dashboard/savesignaldeposit")
def save_signal_deposit():
    user, auth = _require_user()
    if auth is not None:
        return auth
    order_id = request.form.get("order_id", type=int)
    if order_id is None:
        return redirect(url_for("signal"))

    db = _get_db()
    row = db.execute(
        "SELECT id FROM signal_orders WHERE id = ? AND user_id = ?",
        (order_id, user["id"]),
    ).fetchone()
    if row is None:
        return redirect(url_for("signal"))
    return redirect(url_for("signal_payment", order_id=order_id, submitted="1"))


@app.route("/dashboard/withdrawals", methods=["GET", "POST"])
def withdrawals():
    user, auth = _require_user()
    if auth is not None:
        return auth
    submitted = False
    amount = request.form.get("amount", "").strip()
    method = request.form.get("method", "").strip()
    destination = request.form.get("destination", "").strip()
    if request.method == "POST":
        submitted = bool(amount and method and destination)
    return _render_dashboard(
        "withdrawals.html",
        user,
        active_page="withdraw",
        submitted=submitted,
    )


@app.get("/dashboard/accounthistory")
def account_history():
    user, auth = _require_user()
    if auth is not None:
        return auth
    return _render_dashboard(
        "history.html",
        user,
        active_page="history",
        rows=HISTORY_ROWS,
    )


@app.get("/dashboard/deposit_hist")
def transactions():
    user, auth = _require_user()
    if auth is not None:
        return auth
    return _render_dashboard(
        "transactions.html",
        user,
        active_page="transactions",
        rows=TRANSACTION_ROWS,
    )


@app.get("/dashboard/buy-plan")
def buy_plan():
    user, auth = _require_user()
    if auth is not None:
        return auth
    return _render_dashboard(
        "buy_plan.html",
        user,
        active_page="upgrade",
        plans=UPGRADE_PLANS,
        signal_plans=SIGNAL_PLANS,
    )


@app.route("/dashboard/verify-account", methods=["GET", "POST"])
def verify_account():
    user, auth = _require_user()
    if auth is not None:
        return auth
    submitted = False
    if request.method == "POST":
        id_type = request.form.get("id_type", "").strip()
        document_number = request.form.get("document_number", "").strip()
        submitted = bool(id_type and document_number)
    return _render_dashboard(
        "verify_account.html",
        user,
        active_page="account",
        submitted=submitted,
    )


if __name__ == "__main__":
    _init_db()
    _seed_db()
    _log_external_access()
    app.run(host="0.0.0.0", port=8000)
