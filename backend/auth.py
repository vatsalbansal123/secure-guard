"""API-key authentication for SecureGuard.

Model: developer-tool style API keys (like OpenAI / Snyk / Stripe), not user
sessions. Keys are high-entropy random tokens, so they are stored as a fast
SHA-256 hash (NOT bcrypt — that is for low-entropy human passwords) and are
shown to the user exactly once at creation.

Store: SQLite via SQLAlchemy (zero setup, easy to test). Override the path with
the SECUREGUARD_DB env var (the test suite points this at a temp file).
"""

import hashlib
import os
import secrets
from datetime import datetime, timezone

from fastapi import Header, HTTPException, Request, status
from sqlalchemy import Boolean, DateTime, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

# A readable prefix makes keys recognizable in logs/UI (like `sk_` for OpenAI).
KEY_PREFIX = "sg_"

DB_PATH = os.getenv(
    "SECUREGUARD_DB",
    os.path.join(os.path.dirname(__file__), "secureguard.db"),
)
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Only the hash is stored; the plaintext key never touches the database.
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    # First few chars of the plaintext, for display only ("sg_AbCd…").
    prefix: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)


Base.metadata.create_all(engine)


def hash_key(key: str) -> str:
    """Hash a key for storage/lookup. SHA-256 is sufficient for high-entropy keys."""
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> str:
    """A 256-bit URL-safe random key with a readable prefix."""
    return KEY_PREFIX + secrets.token_urlsafe(32)


def create_api_key(name: str = "default") -> str:
    """Create + persist a key, returning the plaintext ONCE (never stored)."""
    key = generate_api_key()
    with Session(engine) as session:
        row = ApiKey(key_hash=hash_key(key), name=name, prefix=key[:11] + "…")
        session.add(row)
        session.commit()
        key_id = row.id

    # Audit the key creation (Week 5). Imported lazily: storage imports Base/engine
    # from this module, so a top-level import would be circular.
    from storage import KEY_CREATED, log_event

    log_event(KEY_CREATED, key_id)
    return key


def require_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    """FastAPI dependency: validate the X-API-Key header on every request.

    Stashes the key hash (for rate limiting) and the key id (for per-developer
    ownership / IDOR checks on history) on request.state. Raises 401 if missing
    or invalid.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key"
        )

    digest = hash_key(x_api_key)
    with Session(engine) as session:
        row = session.scalar(
            select(ApiKey).where(ApiKey.key_hash == digest, ApiKey.active.is_(True))
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    request.state.api_key_hash = digest
    # The owning developer identity used to scope history queries.
    request.state.api_key_id = row.id
    return digest
