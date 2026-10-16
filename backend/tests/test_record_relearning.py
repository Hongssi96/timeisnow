"""Atomic correction/deletion against actual isolated PostgreSQL and ASGI."""
import asyncio,json,unittest
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4
from test_personalization import PersonalizationTests as Base
from test_api_contract import request
from app.common.database import database
from app.ai import provider as ai_provider
from app.guidance import walk_provider

class RecordRelearningTests(unittest.IsolatedAsyncioTestCase):
    setUp=Base.setUp;tearDown=Base.tearDown;call=Base.call
    prepare=Base.prepare;credentials=Base.credentials;signup_login=Base.signup_login
    saved=Base.saved;create=Base.create;search=Base.search;completed=Base.completed
    saved_search=Base.saved_search;routine_body=Base.routine_body;save=Base.save
    ready=Base.ready;refresh=Base.refresh;path=Base.path;mapped=Base.mapped;estimate=Base.estimate;details=Base.details
    fixture=Base.fixture;observation=Base.observation;learn=Base.learn

    async def learned(self,n=5):
        await self.fixture();self.ids=[]
        for _ in range(n):
            tid=self.observation();self.ids.append(tid);r=await self.learn(tid);self.assertEqual(r[0],201,r[2])
        self.tid=self.ids[-1]
        self.detail=(await self.call('/trips/'+self.tid))[2]['data']
        self.event=self.detail['events'][-1]

    async def mutation(self,path,body,method='PATCH',csrf=True):
        headers=[(b'origin',b'http://127.0.0.1:5173'),(b'content-type',b'application/json')]
        if self.cookie:headers.append((b'cookie',self.cookie.encode()))
        if csrf:headers.append((b'x-csrf-token',self.csrf.encode()))
        return await request('/api/v1'+path,method,headers=headers,body=json.dumps(body).encode())

    def edit_body(self,**values):
        return {'expected_version':self.event['version'],'client_request_id':str(uuid4()),'excluded':True,'correction_reason':'learning_exclusion',**values}

    def event_path(self):return '/trips/'+self.tid+'/events/'+self.event['event_id']

    async def test_exclude_rebuilds_to_default_recalculates_without_model_and_restores_safely(self):
        await self.learned()
        with patch.object(ai_provider,'fetch_estimate') as ai,patch.object(walk_provider,'fetch') as walk:
            response=await self.mutation(self.event_path(),self.edit_body())
            self.assertEqual(response[0],200,response[2]);value=response[2]['data']
            self.assertEqual(value['personalization']['sample_counts']['valid'],4)
            self.assertEqual(value['personalization']['factors'][0]['value'],1)
            self.assertFalse(value['personalization']['can_restore'])
            denied=await self.call('/me/personalization/restore',{'expected_version':value['personalization']['profile_version'],'client_request_id':str(uuid4())})
            self.assertEqual(denied[2]['error']['code'],'RESTORE_UNAVAILABLE')
            # Latest current revision is attached without making another explicit AI request.
            fresh=(await self.call(self.path(self.accepted)))[2]['data']['departure']
            self.assertIsNotNone(fresh['personal_walk']);self.assertEqual(fresh['personal_walk']['source'],'profile_recalculation')
            self.assertEqual(fresh['approach_seconds'],436)
            ai.assert_not_called();walk.assert_not_called()
        saved=(await self.call('/trips/'+self.tid))[2]['data'];self.assertEqual(saved['guidance'],self.detail['guidance'])
        self.assertEqual(saved['events'][-1]['version'],2);self.assertEqual(len(saved['corrections']),1)
        restored=await self.mutation(self.event_path(),self.edit_body(expected_version=2,excluded=False,correction_reason='learning_restore'))
        self.assertEqual(restored[0],200,restored[2]);self.assertAlmostEqual(restored[2]['data']['personalization']['factors'][0]['value'],1.04)
        with database() as c:self.assertEqual(c.execute('SELECT first_boarding_buffer_seconds FROM user_profiles').fetchone()['first_boarding_buffer_seconds'],300)

    async def test_delete_five_to_four_cascades_and_replay_never_relearns(self):
        await self.learned();body={'expected_version':self.detail['trip']['version'],'client_request_id':str(uuid4())}
        with patch.object(ai_provider,'fetch_estimate') as ai,patch.object(walk_provider,'fetch') as walk:
            one=await self.mutation('/trips/'+self.tid,body,'DELETE');two=await self.mutation('/trips/'+self.tid,body,'DELETE')
            self.assertEqual((one[0],two[0]),(200,200));self.assertEqual(one[2]['data'],two[2]['data'])
            self.assertEqual(one[2]['data']['personalization']['factors'][0]['value'],1)
            ai.assert_not_called();walk.assert_not_called()
        self.assertEqual((await self.call('/trips/'+self.tid))[0],404)
        self.assertEqual((await self.mutation('/trips/'+self.tid,{**body,'expected_version':3},'DELETE'))[0],409)
        with database() as c:
            self.assertEqual(c.execute('SELECT count(*) AS n FROM manual_trip_events WHERE trip_id=%s',(self.tid,)).fetchone()['n'],0)
            self.assertEqual(c.execute('SELECT count(*) AS n FROM walking_learning_observations WHERE trip_id=%s',(self.tid,)).fetchone()['n'],0)
            self.assertEqual(c.execute("SELECT count(*) AS n FROM walking_learning_updates WHERE restorable=true").fetchone()['n'],0)

    async def test_six_to_five_replays_from_base_instead_of_multiplying_old_factor(self):
        await self.learned(6)
        self.assertAlmostEqual((await self.call('/me/personalization'))[2]['data']['factors'][0]['value'],1.072)
        response=await self.mutation('/trips/'+self.tid,{'expected_version':2,'client_request_id':str(uuid4())},'DELETE')
        self.assertEqual(response[0],200,response[2]);self.assertAlmostEqual(response[2]['data']['personalization']['factors'][0]['value'],1.04)

    async def test_conditions_reclassification_and_original_prediction_stay_immutable(self):
        await self.learned();url='/trips/'+self.tid+'/walking-observation'
        before=(await self.call(url))[2]['data'];self.assertEqual(before['confirmation'],{'same_scope':True,'condition':'normal'})
        body={'same_scope':True,'condition':'running','expected_version':1,'client_request_id':str(uuid4())}
        response=await self.mutation(url,body);self.assertEqual(response[0],200,response[2]);self.assertEqual(response[2]['data']['personalization']['sample_counts']['valid'],4)
        self.assertEqual((await self.mutation(url,body))[2]['data'],response[2]['data'])
        restored=await self.mutation(url,{**body,'condition':'normal','expected_version':2,'client_request_id':str(uuid4())})
        self.assertEqual(restored[0],200);self.assertEqual(restored[2]['data']['personalization']['sample_counts']['valid'],5)
        with database() as c:self.assertEqual(float(c.execute('SELECT predicted_seconds FROM walking_learning_observations WHERE trip_id=%s',(self.tid,)).fetchone()['predicted_seconds']),436)

    async def test_time_constraints_version_and_audit_and_normalized_retry(self):
        await self.learned();body=self.edit_body(excluded=False,correction_reason='timestamp_error')
        from datetime import datetime,timezone
        body['occurred_at']=(datetime.fromisoformat(self.event['occurred_at'])-timedelta(seconds=.5)).isoformat()
        one=await self.mutation(self.event_path(),body);self.assertEqual(one[0],200,one[2])
        # Equivalent timezone text must identify the same correction request.
        body['occurred_at']=datetime.fromisoformat(body['occurred_at']).astimezone(timezone(timedelta(hours=9))).isoformat()
        two=await self.mutation(self.event_path(),body);self.assertEqual(two[0],200,two[2])
        bad=await self.mutation(self.event_path(),self.edit_body(expected_version=2,occurred_at='2000-01-01T00:00:00Z'))
        self.assertEqual(bad[0],422)
        self.assertEqual((await self.mutation(self.event_path(),self.edit_body()))[0],409)
        for change in ({'occurred_at':None},{'occurred_at':1},{'excluded':None},{'base_seconds':1}):
            self.assertEqual((await self.mutation(self.event_path(),self.edit_body(**change)))[0],422)

    async def test_concurrent_edits_delete_race_and_transaction_rollback(self):
        await self.learned();body=self.edit_body()
        responses=await asyncio.gather(self.mutation(self.event_path(),body),self.mutation(self.event_path(),body))
        self.assertEqual([r[0] for r in responses],[200,200])
        with database() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM trip_event_corrections').fetchone()['n'],1)
        from app.personalization import derived
        with patch.object(derived,'recalculate',side_effect=RuntimeError('synthetic failure')):
            failed=await self.mutation(self.event_path(),self.edit_body(expected_version=2,excluded=False))
        self.assertEqual(failed[0],500)
        saved=(await self.call('/trips/'+self.tid))[2]['data'];self.assertEqual(saved['events'][-1]['version'],2)
        self.assertEqual(len(saved['corrections']),1)

    async def test_auth_csrf_owner_active_and_reset_generation(self):
        await self.learned()
        self.assertEqual((await self.mutation(self.event_path(),self.edit_body(),csrf=False))[0],403)
        with database() as c:c.execute("UPDATE manual_trips SET status='active' WHERE id=%s",(self.tid,))
        self.assertEqual((await self.mutation(self.event_path(),self.edit_body()))[2]['error']['code'],'ACTIVE_TRIP_EDIT_FORBIDDEN')
        with database() as c:c.execute("UPDATE manual_trips SET status='cancelled' WHERE id=%s",(self.tid,))
        reset=await self.call('/me/personalization/reset',{'expected_version':2,'client_request_id':str(uuid4())});self.assertEqual(reset[0],200)
        restore=await self.call('/me/personalization/restore',{'expected_version':3,'client_request_id':str(uuid4())});self.assertEqual(restore[0],200)
        self.assertAlmostEqual(restore[2]['data']['factors'][0]['value'],1.04)
        response=await self.mutation(self.event_path(),self.edit_body(excluded=False));self.assertEqual(response[0],200,response[2])
        self.assertEqual(response[2]['data']['personalization']['sample_counts']['valid'],0)
        self.assertEqual(response[2]['data']['personalization']['factors'][0]['value'],1)
        await self.prepare();creds=self.credentials('stranger@example.invalid');await self.call('/auth/register',creds)
        logged=await self.call('/auth/login',{'email':creds['email'],'password':creds['password']});self.cookie=logged[1][b'set-cookie'].decode().split(';')[0];self.csrf=logged[2]['data']['csrf_token']
        self.assertEqual((await self.mutation(self.event_path(),self.edit_body()))[0],404)
        self.assertEqual((await self.mutation('/trips/'+self.tid,{'expected_version':3,'client_request_id':str(uuid4())},'DELETE'))[0],404)

    async def test_delete_removes_audit_retry_payloads_and_dangling_sample_ids(self):
        from psycopg.types.json import Jsonb
        await self.learned();body=self.edit_body();edited=await self.mutation(self.event_path(),body);self.assertEqual(edited[0],200)
        obs=(await self.call('/trips/'+self.tid+'/walking-observation'))[2]['data']['observation_id']
        result=await self.mutation('/trips/'+self.tid,{'expected_version':3,'client_request_id':str(uuid4())},'DELETE');self.assertEqual(result[0],200,result[2])
        self.assertEqual((await self.mutation(self.event_path(),body))[0],404)
        with database() as c:
            self.assertEqual(c.execute('SELECT count(*) AS n FROM trip_event_corrections').fetchone()['n'],0)
            self.assertEqual(c.execute("SELECT count(*) AS n FROM trip_record_mutations WHERE kind!='delete'").fetchone()['n'],0)
            self.assertEqual(c.execute('SELECT count(*) AS n FROM walking_learning_updates WHERE sample_ids @> %s',(Jsonb([obs]),)).fetchone()['n'],0)

    async def test_expired_or_changed_place_base_not_recalculated(self):
        await self.learned()
        with database() as c:
            c.execute("UPDATE walking_paths SET expires_at=clock_timestamp()-interval '1 second'")
        response=await self.mutation(self.event_path(),self.edit_body());self.assertEqual(response[0],200)
        with database() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM walking_estimate_revisions').fetchone()['n'],1)

    async def test_legacy_missing_conditions_require_confirmation_and_audit_blocks_downgrade(self):
        await self.learned()
        with database() as c:c.execute("UPDATE walking_learning_observations SET confirmation=NULL WHERE trip_id=%s",(self.tid,))
        response=await self.mutation(self.event_path(),self.edit_body(excluded=False));self.assertEqual(response[0],200)
        obs=(await self.call('/trips/'+self.tid+'/walking-observation'))[2]['data'];self.assertIn('CONFIRMATION_REQUIRED',obs['exclusion_reasons'])
        fixed=await self.mutation('/trips/'+self.tid+'/walking-observation',{'same_scope':True,'condition':'normal','expected_version':2,'client_request_id':str(uuid4())})
        self.assertEqual(fixed[0],200);self.assertEqual(fixed[2]['data']['personalization']['sample_counts']['valid'],5)
        from alembic import command
        from alembic.config import Config
        from sqlalchemy import create_engine,pool
        from app.common import database as common
        from pathlib import Path
        engine=create_engine('postgresql+psycopg://',creator=common.connect_db,poolclass=pool.NullPool)
        try:
            with self.assertRaises(Exception):
                with engine.connect() as c:
                    config=Config(str(Path(__file__).resolve().parents[2]/'alembic.ini'));config.attributes['connection']=c
                    command.downgrade(config,'0018_walking_learning')
        finally:engine.dispose()
        with database() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM trip_event_corrections').fetchone()['n'],1)

del Base
