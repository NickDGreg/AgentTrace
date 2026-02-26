# Generated DB Schema Notes

Generated from local SQLite files on 2026-02-26.

## sites/login_deposit_basic/data/site.db

- users
  - id INTEGER PRIMARY KEY AUTOINCREMENT
  - email TEXT UNIQUE NOT NULL
  - password_hash TEXT NOT NULL
  - created_at TEXT NOT NULL

- deposit_addresses
  - id INTEGER PRIMARY KEY AUTOINCREMENT
  - user_id INTEGER NOT NULL
  - chain TEXT NOT NULL
  - address TEXT NOT NULL
  - created_at TEXT NOT NULL
  - FOREIGN KEY user_id -> users(id)

## sites/register_basic/data/site.db

- users
  - id INTEGER PRIMARY KEY AUTOINCREMENT
  - email TEXT UNIQUE NOT NULL
  - password_hash TEXT NOT NULL
  - created_at TEXT NOT NULL

- deposit_addresses
  - id INTEGER PRIMARY KEY AUTOINCREMENT
  - user_id INTEGER NOT NULL
  - chain TEXT NOT NULL
  - address TEXT NOT NULL
  - created_at TEXT NOT NULL
  - FOREIGN KEY user_id -> users(id)

## sites/site_one/data/site.db

- users
  - id INTEGER PRIMARY KEY AUTOINCREMENT
  - email TEXT UNIQUE NOT NULL
  - password_hash TEXT NOT NULL
  - uid TEXT NOT NULL
  - created_at TEXT NOT NULL
  - display_name TEXT NOT NULL DEFAULT ''

- deposit_addresses
  - id INTEGER PRIMARY KEY AUTOINCREMENT
  - user_id INTEGER NOT NULL
  - asset TEXT NOT NULL
  - chain TEXT NOT NULL
  - address TEXT NOT NULL
  - created_at TEXT NOT NULL
  - UNIQUE(user_id, asset, chain)
  - FOREIGN KEY user_id -> users(id)
