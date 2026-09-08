"""Authentication helpers for DataBoom API sessions.

Purpose:
    Keep password hashing, session-token generation, and seed-user bootstrapping
    out of route handlers.

Data flow:
    register/login payload -> password hash verification -> state-store user
    record -> bearer session token.

Why this approach:
    The API needs real auth semantics before it can be deployed publicly, but
    Phase 2 does not need a full identity provider dependency in the backend.
    PBKDF2 from the Python standard library gives us salted password hashes
    without adding a new package, and the state-store protocol keeps the later
    Supabase Auth integration isolated from product/run code.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

from databoom.api.models import AppUserResponse, UserRecord
from databoom.core.config import Settings

PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 600_000


def normalize_login_id(value: str) -> str:
    """Return the canonical login identifier used for lookups."""

    return value.strip().lower()


def normalize_email(value: str) -> str:
    """Return the canonical email value used for uniqueness checks."""

    return value.strip().lower()


def hash_password(password: str) -> str:
    """Create a salted PBKDF2 password hash.

    The encoded format stores the algorithm and iteration count beside the salt
    and digest. That lets us increase the iteration count later while still
    verifying older accounts.
    """

    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    )
    return f"{PASSWORD_HASH_ALGORITHM}${PASSWORD_HASH_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    """Return whether a plain password matches an encoded PBKDF2 hash."""

    try:
        algorithm, iterations, salt, expected_digest = encoded_hash.split("$", maxsplit=3)
        if algorithm != PASSWORD_HASH_ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
    except (TypeError, ValueError):
        return False

    return secrets.compare_digest(digest, expected_digest)


def new_session_token() -> str:
    """Create an opaque bearer token for an authenticated browser session."""

    return secrets.token_urlsafe(32)


def user_response_from_record(user: UserRecord) -> AppUserResponse:
    """Return the safe public shape for an internal user record."""

    return AppUserResponse(
        user_id=user.user_id,
        login_id=user.login_id,
        email=user.email,
        name=user.name,
    )


def build_user_record(
    *,
    login_id: str,
    email: str,
    name: str,
    password: str,
    created_at: datetime | None = None,
) -> UserRecord:
    """Create a normalized, hashed user record ready for persistence."""

    normalized_login_id = normalize_login_id(login_id)
    normalized_email = normalize_email(email)
    timestamp = created_at or datetime.now(UTC)
    return UserRecord(
        user_id=f"user_{secrets.token_hex(12)}",
        login_id=normalized_login_id,
        email=normalized_email,
        name=name.strip(),
        password_hash=hash_password(password),
        created_at=timestamp,
        updated_at=timestamp,
    )


def ensure_seed_user(store, settings: Settings) -> None:
    """Create a configured seed user for local or managed deployments.

    Render deployments can set `DATABOOM_SEED_LOGIN_ID` and
    `DATABOOM_SEED_PASSWORD` to guarantee a reviewer/admin account exists. Local
    and test environments also get a low-risk default account so the app can be
    opened immediately after `docker compose up`.
    """

    seed_login_id = settings.seed_login_id
    seed_password = settings.seed_password.get_secret_value() if settings.seed_password else None
    seed_email = settings.seed_email
    seed_name = settings.seed_name

    if seed_password is None and settings.environment in {"local", "test", "docker"}:
        seed_login_id = seed_login_id or "operator"
        seed_password = "databoom-local"
        seed_email = seed_email or "operator@databoom.local"
        seed_name = seed_name or "DataBoom Operator"

    if not seed_login_id or not seed_password:
        return

    normalized_login_id = normalize_login_id(seed_login_id)
    if store.get_user_by_login_id(normalized_login_id) is not None:
        return

    store.save_user(
        build_user_record(
            login_id=normalized_login_id,
            email=seed_email or f"{normalized_login_id}@databoom.local",
            name=seed_name or "DataBoom Operator",
            password=seed_password,
        )
    )
