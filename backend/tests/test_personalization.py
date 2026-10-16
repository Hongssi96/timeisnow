"""Real owned PostgreSQL/ASGI; synthetic time-separated manual events and map/AI."""
import asyncio,copy,json,unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from uuid import uuid4
from psycopg.types.json import Jsonb
from test_personal_walk import PersonalWalkTests as Base,output
from test_api_contract import request
from app.ai import provider as ai_provider
from app.guidance import walk_provider
from app.common.database import database
from app.trips import repository as trips

class PersonalizationTests(unittest.IsolatedAsyncioTestCase):
    setUp=Base.setUp;tearDown=Base.tearDown;call=Base.call
    prepare=Base.prepare;credentials=Base.credentials;signup_login=Base.signup_login
    saved=Base.saved;create=Base.create;search=Base.search;completed=Base.completed
    saved_search=Base.saved_search;routine_body=Base.routine_body;save=Base.save
    ready=Base.ready;refresh=Base.refresh;path=Base.path
    mapped=Base.mapped;estimate=Base.estimate;details=Base.details

    async def fixture(self):
        await self.mapped()
        with patch.object(walk_provider,'fetch',return_value=self.details()),patch.object(ai_provider,'fetch_estimate',side_effect=output):
            response=await self.estimate()
        self.assertEqual(response[0],200,response[2])
        departure=(await self.call(self.path(self.accepted)))[2]['data']['departure']
        response=await self.call('/trips',{'guidance_id':departure['guidance_id'],'measurement_mode':'assisted'})
        self.assertEqual(response[0],201,response[2]);self.tid=response[2]['data']['trip_id']
        with database() as c:
            row=c.execute('SELECT t.user_id,g.snapshot FROM manual_trips t JOIN guidance_snapshots g ON g.id=t.guidance_id WHERE t.id=%s',(self.tid,)).fetchone()
            self.owner=row['user_id'];self.snapshot=row['snapshot']
            trips.cancel(c,self.tid)

    def observation(self,seconds=523.2,*,delayed=False,missing=False,before_reset=False,unverified=False):
        tid=uuid4();snapshot=copy.deepcopy(self.snapshot)
        if unverified:snapshot['departure']['personal_walk']=None
        end=datetime.now(timezone.utc)-timedelta(seconds=1)
        start=end-timedelta(seconds=seconds)
        snapshot['departure']['calculated_at']=(start-timedelta(seconds=1)).isoformat()
        if not before_reset:
            # Fixture clock simulates recording AFTER reset without wall-clock waiting.
            with database() as c:c.execute("UPDATE walking_learning_state SET started_at='epoch'")
        with database() as c:
            trips.insert(c,self.owner,uuid4(),tid,self.rid,snapshot,'assisted')
            trips.cancel(c,tid)
            legs=snapshot['candidate']['ordered_legs'];first=next(i for i,l in enumerate(legs) if l['type']=='BUS')
            kinds=[('departed',legs[0]['leg_id'],start),('boarded' if missing else 'approach_arrived',legs[max(0,first-1)]['leg_id'],end)]
            for kind,lid,at in kinds:
                c.execute('INSERT INTO manual_trip_events(id,trip_id,client_event_id,body_hash,type,leg_id,source,occurred_at,received_at) VALUES(%s,%s,%s,%s,%s,%s,\'manual\',%s,%s)',
                  (uuid4(),tid,uuid4(),'a'*64,kind,lid,at,at+timedelta(seconds=61 if delayed else 1)))
        return str(tid)

    async def learn(self,tid,**changes):
        return await self.call('/trips/'+tid+'/walking-observation',{'same_scope':True,'condition':'normal',**changes})

    async def test_five_samples_once_median_before_update_error_and_recalculation(self):
        await self.fixture()
        tids=[self.observation(n) for n in (436,523.2,523.2,523.2,654)]
        with patch.object(ai_provider,'fetch_estimate') as model,patch.object(walk_provider,'fetch') as walk:
            responses=[await self.learn(t) for t in tids]
            self.assertEqual([r[0] for r in responses],[201]*5)
            self.assertEqual([r[2]['data']['updated'] for r in responses],[False]*4+[True])
            replay=await self.learn(tids[-1]);self.assertEqual(replay[0],200);self.assertEqual(replay[2],responses[-1][2] | {'meta':replay[2]['meta']})
            value=(await self.call('/me/personalization'))[2]['data']
            self.assertEqual(value['sample_counts']['valid'],5);self.assertAlmostEqual(value['factors'][0]['value'],1.04)
            self.assertEqual(value['quality']['baseline_mae_seconds'],value['quality']['personalized_mae_seconds'])
            self.assertEqual(value['quality']['baseline_underprediction_rate'],.8)
            self.assertEqual((await self.learn(tids[-1],same_scope=False))[0],409)
            # Existing F05 recalculation reuses the immutable base with the learned profile.
            new=await self.estimate();self.assertEqual(new[0],200,new[2]);self.assertEqual(new[2]['data']['estimate']['source'],'profile_recalculation')
            self.assertEqual(new[2]['data']['estimate']['estimated_seconds'],454)
            model.assert_not_called();walk.assert_not_called()
        with database() as c:
            self.assertEqual(c.execute('SELECT count(*) AS n FROM walking_learning_updates').fetchone()['n'],1)
            self.assertEqual(c.execute('SELECT first_boarding_buffer_seconds FROM user_profiles').fetchone()['first_boarding_buffer_seconds'],300)

    async def test_exclusions_no_boarding_inference_or_wait_learning(self):
        await self.fixture()
        cases=[(self.observation(missing=True),{},'MISSING_WALK_EVENTS'),(self.observation(delayed=True),{},'INPUT_DELAY'),
          (self.observation(unverified=True),{},'UNVERIFIED_BASE'),(self.observation(),{'same_scope':False},'SCOPE_MISMATCH'),
          (self.observation(),{'condition':'running'},'RUNNING'),(self.observation(1308),{},'RATIO_REVIEW_REQUIRED')]
        for tid,body,reason in cases:
            response=await self.learn(tid,**body);self.assertEqual(response[0],201,response[2])
            self.assertIn(reason,response[2]['data']['exclusion_reasons']);self.assertFalse(response[2]['data']['updated'])
        value=(await self.call('/me/personalization'))[2]['data']
        self.assertEqual(value['sample_counts'],{'valid':0,'excluded':6});self.assertIsNone(value['quality']['baseline_mae_seconds'])

    async def test_reset_version_replay_generation_and_restore(self):
        await self.fixture()
        for _ in range(5):self.assertEqual((await self.learn(self.observation()))[0],201)
        body={'expected_version':2,'client_request_id':str(uuid4())}
        reset=await self.call('/me/personalization/reset',body);self.assertEqual(reset[0],200,reset[2])
        self.assertEqual(reset[2]['data']['factors'][0]['value'],1);self.assertEqual(reset[2]['data']['sample_counts']['valid'],0)
        self.assertEqual((await self.call('/me/personalization/reset',body))[2]['data'],reset[2]['data'])
        stale=await self.call('/me/personalization/reset',{**body,'client_request_id':str(uuid4())});self.assertEqual(stale[0],409)
        rejected=await self.learn(self.observation(before_reset=True));self.assertIn('BEFORE_RESET',rejected[2]['data']['exclusion_reasons'])
        restored=await self.call('/me/personalization/restore',{'expected_version':3,'client_request_id':str(uuid4())})
        self.assertEqual(restored[0],200);self.assertAlmostEqual(restored[2]['data']['factors'][0]['value'],1.04)
        self.assertEqual(restored[2]['data']['sample_counts']['valid'],0)

    async def test_concurrent_replay_auth_ownership_csrf_and_private_response(self):
        await self.fixture();tid=self.observation()
        responses=await asyncio.gather(self.learn(tid),self.learn(tid));self.assertEqual(sorted(r[0] for r in responses),[200,201])
        self.assertEqual((await self.call('/trips/'+tid+'/walking-observation',{'same_scope':True,'condition':'normal'},csrf=False))[0],403)
        self.assertEqual((await self.learn(str(uuid4())))[0],404)
        self.assertEqual((await self.learn(tid,base_seconds=1))[0],422)
        self.assertEqual((await request('/api/v1/me/personalization'))[0],401)
        response=await self.call('/me/personalization');self.assertEqual(response[1][b'cache-control'],b'no-store')
        for key in ('latitude','longitude','place_id','path_key'):self.assertNotIn(key,json.dumps(response[2]))
        await self.prepare();creds=self.credentials('other@example.invalid');await self.call('/auth/register',creds)
        login=await self.call('/auth/login',{'email':creds['email'],'password':creds['password']});self.cookie=login[1][b'set-cookie'].decode().split(';')[0];self.csrf=login[2]['data']['csrf_token']
        self.assertEqual((await self.learn(tid))[0],404)

    async def test_changed_place_not_learned_and_cascade_preserves_factor_history(self):
        await self.fixture();tid=self.observation()
        with database() as c:c.execute('UPDATE saved_places SET location_version=location_version+1')
        response=await self.learn(tid);self.assertIn('PLACE_CHANGED',response[2]['data']['exclusion_reasons'])
        with database() as c:
            c.execute('DELETE FROM guidance_snapshots WHERE id=(SELECT guidance_id FROM manual_trips WHERE id=%s)',(tid,))
            self.assertEqual(c.execute('SELECT count(*) AS n FROM walking_learning_observations').fetchone()['n'],0)

    def seed_valid(self,ratios,other_path=False):
        """Seed accepted historical fixtures to test bounded pool selection independently."""
        from app.personalization import repository as learning
        other_key='f'*64
        if other_path:
            # Accepted samples need a retained base for their distinct synthetic segment.
            with database() as c:
                c.execute('''INSERT INTO walking_paths(id,user_id,path_key,candidate_id,origin_ref,destination_ref,direction,scope,
                  place_refs,evidence,verified_at,calculated_at,expires_at,retained_until,cache_key,cache_identity)
                  SELECT %s,user_id,%s,candidate_id,origin_ref,destination_ref,direction,scope,
                    place_refs,evidence,verified_at,calculated_at,expires_at,retained_until,%s,cache_identity
                  FROM walking_paths WHERE user_id=%s AND cache_key IS NOT NULL AND cache_key<>%s
                    AND NOT EXISTS(SELECT 1 FROM walking_paths WHERE user_id=%s AND cache_key=%s) LIMIT 1''',
                  (uuid4(),other_key,other_key,self.owner,other_key,self.owner,other_key))
        for ratio in ratios:
            tid=self.observation()
            with database() as c:
                p=learning.locked(c,self.owner)
                e=learning.evidence(c,self.owner,self.snapshot['departure']['personal_walk']['revision_id'])
                learning.save_observation(c,(uuid4(),self.owner,tid,'b'*64,p['generation'],other_key if other_path else e['cache_key'],
                  Jsonb(e['place_refs']),436,436*ratio,436,ratio,'valid',Jsonb([]),Jsonb({}),datetime.now(timezone.utc)+timedelta(days=1)))

    async def test_same_segment_pool_wins_without_concatenating_other_type_samples(self):
        await self.fixture();self.seed_valid([1.2]*4);self.seed_valid([2]*16,other_path=True)
        response=await self.learn(self.observation());self.assertTrue(response[2]['data']['updated'])
        value=(await self.call('/me/personalization'))[2]['data'];self.assertAlmostEqual(value['factors'][0]['value'],1.04)
        self.assertEqual(value['sample_counts']['valid'],21)
        with database() as c:
            row=c.execute('SELECT sample_ids,pool_scope FROM walking_learning_updates').fetchone()
            self.assertEqual(len(row['sample_ids']),5);self.assertEqual(row['pool_scope'],'same_segment')

    async def test_same_type_fallback_and_recent_twenty_only(self):
        await self.fixture();self.seed_valid([.5]*5,other_path=True);self.seed_valid([1.5]*20,other_path=True)
        response=await self.learn(self.observation());self.assertTrue(response[2]['data']['updated'])
        value=(await self.call('/me/personalization'))[2]['data'];self.assertAlmostEqual(value['factors'][0]['value'],1.1)
        self.assertEqual(value['sample_counts']['valid'],26)
        with database() as c:
            row=c.execute('SELECT sample_ids,pool_scope FROM walking_learning_updates').fetchone()
            self.assertEqual(len(row['sample_ids']),20);self.assertEqual(row['pool_scope'],'same_type')

    async def test_migration_downgrade_retains_existing_user_trip_events_and_factor(self):
        from alembic import command
        from alembic.config import Config
        from sqlalchemy import create_engine,pool
        from app.common import database as common
        from pathlib import Path
        await self.fixture();tid=self.observation();await self.learn(tid)
        with database() as c:before=c.execute('SELECT count(*) AS n FROM manual_trip_events').fetchone()['n']
        engine=create_engine('postgresql+psycopg://',creator=common.connect_db,poolclass=pool.NullPool)
        try:
            with engine.connect() as c:
                config=Config(str(Path(__file__).resolve().parents[2]/'alembic.ini'));config.attributes['connection']=c
                command.downgrade(config,'0017_trip_outcomes');command.upgrade(config,'head')
        finally:engine.dispose()
        with database() as c:
            self.assertEqual(c.execute('SELECT count(*) AS n FROM manual_trip_events').fetchone()['n'],before)
            self.assertEqual(c.execute('SELECT walking_duration_factor FROM user_profiles').fetchone()['walking_duration_factor'],1)

del Base
