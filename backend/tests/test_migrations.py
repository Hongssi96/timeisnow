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
                    command.upgrade(config, '0003_saved_places')
                    user_id, place_id = str(uuid4()), str(uuid4())
                    connection.execute(text("INSERT INTO users(id,display_name) VALUES(:id,'migration fixture')"), {'id':user_id})
                    connection.execute(text('''INSERT INTO saved_places(id,user_id,label,name,address,latitude,longitude)
                        VALUES(:id,:user_id,'home','synthetic','synthetic address',37.5,127)'''), {'id':place_id,'user_id':user_id})
                    connection.commit()
                    command.upgrade(config, "head")
                    command.upgrade(config, "head")
                    self.assertEqual(connection.execute(text('SELECT location_source,entrance_note,location_address,version FROM saved_places')).one(),
                                     ('search',None,None,1))
                    connection.commit()
                    command.downgrade(config, '0003_saved_places')
                    self.assertEqual(connection.execute(text('SELECT latitude,longitude,version FROM saved_places')).one(), (37.5,127.0,1))
                    connection.commit()
                    command.upgrade(config, 'head')
                    self.assertEqual(connection.execute(text(
                        "SELECT version_num FROM alembic_version")).scalars().all(),
                        ["0004_place_map_pin"])
                    self.assertEqual(sorted(inspect(connection).get_table_names(schema=schema)),
                                     ['alembic_version', 'auth_credentials', 'auth_rate_limit_buckets',
                                      'auth_sessions', 'place_creation_keys', 'place_location_confirmations', 'place_searches', 'saved_places', 'user_profiles', 'users'])
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
