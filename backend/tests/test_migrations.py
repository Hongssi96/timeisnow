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
    def test_upgrade_from_either_published_parent_preserves_domain_data(self):
        engine = create_engine("postgresql+psycopg://", creator=connect_db,
                               poolclass=pool.NullPool, hide_parameters=True)
        try:
            for parent in ('0013_manual_trips', '0013_meeting_core'):
                schema = 'migration_parent_' + uuid4().hex
                with engine.connect() as connection:
                    connection.execute(text(f'CREATE SCHEMA "{schema}"'))
                    connection.commit()
                    try:
                        connection.execute(text(f'SET search_path TO "{schema}"'))
                        connection.commit()
                        config = Config(str(BACKEND.parent / "alembic.ini"))
                        config.attributes["connection"] = connection
                        command.upgrade(config, parent)
                        uid, item = str(uuid4()), str(uuid4())
                        connection.execute(text("INSERT INTO users(id,display_name) VALUES(:id,'parent fixture')"), {'id':uid})
                        if parent == '0013_manual_trips':
                            connection.execute(text("""INSERT INTO guidance_snapshots(id,user_id,snapshot,expires_at)
                                VALUES(:id,:uid,'{}',now()+interval '90 days')"""), {'id':item,'uid':uid})
                            table = 'guidance_snapshots'
                            trip_id, event_id = str(uuid4()), str(uuid4())
                            connection.execute(text("""INSERT INTO manual_trips(id,user_id,guidance_id,measurement_mode,expires_at)
                                VALUES(:id,:uid,:gid,'assisted',now()+interval '90 days')"""), {'id':trip_id,'uid':uid,'gid':item})
                            connection.execute(text("""INSERT INTO manual_trip_events(id,trip_id,client_event_id,body_hash,type,leg_id,source,occurred_at)
                                VALUES(:id,:tid,:id,:hash,'departed',:id,'manual',now())"""), {'id':event_id,'tid':trip_id,'hash':'0'*64})
                        else:
                            connection.execute(text("INSERT INTO meetings(id,user_id,title) VALUES(:id,:uid,'parent fixture')"),
                                               {'id':item,'uid':uid})
                            table = 'meetings'
                        connection.commit()
                        command.upgrade(config, 'head')
                        self.assertEqual(connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one(),
                                         '0021_meeting_flow_merge')
                        self.assertEqual(str(connection.execute(text(f'SELECT id FROM {table}')).scalar_one()), item)
                        if parent == '0013_manual_trips':
                            self.assertEqual(str(connection.execute(text('SELECT id FROM manual_trip_events')).scalar_one()),event_id)
                            for kind in ('approach_arrived','boarded'):
                                eid=str(uuid4())
                                connection.execute(text("""INSERT INTO manual_trip_events(id,trip_id,client_event_id,body_hash,type,leg_id,source,occurred_at)
                                    VALUES(:id,:tid,:id,:hash,:kind,:id,'manual',now())"""), {'id':eid,'tid':trip_id,'hash':'0'*64,'kind':kind})
                            connection.commit()
                            from sqlalchemy.exc import IntegrityError
                            connection.execute(text("UPDATE manual_trips SET status='completed',version=2 WHERE id=:id"),{'id':trip_id})
                            connection.commit()
                            with self.assertRaises(IntegrityError):command.downgrade(config,'0016_transfer_events')
                            connection.rollback()
                            self.assertEqual(connection.execute(text('SELECT status FROM manual_trips')).scalar_one(),'completed')
                            connection.execute(text("UPDATE manual_trips SET status='active',version=1 WHERE id=:id"),{'id':trip_id})
                            terminal_id=str(uuid4())
                            connection.execute(text("""INSERT INTO manual_trip_events(id,trip_id,client_event_id,body_hash,type,leg_id,source,occurred_at)
                                VALUES(:id,:tid,:id,:hash,'arrived',:id,'manual',now())"""), {'id':terminal_id,'tid':trip_id,'hash':'0'*64})
                            connection.commit()
                            with self.assertRaises(IntegrityError):command.downgrade(config,'0016_transfer_events')
                            connection.rollback()
                            self.assertEqual(connection.execute(text('SELECT count(*) FROM manual_trip_events')).scalar_one(),4)
                            connection.execute(text('DELETE FROM manual_trip_events WHERE id=:id'),{'id':terminal_id})
                            connection.commit()
                            extras=[]
                            for kind in ('boarded','alighted'):
                                eid=str(uuid4());extras.append(eid)
                                connection.execute(text("""INSERT INTO manual_trip_events(id,trip_id,client_event_id,body_hash,type,leg_id,source,occurred_at)
                                    VALUES(:id,:tid,:id,:hash,:kind,:id,'manual',now())"""), {'id':eid,'tid':trip_id,'hash':'0'*64,'kind':kind})
                            connection.commit()
                            with self.assertRaises(IntegrityError):command.downgrade(config,'0015_first_boarding_events')
                            connection.rollback()
                            self.assertEqual(connection.execute(text('SELECT count(*) FROM manual_trip_events')).scalar_one(),5)
                            connection.execute(text('DELETE FROM manual_trip_events WHERE id=:id'),{'id':extras[1]})
                            connection.commit()
                            with self.assertRaises(IntegrityError):command.downgrade(config,'0015_first_boarding_events')
                            connection.rollback()
                            connection.execute(text('DELETE FROM manual_trip_events WHERE id=:id'),{'id':extras[0]})
                            connection.commit()
                            with self.assertRaises(IntegrityError):command.downgrade(config,'0014_integrated_features')
                            connection.rollback()
                            self.assertEqual(connection.execute(text('SELECT count(*) FROM manual_trip_events')).scalar_one(),3)
                            connection.execute(text("DELETE FROM manual_trip_events WHERE type<>'departed'"))
                            connection.commit()
                            command.downgrade(config,'0014_integrated_features')
                            command.upgrade(config,'head')
                            self.assertEqual(str(connection.execute(text('SELECT id FROM manual_trip_events')).scalar_one()),event_id)
                        self.assertTrue({'meetings','manual_trips','guidance_snapshots'} <=
                                        set(inspect(connection).get_table_names(schema=schema)))
                        connection.commit()
                    finally:
                        connection.rollback()
                        connection.execute(text('SET search_path TO public'))
                        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
                        connection.commit()
        finally:
            engine.dispose()

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
                        ["0021_meeting_flow_merge"])
                    self.assertEqual(sorted(inspect(connection).get_table_names(schema=schema)),
                                     ['ai_executions', 'alembic_version', 'auth_credentials', 'auth_rate_limit_buckets',
                                      'auth_sessions', 'guidance_snapshots', 'jobs', 'journey_plans', 'journey_search_keys', 'journey_searches',
                                      'manual_trip_creation_keys', 'manual_trip_events', 'manual_trips',
                                      'meeting_idempotency_keys', 'meeting_invite_replays', 'meeting_invites',
                                      'meeting_journeys', 'meeting_members', 'meeting_revisions',
                                      'meeting_share_events', 'meetings',
                                      'place_creation_keys', 'place_location_confirmations', 'place_searches',
                                      'routine_creation_keys', 'routines', 'saved_places', 'trip_event_corrections', 'trip_exports', 'trip_record_mutations', 'user_profiles', 'users',
                                      'walking_estimate_revisions', 'walking_estimates', 'walking_learning_observations', 'walking_learning_state', 'walking_learning_updates', 'walking_paths'])
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
