"""Integration check in a unique temporary schema; requires local PostgreSQL."""
import sys
import unittest
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, pool, text

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from app.database import connect_db


class MigrationTest(unittest.TestCase):
    def test_baseline_roundtrip(self):
        schema = "migration_test_" + uuid4().hex
        engine = create_engine("postgresql+psycopg://", creator=connect_db,
                               poolclass=pool.NullPool, hide_parameters=True)
        created = False
        try:
            with engine.connect() as connection:
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
                connection.commit()
                created = True
                connection.execute(text(f'SET search_path TO "{schema}"'))
                connection.commit()
                config = Config(str(BACKEND.parent / "alembic.ini"))
                config.attributes["connection"] = connection
                for attempt in range(2):
                    command.upgrade(config, "head")
                    command.upgrade(config, "head")
                    self.assertEqual(connection.execute(text(
                        "SELECT version_num FROM alembic_version")).scalars().all(),
                        ["0002_member_auth"])
                    self.assertEqual(sorted(inspect(connection).get_table_names(schema=schema)),
                                     ['alembic_version', 'auth_credentials', 'auth_rate_limit_buckets',
                                      'auth_sessions', 'user_profiles', 'users'])
                    connection.commit()
                    command.downgrade(config, "base")
                    self.assertEqual(connection.execute(text(
                        "SELECT count(*) FROM alembic_version")).scalar_one(), 0)
                    connection.commit()
        finally:
            if created:
                with engine.begin() as cleanup:
                    # Only the randomly generated schema owned by this test is removed.
                    cleanup.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
