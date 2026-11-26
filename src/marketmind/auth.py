"""Local user accounts and browser-session storage."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import uuid4

from marketmind.settings import OUTPUT_DIR

AUTH_DB = OUTPUT_DIR / "accounts.sqlite"
SESSION_COOKIE = "marketmind_session"
SESSION_MAX_AGE = 30 * 24 * 60 * 60
PASSWORD_MIN_LENGTH = 12
_DUMMY_SALT = bytes.fromhex("000102030405060708090a0b0c0d0e0f")


class AccountAlreadyExists(Exception):
    """Raised when an account already uses the supplied email."""


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    AUTH_DB.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(AUTH_DB, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            salt BLOB NOT NULL,
            password_hash BLOB NOT NULL,
            created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at INTEGER NOT NULL
        );
        """
    )
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _password_hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)


def create_account(email: str, password: str) -> dict:
    normalized_email = email.strip().casefold()
    if "@" not in normalized_email or len(normalized_email) > 254:
        raise ValueError("Enter a valid email address.")
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters.")

    user_id = uuid4().hex
    salt = secrets.token_bytes(16)
    digest = _password_hash(password, salt)
    try:
        with _connect() as connection:
            connection.execute(
                "INSERT INTO users (id, email, salt, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, normalized_email, salt, digest, int(time.time())),
            )
    except sqlite3.IntegrityError as exc:
        raise AccountAlreadyExists from exc
    return {"id": user_id, "email": normalized_email}


def authenticate(email: str, password: str) -> dict | None:
    normalized_email = email.strip().casefold()
    with _connect() as connection:
        row = connection.execute(
            "SELECT id, email, salt, password_hash FROM users WHERE email = ?",
            (normalized_email,),
        ).fetchone()
    if row is None:
        _password_hash(password, _DUMMY_SALT)
        return None
    if not hmac.compare_digest(_password_hash(password, row["salt"]), row["password_hash"]):
        return None
    return {"id": row["id"], "email": row["email"]}


def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
    expires_at = int(time.time()) + SESSION_MAX_AGE
    with _connect() as connection:
        connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (int(time.time()),))
        connection.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (token_hash, user_id, expires_at),
        )
    return token


def user_for_session(token: str | None) -> dict | None:
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode("ascii", errors="ignore")).hexdigest()
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT users.id, users.email
            FROM sessions JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at > ?
            """,
            (token_hash, int(time.time())),
        ).fetchone()
    return {"id": row["id"], "email": row["email"]} if row else None


def delete_session(token: str | None) -> None:
    if not token:
        return
    token_hash = hashlib.sha256(token.encode("ascii", errors="ignore")).hexdigest()
    with _connect() as connection:
        connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))


def cookie_secure() -> bool:
    return os.getenv("AUTH_COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes"}
