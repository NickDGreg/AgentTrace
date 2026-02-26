from __future__ import annotations

from datetime import datetime, timezone
from flask import Flask, g, redirect, render_template, request, session, url_for
from pathlib import Path
import base64
import bcrypt
import hashlib
import sqlite3

app = Flask(__name__)
app.secret_key = "agenttrace-site-one"
app.url_map.strict_slashes = False

DB_PATH = Path("/app/data/site.db")
SEED_EMAIL = "user1@example.com"
SEED_PASSWORD = "pass1"
ASSET_ORDER = ["USDT", "BTC", "ETH", "USDC"]
ASSET_CONFIG = {
    "USDT": {"chain": "TRC20", "kind": "tron"},
    "USDC": {"chain": "TRC20", "kind": "tron"},
    "BTC": {"chain": "BTC", "kind": "btc"},
    "ETH": {"chain": "ERC20", "kind": "eth"},
}


def _is_authenticated() -> bool:
    return session.get("user_email") is not None


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


def _ensure_user_schema(db: sqlite3.Connection) -> None:
    columns = {row[1] for row in db.execute("PRAGMA table_info(users)")}
    if "display_name" not in columns:
        db.execute(
            "ALTER TABLE users ADD COLUMN display_name TEXT NOT NULL DEFAULT ''"
        )
    db.execute(
        "UPDATE users SET display_name = '' WHERE display_name IS NULL"
    )


def _init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                uid TEXT NOT NULL,
                created_at TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT ''
            )
            """
        )
        _ensure_user_schema(db)
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS deposit_addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                asset TEXT NOT NULL,
                chain TEXT NOT NULL,
                address TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, asset, chain),
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
    # Deterministic QR-like pattern without external dependencies.
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


def _uid_for_email(email: str) -> str:
    digest = hashlib.sha256(email.encode("utf-8")).hexdigest()
    numeric = int(digest[:8], 16) % 900000 + 100000
    return str(numeric)


def _mask_email(email: str) -> str:
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    left = local[:2] if len(local) >= 2 else local
    right = domain[-6:] if len(domain) >= 6 else domain
    return f"{left}|****|{right}"


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


def _generate_address(user_id: int, asset: str) -> str:
    seed = hashlib.sha256(f"{user_id}:{asset}:goldentradr".encode("utf-8")).digest()
    kind = ASSET_CONFIG[asset]["kind"]
    if kind == "btc":
        alphabet = "023456789acdefghjklmnpqrstuvwxyz"
        return "bc1" + _select_chars(seed, alphabet, 39)
    if kind == "eth":
        return "0x" + hashlib.sha256(seed).hexdigest()[:40]
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    return "T" + _select_chars(seed, alphabet, 33)


def _ensure_user_addresses(db: sqlite3.Connection, user_id: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    for asset in ASSET_ORDER:
        config = ASSET_CONFIG[asset]
        existing = db.execute(
            """
            SELECT id FROM deposit_addresses
            WHERE user_id = ? AND asset = ? AND chain = ?
            """,
            (user_id, asset, config["chain"]),
        ).fetchone()
        if existing is None:
            address = _generate_address(user_id, asset)
            db.execute(
                """
                INSERT INTO deposit_addresses (user_id, asset, chain, address, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, asset, config["chain"], address, now),
            )
    db.commit()


def _address_map_for_user(
    db: sqlite3.Connection, user_id: int
) -> dict[str, dict[str, str]]:
    rows = db.execute(
        """
        SELECT asset, chain, address
        FROM deposit_addresses
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchall()

    address_map = {}
    for row in rows:
        address_map[row["asset"]] = {
            "address": row["address"],
            "chain": row["chain"],
            "qr": _qr_svg_data_uri(row["address"]),
        }
    return address_map


def _seed_db() -> None:
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        user = db.execute(
            "SELECT id, email, uid, display_name FROM users WHERE email = ?",
            (SEED_EMAIL,),
        ).fetchone()
        if user is None:
            password_hash = bcrypt.hashpw(
                SEED_PASSWORD.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")
            uid = _uid_for_email(SEED_EMAIL)
            db.execute(
                """
                INSERT INTO users (email, password_hash, uid, created_at, display_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (SEED_EMAIL, password_hash, uid, now, "Golden Pilot"),
            )
            user_id = db.execute(
                "SELECT id FROM users WHERE email = ?", (SEED_EMAIL,)
            ).fetchone()["id"]
        else:
            user_id = user["id"]
            if not user["uid"]:
                db.execute(
                    "UPDATE users SET uid = ? WHERE id = ?",
                    (_uid_for_email(SEED_EMAIL), user_id),
                )
            if not user["display_name"]:
                db.execute(
                    "UPDATE users SET display_name = ? WHERE id = ?",
                    ("Golden Pilot", user_id),
                )
        _ensure_user_addresses(db, user_id)


@app.context_processor
def _inject_globals():
    return {
        "is_authenticated": _is_authenticated(),
        "current_email": session.get("user_email"),
    }


@app.get("/")
def home() -> str:
    return render_template("home.html", title="GoldenTradr | Home")


@app.get("/register")
def register() -> str:
    return render_template("register.html", title="GoldenTradr | Register", error=None)


@app.post("/register")
def register_post():
    display_name = request.form.get("display_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    agree = request.form.get("agree")

    errors = []
    if not display_name:
        errors.append("Name is required.")
    if not email:
        errors.append("Email is required.")
    if not password:
        errors.append("Password is required.")
    if agree != "on":
        errors.append("You must accept the agreement.")

    if errors:
        return (
            render_template(
                "register.html",
                title="GoldenTradr | Register",
                error=" ".join(errors),
                form={"email": email, "display_name": display_name},
            ),
            400,
        )

    db = _get_db()
    existing = db.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    if existing is not None:
        return (
            render_template(
                "register.html",
                title="GoldenTradr | Register",
                error="Account already exists.",
                form={"email": email, "display_name": display_name},
            ),
            400,
        )

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )
    uid = _uid_for_email(email)
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        """
        INSERT INTO users (email, password_hash, uid, created_at, display_name)
        VALUES (?, ?, ?, ?, ?)
        """,
        (email, password_hash, uid, now, display_name),
    )
    user_id = db.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,),
    ).fetchone()["id"]
    _ensure_user_addresses(db, user_id)
    return redirect(url_for("login"))


@app.get("/login")
def login() -> str:
    return render_template("login.html", title="GoldenTradr | Sign In", error=None)


@app.post("/login")
def login_post():
    account = request.form.get("account", "").strip().lower()
    password = request.form.get("password", "")
    db = _get_db()
    row = db.execute(
        "SELECT id, email, password_hash FROM users WHERE email = ?",
        (account,),
    ).fetchone()
    if row is not None and password:
        stored_hash = row["password_hash"].encode("utf-8")
        if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            session["user_email"] = row["email"]
            session["user_id"] = row["id"]
            return redirect(url_for("index"))

    return (
        render_template(
            "login.html",
            title="GoldenTradr | Sign In",
            error="Invalid account or password.",
        ),
        401,
    )


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.get("/index")
def index() -> str:
    auth = _require_auth()
    if auth is not None:
        return auth
    return render_template("index.html", title="GoldenTradr | Portfolio")


@app.get("/account")
def account() -> str:
    auth = _require_auth()
    if auth is not None:
        return auth

    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    db = _get_db()
    user = db.execute(
        "SELECT id, email, uid FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if user is None:
        return redirect(url_for("login"))

    _ensure_user_addresses(db, user_id)
    return render_template(
        "account.html",
        title="GoldenTradr | Account",
        masked_email=_mask_email(user["email"]),
        uid=user["uid"],
    )


@app.get("/account/deposit-panel")
def account_deposit_panel():
    if not _is_authenticated():
        return "Unauthorized", 401

    user_id = session.get("user_id")
    if user_id is None:
        return "Unauthorized", 401

    db = _get_db()
    _ensure_user_addresses(db, user_id)
    address_map = _address_map_for_user(db, user_id)
    default_asset = ASSET_ORDER[0]
    return render_template(
        "_deposit_panel.html",
        address_map=address_map,
        asset_order=ASSET_ORDER,
        default_asset=default_asset,
    )


@app.get("/market")
def market() -> str:
    return render_template("market.html", title="GoldenTradr | Market")


@app.get("/loans")
def loans() -> str:
    return render_template("loans.html", title="GoldenTradr | Loans")


@app.get("/ai-trading")
def ai_trading() -> str:
    return render_template("ai_trading.html", title="GoldenTradr | Golden AI Trading")


if __name__ == "__main__":
    _init_db()
    _seed_db()
    app.run(host="0.0.0.0", port=8000)
