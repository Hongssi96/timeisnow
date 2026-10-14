"""Ports: abstract interfaces for cross-cutting concerns, with default adapters.

서비스 계층은 구현체가 아니라 이 추상 클래스에만 의존한다. 구체 어댑터는
조립 지점(app/meetings/wiring.py, FastAPI Depends)에서 주입하므로 테스트는
같은 생성자에 가짜 구현을 넣어 DB·HTTP 없이 규칙을 검증할 수 있다.
"""
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime, timezone
import secrets

from app.auth import security
from app.common.database import database


class Clock(ABC):
    """Time source for expiry and schedule checks."""

    @abstractmethod
    def now(self) -> datetime:
        """Return the current moment as an aware datetime."""


class UtcClock(Clock):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class Database(ABC):
    """Transaction scope. One yielded connection is one transaction."""

    @abstractmethod
    def connect(self):
        """Context manager yielding a transaction-scoped connection."""


class PostgresDatabase(Database):
    @contextmanager
    def connect(self):
        with database() as connection:
            yield connection


class Identity(ABC):
    """Who is calling, and how fast they are allowed to call."""

    @abstractmethod
    def authenticate(self, connection, request, write=False):
        """Resolve the signed-in user id or raise 401/403."""

    @abstractmethod
    def throttle(self, connection, scope, value, seconds, maximum):
        """Count one call against the bucket or raise 429 RATE_LIMITED."""


class SessionIdentity(Identity):
    def authenticate(self, connection, request, write=False):
        return security.authenticated(connection, request, write)

    def throttle(self, connection, scope, value, seconds, maximum):
        _, secret, _ = security.settings()
        key = security.bucket(connection, scope, value, seconds, maximum, secret)
        security.increment(connection, key)


class TokenIssuer(ABC):
    """One-time secrets that are shared outside the database."""

    @abstractmethod
    def issue(self) -> str:
        """Return a fresh opaque token; only its hash may be stored."""


class UrlSafeTokenIssuer(TokenIssuer):
    def issue(self) -> str:
        return secrets.token_urlsafe(32)
