"""Real PostgreSQL history snapshots/ownership/expiry/rollback, synthetic AI only."""
import copy
import json
import unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from uuid import uuid4
import test_places
from test_ai_walking import fixture,result
from app.common.database import database
from app.common.errors import AuthError
from app.walking import history_service as service,history_repository as repository


class WalkingHistoryTests(unittest.IsolatedAsyncioTestCase):
    setUp=test_places.PlaceTests.setUp
    tearDown=test_places.PlaceTests.tearDown
    call=test_places.PlaceTests.call
    prepare=test_places.PlaceTests.prepare
    credentials=test_places.PlaceTests.credentials
    signup_login=test_places.PlaceTests.signup_login
    saved=test_places.PlaceTests.saved
    create=test_places.PlaceTests.create

    async def setup_owner(self):
        registered=await self.signup_login()
        self.owner=registered[2]['data']['user_id']
        self.value=fixture();self.output=result()
        self.context={'place_refs':[],'verified_at':datetime.now(timezone.utc)-timedelta(seconds=1),
                      'valid_until':datetime.now(timezone.utc)+timedelta(days=60)}
        self.metadata={'model_version':'gpt-5.6-luna','latency_ms':2500,'usage':None}

    def store(self,**kw):
        return service.persist(kw.get('owner',self.owner),kw.get('value',self.value),kw.get('output',self.output),
            context=kw.get('context',self.context),metadata=kw.get('metadata',self.metadata))

    def counts(self):
        with database() as c:
            return tuple(c.execute('SELECT count(*) AS n FROM '+table).fetchone()['n']
                for table in ['ai_executions','walking_paths','walking_estimates','walking_estimate_revisions'])

    async def test_snapshot_get_replay_and_no_provider_calls(self):
        await self.setup_owner()
        with patch('app.ai.provider.fetch_estimate') as upstream:
            stored=self.store();replay=self.store();upstream.assert_not_called()
        self.assertEqual(stored,replay);self.assertEqual(self.counts(),(1,1,1,1))
        estimate=stored['estimates'][0]
        status,headers,body=await self.call('/walking-estimates/'+estimate['estimate_id'])
        self.assertEqual(status,200);self.assertEqual(headers[b'cache-control'],b'no-store')
        data=body['data'];self.assertEqual(data['estimated_seconds'],360);self.assertEqual(data['base_seconds'],300)
        self.assertEqual(data['applied_duration_factor'],1.2);self.assertFalse(data['reused'])
        self.assertEqual(data['revision_id'],estimate['revision_id'])
        with database() as c:
            execution=c.execute('SELECT * FROM ai_executions').fetchone()
            revision=c.execute('SELECT * FROM walking_estimate_revisions').fetchone()
        self.assertEqual(execution['model_version'],'gpt-5.6-luna');self.assertIsNone(execution['usage'])
        self.assertEqual(execution['system_prompt_version'],'common.v1')
        self.assertNotIn('reason',execution['structured_result']['results'][0])
        self.assertAlmostEqual((revision['expires_at']-revision['calculated_at']).total_seconds(),30*86400,delta=0.001)
        self.assertAlmostEqual((execution['retained_until']-execution['created_at']).total_seconds(),90*86400,delta=0.001)
        for secret in ['input_evidence','structured_result','latency_ms','usage','origin_ref']:
            self.assertNotIn(secret,data)

    async def test_conflicting_execution_and_new_snapshot_preserves_old(self):
        await self.setup_owner();old=self.store()
        with self.assertRaises(AuthError) as error:self.store(metadata={**self.metadata,'latency_ms':1})
        self.assertEqual(error.exception.code,'IDEMPOTENCY_CONFLICT');self.assertEqual(self.counts(),(1,1,1,1))
        value=copy.deepcopy(self.value);output=copy.deepcopy(self.output)
        value['request_id']=output['request_id']='req_new';value['profile']['validated_duration_factor']=1.0
        output['results'][0].update(applied_duration_factor=1.0,estimated_seconds=300)
        new=self.store(value=value,output=output)
        self.assertNotEqual(new['estimates'][0]['revision_id'],old['estimates'][0]['revision_id'])
        with database() as c:
            values=c.execute('SELECT estimated_seconds FROM walking_estimate_revisions ORDER BY calculated_at').fetchall()
        self.assertEqual([int(row['estimated_seconds']) for row in values],[360,300])

    async def test_needs_data_and_failed_execution_never_create_estimates(self):
        await self.setup_owner();value=copy.deepcopy(self.value);output=copy.deepcopy(self.output)
        value['candidates'][0]['is_walkable_route']=False
        output['results'][0].update(status='needs_data',base_seconds=None,applied_duration_factor=None,
            estimated_seconds=None,method='none',missing_segments=['WALKABLE_ROUTE_UNCONFIRMED'])
        saved=self.store(value=value,output=output,metadata={'model_version':None})
        self.assertEqual(saved['estimates'],[]);self.assertEqual(self.counts(),(1,0,0,0))
        value['request_id']='req_failed'
        failed=service.record_failure(self.owner,value,context=self.context,metadata={'model_version':None},failure_code='AI_OUTPUT_INVALID')
        self.assertEqual(failed['estimates'],[]);self.assertEqual(self.counts(),(2,0,0,0))
        with database() as c:
            rows=c.execute('SELECT validation_status,failure_code,structured_result FROM ai_executions ORDER BY created_at').fetchall()
        self.assertEqual([row['validation_status'] for row in rows],['needs_data','failed'])
        self.assertIsNone(rows[1]['structured_result'])
        with self.assertRaises(AuthError):service.record_failure(self.owner,value,context=self.context,metadata={'model_version':None},failure_code='private-secret')

    async def test_bad_output_unconfirmed_and_context_are_not_saved(self):
        await self.setup_owner()
        value=copy.deepcopy(self.value);value['candidates'][0]['is_walkable_route']=False
        with self.assertRaises(AuthError):self.store(value=value)
        output=copy.deepcopy(self.output);output['results'][0]['estimated_seconds']=361
        with self.assertRaises(AuthError):self.store(output=output)
        for context in [{**self.context,'valid_until':datetime.now(timezone.utc)-timedelta(seconds=1)},
                        {**self.context,'verified_at':datetime.now(timezone.utc)+timedelta(days=1)},
                        {**self.context,'latitude':37.5}]:
            with self.assertRaises(AuthError):self.store(context=context)
        with self.assertRaises(AuthError):self.store(metadata={'model_version':None})
        self.assertEqual(self.counts(),(0,0,0,0))

    async def test_place_name_position_delete_and_retained_history(self):
        await self.setup_owner();_,created=await self.saved();place=created[2]['data'];identifier=place['place_id']
        self.context['place_refs']=[{'place_id':identifier,'location_version':1}]
        stored=self.store();url='/walking-estimates/'+stored['estimates'][0]['estimate_id']
        with database() as c:c.execute('UPDATE saved_places SET label=%s,version=version+1 WHERE id=%s',('합성 이름 변경',identifier))
        self.assertEqual((await self.call(url))[0],200)
        with database() as c:c.execute('UPDATE saved_places SET location_version=location_version+1 WHERE id=%s',(identifier,))
        self.assertEqual((await self.call(url))[0],409)
        with self.assertRaises(AuthError) as error:self.store()
        self.assertEqual(error.exception.status,409)
        with database() as c:c.execute('DELETE FROM saved_places WHERE id=%s',(identifier,))
        self.assertEqual((await self.call(url))[0],404);self.assertEqual(self.counts(),(1,1,1,1))

    async def test_profile_version_blocks_save_and_read(self):
        await self.setup_owner();stored=self.store()
        with database() as c:c.execute('UPDATE user_profiles SET version=version+1 WHERE user_id=%s',(self.owner,))
        self.assertEqual((await self.call('/walking-estimates/'+stored['estimates'][0]['estimate_id']))[0],409)
        with self.assertRaises(AuthError) as error:self.store()
        self.assertEqual(error.exception.status,409)

    async def test_auth_ownership_wrong_ids_and_place_refs(self):
        await self.setup_owner();_,created=await self.saved();identifier=created[2]['data']['place_id']
        stored=self.store();url='/walking-estimates/'+stored['estimates'][0]['estimate_id']
        self.cookie=None;self.csrf=None
        self.assertEqual((await self.call(url))[0],401)
        await self.prepare();creds=self.credentials('other@example.invalid')
        registered=await self.call('/auth/register',creds);other=registered[2]['data']['user_id']
        logged=await self.call('/auth/login',{'email':creds['email'],'password':creds['password']})
        self.cookie=logged[1][b'set-cookie'].decode().split(';')[0]
        self.assertEqual((await self.call(url))[0],404)
        self.assertEqual((await self.call('/walking-estimates/invalid'))[0],404)
        with self.assertRaises(AuthError) as error:self.store(owner=other,context={**self.context,'place_refs':[{'place_id':identifier,'location_version':1}]})
        self.assertEqual(error.exception.status,404)
        self.assertEqual(self.counts(),(1,1,1,1))

    async def test_evidence_expiry_caps_estimate_and_expired_read_is_blocked(self):
        await self.setup_owner();self.context['valid_until']=datetime.now(timezone.utc)+timedelta(days=2)
        stored=self.store()
        with database() as c:
            row=c.execute('SELECT expires_at FROM walking_estimate_revisions').fetchone()
            self.assertEqual(row['expires_at'],self.context['valid_until'])
            c.execute("UPDATE walking_estimate_revisions SET expires_at=clock_timestamp()-interval '1 second',calculated_at=clock_timestamp()-interval '2 seconds'")
        self.assertEqual((await self.call('/walking-estimates/'+stored['estimates'][0]['estimate_id']))[0],404)
        self.assertEqual(self.counts(),(1,1,1,1))

    async def test_purge_expired_history_and_user_delete_cascade(self):
        await self.setup_owner();self.store()
        with database() as c:
            c.execute("UPDATE walking_paths SET retained_until=clock_timestamp()-interval '1 second',calculated_at=clock_timestamp()-interval '2 seconds'")
            c.execute("UPDATE ai_executions SET retained_until=clock_timestamp()-interval '1 second',created_at=clock_timestamp()-interval '2 seconds'")
        service.purge_expired_history(self.owner);self.assertEqual(self.counts(),(0,0,0,0))
        self.store()
        with database() as c:c.execute('DELETE FROM users WHERE id=%s',(self.owner,))
        self.assertEqual(self.counts(),(0,0,0,0))

    async def test_atomic_rollback_if_revision_insert_fails(self):
        await self.setup_owner()
        with patch.object(repository,'insert_revision',side_effect=RuntimeError('synthetic storage failure')),self.assertRaises(RuntimeError):self.store()
        self.assertEqual(self.counts(),(0,0,0,0))

    async def test_integrated_synthetic_execution_and_failure_history(self):
        await self.setup_owner()
        with patch('app.ai.provider.fetch_estimate',return_value=json.dumps(self.output)) as upstream:
            saved=service.estimate_and_store(self.owner,self.value,context=self.context)
            replay=service.estimate_and_store(self.owner,self.value,context=self.context)
            self.assertEqual(saved['estimates'],replay['estimates'])
        self.assertEqual(upstream.call_count,1);self.assertEqual(len(saved['estimates']),1)
        value=copy.deepcopy(self.value);value['request_id']='req_failure'
        with patch('app.ai.provider.fetch_estimate',side_effect=AuthError(503,'PROVIDER_UNAVAILABLE','safe')) as upstream,self.assertRaises(AuthError):
            service.estimate_and_store(self.owner,value,context=self.context)
        self.assertEqual(upstream.call_count,1);self.assertEqual(self.counts(),(2,1,1,1))

    async def test_integrated_unready_and_ownership_failures_never_call_provider(self):
        await self.setup_owner();value=copy.deepcopy(self.value);value['candidates'][0]['is_walkable_route']=False
        with patch('app.ai.provider.fetch_estimate') as upstream:
            saved=service.estimate_and_store(self.owner,value,context=self.context)
            upstream.assert_not_called()
        self.assertEqual(saved['estimates'],[])
        with database() as c:
            row=c.execute('SELECT model_version,latency_ms FROM ai_executions').fetchone()
        self.assertIsNone(row['model_version']);self.assertIsNone(row['latency_ms'])
        with patch('app.ai.provider.fetch_estimate') as upstream,self.assertRaises(AuthError):
            service.estimate_and_store(str(uuid4()),self.value,context=self.context)
        upstream.assert_not_called()

    async def test_place_changes_during_model_execution_do_not_save(self):
        await self.setup_owner();_,created=await self.saved();identifier=created[2]['data']['place_id']
        self.context['place_refs']=[{'place_id':identifier,'location_version':1}]
        def changed(_):
            with database() as c:c.execute('UPDATE saved_places SET location_version=location_version+1 WHERE id=%s',(identifier,))
            return json.dumps(self.output)
        with patch('app.ai.provider.fetch_estimate',side_effect=changed),self.assertRaises(AuthError) as error:
            service.estimate_and_store(self.owner,self.value,context=self.context)
        self.assertEqual(error.exception.status,409);self.assertEqual(self.counts(),(0,0,0,0))

    async def test_database_composite_fk_blocks_cross_owner_revision(self):
        await self.setup_owner();saved=self.store()
        with database() as c:
            other=uuid4();c.execute("INSERT INTO users(id,display_name) VALUES(%s,'synthetic other')",(other,))
            row=c.execute('SELECT * FROM walking_estimate_revisions').fetchone()
        from app.common import database as common_database
        import psycopg
        with common_database.connect_db() as c:
            with self.assertRaises(psycopg.errors.ForeignKeyViolation):
                with c.transaction():
                    c.execute('UPDATE walking_estimate_revisions SET user_id=%s WHERE id=%s',(other,row['id']))
        self.assertEqual(self.counts(),(1,1,1,1))

    async def test_overlapping_execution_is_blocked_before_second_model_call(self):
        await self.setup_owner()
        def overlapping(_):
            with self.assertRaises(AuthError) as error:
                service.estimate_and_store(self.owner,self.value,context=self.context)
            self.assertEqual(error.exception.code,'EXECUTION_IN_PROGRESS')
            return json.dumps(self.output)
        with patch('app.ai.provider.fetch_estimate',side_effect=overlapping) as upstream:
            saved=service.estimate_and_store(self.owner,self.value,context=self.context)
            replay=service.estimate_and_store(self.owner,self.value,context=self.context)
        self.assertEqual(upstream.call_count,1);self.assertEqual(saved['estimates'],replay['estimates'])
        self.assertEqual(self.counts(),(1,1,1,1))

    def test_openapi_estimate_contract(self):
        from app.main import app
        response=app.openapi()['paths']['/api/v1/walking-estimates/{estimate_id}']['get']['responses']['200']
        self.assertEqual(response['content']['application/json']['schema']['$ref'],'#/components/schemas/EstimateEnvelope')


if __name__=='__main__':unittest.main()
