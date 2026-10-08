"""Local PostgreSQL connection helpers; never log connection settings or passwords."""
from contextlib import contextmanager
import os
from pathlib import Path

import psycopg
from psycopg import Error as DatabaseError
from psycopg.rows import dict_row
from dotenv import dotenv_values

from app.common.errors import AuthError

ROOT = Path(__file__).resolve().parents[3]


def connect_db():
    # Explicit process settings take precedence; empty values remain invalid.
    settings = {**dotenv_values(ROOT / ".env"), **os.environ}
    required = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
    if any(not settings.get(key) for key in required):
        raise ValueError("Required PostgreSQL settings are missing.")
    return psycopg.connect(
        host=settings.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(settings.get("POSTGRES_PORT", "5432")),
        dbname=settings["POSTGRES_DB"],
        user=settings["POSTGRES_USER"],
        password=settings["POSTGRES_PASSWORD"],
        connect_timeout=5,
        application_name="timeisnow-backend",
    )


@contextmanager
def database():
    """One dict-row connection per request path; failures surface as SERVICE_UNAVAILABLE."""
    try:
        with connect_db() as connection:
            connection.row_factory = dict_row
            yield connection
    except DatabaseError:
        raise AuthError(503, 'SERVICE_UNAVAILABLE', '인증 서버에 연결할 수 없어요.') from None
