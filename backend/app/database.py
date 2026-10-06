"""Local PostgreSQL connection; never log connection settings or passwords."""
import os
from pathlib import Path

import psycopg
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]


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
