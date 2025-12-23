from __future__ import annotations

from datetime import datetime, timezone
from flask import Flask, g, redirect, request, session, url_for
from pathlib import Path
import bcrypt
import sqlite3

app = Flask(__name__)
app.secret_key = "agenttrace-login-deposit-basic"

DB_PATH = Path("/app/data/site.db")
SEED_EMAIL = "user1@example.com"
SEED_PASSWORD = "pass1"
SEED_ADDRESSES = {
    "BTC": "bc1qagenttrace0login0deposit0basic0000000000000000",
    "ETH": "0xagenttrace0login0deposit0basic0000000000000000000",
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


def _init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
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
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        db.commit()


def _seed_db() -> None:
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        user = db.execute(
            "SELECT id, email FROM users WHERE email = ?",
            (SEED_EMAIL,),
        ).fetchone()
        if user is None:
            password_hash = bcrypt.hashpw(
                SEED_PASSWORD.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")
            db.execute(
                "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                (SEED_EMAIL, password_hash, now),
            )
            user_id = db.execute(
                "SELECT id FROM users WHERE email = ?", (SEED_EMAIL,)
            ).fetchone()["id"]
        else:
            user_id = user["id"]

        for chain, address in SEED_ADDRESSES.items():
            existing = db.execute(
                "SELECT id FROM deposit_addresses WHERE user_id = ? AND chain = ?",
                (user_id, chain),
            ).fetchone()
            if existing is None:
                db.execute(
                    """
                    INSERT INTO deposit_addresses (user_id, chain, address, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, chain, address, now),
                )
        db.commit()


@app.get("/login")
def login() -> str:
    return """
    <h1>Login</h1>
    <form method="post" action="/login">
      <label>Email <input type="email" name="email" required></label><br>
      <label>Password <input type="password" name="password" required></label><br>
      <button type="submit">Sign in</button>
    </form>
    """, 200


@app.post("/login")
def login_post():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    db = _get_db()
    row = db.execute(
        "SELECT id, email, password_hash FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    if row is not None and password:
        stored_hash = row["password_hash"].encode("utf-8")
        if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            return (
                "<p>Invalid credentials.</p><p><a href='/login'>Try again</a></p>",
                401,
            )
        session["user_email"] = row["email"]
        session["user_id"] = row["id"]
        return redirect(url_for("dashboard"))
    return (
        "<p>Invalid credentials.</p><p><a href='/login'>Try again</a></p>",
        401,
    )


@app.get("/")
def index() -> str:
    return redirect(url_for("login"))


@app.get("/dashboard")
def dashboard():
    auth = _require_auth()
    if auth is not None:
        return auth
    return """
    <h1>Dashboard</h1>
    <p><a href="/deposit">Go to deposit page</a></p>
    """, 200


@app.get("/deposit")
def deposit():
    auth = _require_auth()
    if auth is not None:
        return auth
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    db = _get_db()
    rows = db.execute(
        "SELECT chain, address FROM deposit_addresses WHERE user_id = ? ORDER BY chain",
        (user_id,),
    ).fetchall()
    items = "\n".join(
        f"<li><strong>{row['chain']}</strong>: <span>{row['address']}</span></li>"
        for row in rows
    )
    return f"""
    <h1>Deposit</h1>
    <ul>
      {items}
    </ul>
    """, 200


if __name__ == "__main__":
    _init_db()
    _seed_db()
    app.run(host="0.0.0.0", port=8000)
