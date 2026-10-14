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
from app.common.database import connect_db


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
                    connection.execute(text('INSERT INTO user_profiles(user_id) VALUES(:id)'), {'id':user_id})
                    connection.execute(text('''INSERT INTO saved_places(id,user_id,label,name,address,latitude,longitude,version)
                        VALUES(:id,:user_id,'home','synthetic','synthetic address',37.5,127,4)'''), {'id':place_id,'user_id':user_id})
                    connection.commit()
                    command.upgrade(config, '0009_walking_history')
                    path_id=str(uuid4())
                    connection.execute(text("""INSERT INTO walking_paths(id,user_id,path_key,candidate_id,origin_ref,destination_ref,direction,scope,
                        place_refs,evidence,verified_at,calculated_at,expires_at,retained_until)
                        VALUES(:id,:user_id,repeat('a',64),'legacy','origin','destination','outbound','synthetic','[]',jsonb_build_object('legacy',true),
                        clock_timestamp(),clock_timestamp(),clock_timestamp()+interval '30 days',clock_timestamp()+interval '90 days')"""),{'id':path_id,'user_id':user_id})
                    connection.commit()
                    command.upgrade(config, "head")
                    self.assertEqual(connection.execute(text('SELECT walking_duration_factor FROM user_profiles WHERE user_id=:id'),{'id':user_id}).scalar_one(),1.0)
                    self.assertEqual(connection.execute(text('SELECT cache_key,cache_identity,evidence FROM walking_paths WHERE id=:id'),{'id':path_id}).one(),(None,None,{'legacy':True}))
                    connection.commit()
                    command.downgrade(config, '0009_walking_history')
                    self.assertEqual(connection.execute(text('SELECT evidence FROM walking_paths WHERE id=:id'),{'id':path_id}).scalar_one(),{'legacy':True})
                    connection.commit()
                    command.upgrade(config, "head")
                    self.assertEqual(connection.execute(text('SELECT walking_duration_factor FROM user_profiles WHERE user_id=:id'),{'id':user_id}).scalar_one(),1.0)
                    self.assertEqual(connection.execute(text('SELECT location_source,entrance_note,location_address,version FROM saved_places')).one(),
                                     ('search',None,None,4))
                    self.assertEqual(connection.execute(text('SELECT location_version FROM saved_places')).scalar_one(),4)
                    connection.commit()
                    command.downgrade(config, '0003_saved_places')
                    self.assertEqual(connection.execute(text('SELECT latitude,longitude,version FROM saved_places')).one(), (37.5,127.0,4))
                    connection.commit()
                    command.upgrade(config, 'head')
                    self.assertEqual(connection.execute(text(
                        "SELECT version_num FROM alembic_version")).scalars().all(),
                        ["0013_meeting_core"])
                    self.assertEqual(sorted(inspect(connection).get_table_names(schema=schema)),
                                     ['ai_executions', 'alembic_version', 'auth_credentials', 'auth_rate_limit_buckets',
                                      'auth_sessions', 'jobs', 'journey_plans', 'journey_search_keys', 'journey_searches',
                                      'meeting_idempotency_keys', 'meeting_invites', 'meeting_members', 'meeting_revisions',
                                      'meetings', 'place_creation_keys', 'place_location_confirmations', 'place_searches',
                                      'routine_creation_keys', 'routines', 'saved_places', 'user_profiles', 'users',
                                      'walking_estimate_revisions', 'walking_estimates', 'walking_paths'])
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
