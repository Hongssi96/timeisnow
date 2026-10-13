"""Physical cache contract, expiry and concurrency on isolated PostgreSQL; mock AI."""
import copy
import json
import unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from uuid import uuid4
import test_walking_history as history
from app.common.database import database
from app.common.errors import AuthError
from app.ai.walking_service import parse_input,expected
from app.walking import history_service as service


def source(candidate_id='walk_001'):
    return dict(candidate_id=candidate_id,provider='synthetic',provider_path_ref='route_1',path_version='v1',
        origin_entrance_ref='entrance_1',destination_entrance_ref='not_applicable',condition_version='v1')


def synthetic(messages):
    value=parse_input(json.loads(messages[-1]['content']))
    results=[]
    for candidate in value.candidates:
        base,factor,seconds,method=expected(candidate,value.profile)
        results.append({key:getattr(candidate,key) for key in ['candidate_id','origin_ref','destination_ref','direction','scope','evidence_ids','missing_segments']} |
            dict(status='ok',base_seconds=base,applied_duration_factor=factor,estimated_seconds=seconds,method=method,reason='synthetic'))
    return json.dumps(dict(request_id=value.request_id,prompt_version='walking_estimate.v1',results=results))


class WalkingCacheTests(unittest.IsolatedAsyncioTestCase):
    setUp=history.WalkingHistoryTests.setUp
    tearDown=history.WalkingHistoryTests.tearDown
    call=history.WalkingHistoryTests.call
    prepare=history.WalkingHistoryTests.prepare
    credentials=history.WalkingHistoryTests.credentials
    signup_login=history.WalkingHistoryTests.signup_login
    saved=history.WalkingHistoryTests.saved
    create=history.WalkingHistoryTests.create
    setup_owner=history.WalkingHistoryTests.setup_owner
    counts=history.WalkingHistoryTests.counts

    def seed(self,sources=None):
        return service.persist(self.owner,self.value,self.output,context=self.context,metadata=self.metadata,
            cache_sources=[source()] if sources is None else sources)

    def next_value(self,name='req_next'):
        value=copy.deepcopy(self.value);value['request_id']=name
        value['candidates'][0]['candidate_id']='walk_new';value['candidates'][0]['evidence_ids']=['evidence_new']
        return value

    def run_cached(self,value=None,sources=None,context=None,owner=None):
        value=value or self.next_value()
        return service.estimate_and_store(owner or self.owner,value,context=context or self.context,
            cache_sources=sources if sources is not None else [source(value['candidates'][0]['candidate_id'])])

    async def test_full_hit_remaps_ids_preserves_expiry_no_model_or_numeric_writes(self):
        await self.setup_owner();original=self.seed()
        with patch('app.ai.provider.fetch_estimate') as upstream:
            first=self.run_cached();replay=self.run_cached();upstream.assert_not_called()
        self.assertEqual(first['estimates'],replay['estimates']);self.assertEqual(self.counts(),(2,1,1,1))
        entry=first['estimates'][0];old=original['estimates'][0]
        self.assertTrue(entry['reused']);self.assertEqual(entry['estimate_id'],old['estimate_id'])
        self.assertEqual(entry['revision_id'],old['revision_id']);self.assertEqual(entry['expires_at'],old['expires_at'])
        result=first['result']['results'][0];self.assertEqual(result['candidate_id'],'walk_new')
        self.assertEqual(result['evidence_ids'],['evidence_new']);self.assertEqual(result['estimated_seconds'],360)
        with database() as c:
            row=c.execute("SELECT * FROM ai_executions WHERE request_id='req_next'").fetchone()
        for key in ('model_version','latency_ms','usage'):self.assertIsNone(row[key])
        self.assertEqual(len(row['reused_estimates']),1)
        status,_,body=await self.call('/walking-estimates/'+entry['estimate_id'])
        self.assertEqual(status,200);self.assertFalse(body['data']['reused'])

    async def test_mixed_hit_only_misses_sent_and_replay_is_complete(self):
        await self.setup_owner();self.seed();value=self.next_value()
        other=copy.deepcopy(value['candidates'][0]);other['candidate_id']='walk_other';other['direction']='inbound'
        value['candidates'].append(other);sources=[source('walk_new'),source('walk_other')]
        with patch('app.ai.provider.fetch_estimate',side_effect=synthetic) as upstream:
            first=self.run_cached(value,sources);replay=self.run_cached(value,sources)
        self.assertEqual(upstream.call_count,1)
        sent=json.loads(upstream.call_args.args[0][-1]['content'])
        self.assertEqual([item['candidate_id'] for item in sent['candidates']],['walk_other'])
        self.assertEqual(first['estimates'],replay['estimates']);self.assertEqual(self.counts(),(2,2,2,2))
        self.assertEqual({item['candidate_id']:item['reused'] for item in first['estimates']},{'walk_new':True,'walk_other':False})
        with database() as c:
            row=c.execute("SELECT model_version FROM ai_executions WHERE request_id='req_next'").fetchone()
        self.assertEqual(row['model_version'],'gpt-5.6-luna')

    async def test_physical_condition_changes_are_misses(self):
        await self.setup_owner();self.seed()
        changes=[('direction','inbound'),('scope','stop_to_place_entrance'),('provider_duration_seconds',301),
            ('distance_meters',351),('provider_duration_includes_personalization',True),('origin_ref','place_v2'),('destination_ref','stop_2')]
        variants=[]
        for key,replacement in changes:
            value=self.next_value('req_'+key);value['candidates'][0][key]=replacement
            if key=='scope':value['candidates'][0]['required_scope']=replacement
            variants.append((value,[source('walk_new')]))
        for key in ['provider','provider_path_ref','path_version','origin_entrance_ref','destination_entrance_ref','condition_version']:
            value=self.next_value('req_'+key);identity=source('walk_new');identity[key]='changed'
            variants.append((value,[identity]))
        for value,sources in variants:
            with self.subTest(value['request_id']),patch('app.ai.provider.fetch_estimate',side_effect=synthetic) as upstream:
                saved=self.run_cached(value,sources)
                self.assertEqual(upstream.call_count,1);self.assertFalse(saved['estimates'][0]['reused'])

    async def test_missing_or_invalid_identity_and_unready_never_reuse(self):
        await self.setup_owner();self.seed()
        with patch('app.ai.provider.fetch_estimate',side_effect=synthetic) as upstream:
            saved=service.estimate_and_store(self.owner,self.next_value(),context=self.context)
        self.assertEqual(upstream.call_count,1);self.assertFalse(saved['estimates'][0]['reused'])
        for replacement in ('unknown','none','not_applicable'):
            identity=source('walk_new');identity['path_version']=replacement
            with patch('app.ai.provider.fetch_estimate') as upstream,self.assertRaises(AuthError) as error:
                self.run_cached(self.next_value('req_invalid_'+replacement),[identity])
            self.assertEqual(error.exception.status,422);upstream.assert_not_called()
        value=self.next_value('req_unready');value['candidates'][0]['is_walkable_route']=False
        with patch('app.ai.provider.fetch_estimate') as upstream:
            saved=self.run_cached(value);upstream.assert_not_called()
        self.assertEqual(saved['estimates'],[]);self.assertEqual(saved['result']['results'][0]['status'],'needs_data')

    async def test_legacy_cache_identity_is_not_inferred(self):
        await self.setup_owner();service.persist(self.owner,self.value,self.output,context=self.context,metadata=self.metadata)
        with patch('app.ai.provider.fetch_estimate',side_effect=synthetic) as upstream:saved=self.run_cached()
        self.assertEqual(upstream.call_count,1);self.assertFalse(saved['estimates'][0]['reused'])
        with database() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM walking_paths WHERE cache_key IS NULL').fetchone()['n'],1)

    async def test_profile_only_change_recalculates_without_ai(self):
        await self.setup_owner();self.seed();value=self.next_value()
        value['profile']['validated_duration_factor']=1.3
        with patch('app.ai.provider.fetch_estimate') as upstream:saved=self.run_cached(value)
        upstream.assert_not_called();self.assertEqual(saved['result']['results'][0]['estimated_seconds'],390)
        self.assertEqual(saved['estimates'][0]['source'],'profile_recalculation')
        value['profile']['version']=2;value['request_id']='req_profile_v2'
        with database() as c:c.execute('UPDATE user_profiles SET version=2 WHERE user_id=%s',(self.owner,))
        with patch('app.ai.provider.fetch_estimate') as upstream:saved=self.run_cached(value)
        upstream.assert_not_called();self.assertEqual(saved['result']['results'][0]['estimated_seconds'],390)
        self.assertEqual(self.counts(),(3,1,1,3))

    async def test_effective_expiry_capped_without_extending_source(self):
        await self.setup_owner();original=self.seed()
        context={**self.context,'valid_until':datetime.now(timezone.utc)+timedelta(hours=1)}
        with patch('app.ai.provider.fetch_estimate') as upstream:saved=self.run_cached(context=context);upstream.assert_not_called()
        self.assertEqual(saved['estimates'][0]['expires_at'],context['valid_until'].isoformat())
        with database() as c:row=c.execute('SELECT expires_at FROM walking_estimate_revisions').fetchone()
        self.assertEqual(row['expires_at'].isoformat(),original['estimates'][0]['expires_at'])
        with patch('app.ai.provider.fetch_estimate') as upstream,self.assertRaises(AuthError):
            self.run_cached(self.next_value('req_expired_context'),context={**context,'valid_until':datetime.now(timezone.utc)-timedelta(seconds=1)})
        upstream.assert_not_called()

    async def test_expired_source_misses_and_dangling_replay_is_blocked(self):
        await self.setup_owner();self.seed();cached=self.run_cached()
        with database() as c:
            c.execute("UPDATE walking_estimate_revisions SET calculated_at=clock_timestamp()-interval '2 seconds',expires_at=clock_timestamp()-interval '1 second'")
        with patch('app.ai.provider.fetch_estimate') as upstream,self.assertRaises(AuthError) as error:self.run_cached()
        self.assertEqual(error.exception.status,404);upstream.assert_not_called()
        with patch('app.ai.provider.fetch_estimate',side_effect=synthetic) as upstream:self.run_cached(self.next_value('req_new_after_expiry'))
        self.assertEqual(upstream.call_count,1)
        with database() as c:c.execute('DELETE FROM walking_paths WHERE id=(SELECT walking_path_id FROM walking_estimates WHERE id=%s)',(cached['estimates'][0]['estimate_id'],))
        with patch('app.ai.provider.fetch_estimate') as upstream,self.assertRaises(AuthError) as error:self.run_cached()
        self.assertEqual(error.exception.status,404);upstream.assert_not_called()

    async def test_wrong_owner_does_not_receive_cached_value(self):
        await self.setup_owner();old=self.seed()
        await self.prepare();registered=await self.call('/auth/register',self.credentials('other@example.invalid'))
        self.assertEqual(registered[0],201);new_owner=registered[2]['data']['user_id']
        with patch('app.ai.provider.fetch_estimate',side_effect=synthetic) as upstream:saved=self.run_cached(owner=new_owner)
        self.assertEqual(upstream.call_count,1);self.assertFalse(saved['estimates'][0]['reused'])
        self.assertNotEqual(saved['estimates'][0]['estimate_id'],old['estimates'][0]['estimate_id'])

    async def test_name_keeps_hit_location_change_and_delete_block(self):
        await self.setup_owner();_,created=await self.saved();place_id=created[2]['data']['place_id']
        self.context['place_refs']=[dict(place_id=place_id,location_version=1)];self.seed()
        with database() as c:c.execute("UPDATE saved_places SET name='renamed',version=version+1 WHERE id=%s",(place_id,))
        with patch('app.ai.provider.fetch_estimate') as upstream:self.run_cached();upstream.assert_not_called()
        with database() as c:c.execute('UPDATE saved_places SET location_version=2 WHERE id=%s',(place_id,))
        with patch('app.ai.provider.fetch_estimate') as upstream,self.assertRaises(AuthError) as error:self.run_cached(self.next_value('req_changed_place'))
        self.assertEqual(error.exception.status,409);upstream.assert_not_called()
        context={**self.context,'place_refs':[dict(place_id=place_id,location_version=2)]}
        with patch('app.ai.provider.fetch_estimate',side_effect=synthetic) as upstream:saved=self.run_cached(self.next_value('req_current_place'),context=context)
        self.assertEqual(upstream.call_count,1);self.assertFalse(saved['estimates'][0]['reused'])
        with database() as c:c.execute('DELETE FROM saved_places WHERE id=%s',(place_id,))
        with patch('app.ai.provider.fetch_estimate') as upstream,self.assertRaises(AuthError) as error:self.run_cached(self.next_value('req_deleted_place'),context=context)
        self.assertEqual(error.exception.status,404);upstream.assert_not_called()

    async def test_tampered_numeric_source_is_rejected_without_model(self):
        await self.setup_owner();self.seed()
        with database() as c:c.execute('UPDATE walking_estimate_revisions SET estimated_seconds=361')
        with patch('app.ai.provider.fetch_estimate') as upstream,self.assertRaises(AuthError) as error:self.run_cached()
        self.assertEqual(error.exception.code,'AI_OUTPUT_INVALID');upstream.assert_not_called()
        self.assertEqual(self.counts(),(1,1,1,1))

    async def test_same_key_different_requests_overlap_once_then_hit(self):
        await self.setup_owner()
        def overlapping(messages):
            with self.assertRaises(AuthError) as error:self.run_cached(self.next_value('req_overlap'))
            self.assertEqual(error.exception.code,'EXECUTION_IN_PROGRESS')
            return synthetic(messages)
        with patch('app.ai.provider.fetch_estimate',side_effect=overlapping) as upstream:
            first=self.run_cached(self.value,[source()]);second=self.run_cached()
        self.assertEqual(upstream.call_count,1);self.assertTrue(second['estimates'][0]['reused'])
        self.assertEqual(first['estimates'][0]['estimate_id'],second['estimates'][0]['estimate_id'])

    async def test_cache_source_change_conflicts_on_same_request_id(self):
        await self.setup_owner();self.seed();self.run_cached()
        other=source('walk_new');other['condition_version']='v2'
        with patch('app.ai.provider.fetch_estimate') as upstream,self.assertRaises(AuthError) as error:self.run_cached(sources=[other])
        self.assertEqual(error.exception.code,'IDEMPOTENCY_CONFLICT');upstream.assert_not_called()

    async def test_failed_miss_releases_physical_locks(self):
        await self.setup_owner()
        with patch('app.ai.provider.fetch_estimate',side_effect=AuthError(503,'PROVIDER_UNAVAILABLE','safe')),self.assertRaises(AuthError):self.run_cached()
        with patch('app.ai.provider.fetch_estimate',side_effect=synthetic) as upstream:saved=self.run_cached(self.next_value('req_after_failure'))
        self.assertEqual(upstream.call_count,1);self.assertFalse(saved['estimates'][0]['reused'])

    async def test_distance_fallback_cache_and_changed_speed(self):
        await self.setup_owner()
        self.value['candidates'][0]['provider_duration_seconds']=None
        self.value['profile']['fallback_speed_mps']=1.2
        self.output=json.loads(synthetic([{'content':json.dumps(self.value)}]));self.seed()
        with patch('app.ai.provider.fetch_estimate') as upstream:saved=self.run_cached();upstream.assert_not_called()
        self.assertEqual(saved['result']['results'][0]['method'],'distance_speed')
        value=self.next_value('req_speed_changed');value['profile']['fallback_speed_mps']=1.3
        with patch('app.ai.provider.fetch_estimate',side_effect=synthetic) as upstream:saved=self.run_cached(value)
        self.assertEqual(upstream.call_count,1);self.assertFalse(saved['estimates'][0]['reused'])

    async def test_source_expires_during_miss_rolls_back_combined_result(self):
        await self.setup_owner();self.seed();value=self.next_value()
        other=copy.deepcopy(value['candidates'][0]);other['candidate_id']='walk_other';other['direction']='inbound'
        value['candidates'].append(other)
        def expired(messages):
            with database() as c:c.execute("UPDATE walking_estimate_revisions SET calculated_at=clock_timestamp()-interval '2 seconds',expires_at=clock_timestamp()-interval '1 second'")
            return synthetic(messages)
        with patch('app.ai.provider.fetch_estimate',side_effect=expired) as upstream,self.assertRaises(AuthError) as error:
            self.run_cached(value,[source('walk_new'),source('walk_other')])
        self.assertEqual(error.exception.status,404);self.assertEqual(upstream.call_count,1)
        self.assertEqual(self.counts(),(1,1,1,1))

    async def test_cache_versions_and_ephemeral_identifiers(self):
        await self.setup_owner()
        from dataclasses import replace
        from app.walking import cache_service as cache
        from app.ai.prompt_loader import load_prompt
        request=parse_input(self.value);candidate=request.candidates[0]
        key,_=cache.identity(candidate,request,[],source())
        changed=parse_input(self.next_value())
        self.assertEqual(key,cache.identity(changed.candidates[0],changed,[],source('walk_new'))[0])
        bundle=load_prompt('walking_estimate')
        for changed_bundle in [replace(bundle,system=replace(bundle.system,version='common.v2')),
            replace(bundle,developer=replace(bundle.developer,version='walking_estimate.v2'))]:
            with patch.object(cache,'load_prompt',return_value=changed_bundle):self.assertNotEqual(key,cache.identity(candidate,request,[],source())[0])
        with patch.object(cache,'MODEL','another_model'):self.assertNotEqual(key,cache.identity(candidate,request,[],source())[0])

    async def test_long_factor_is_preserved_in_numeric_storage(self):
        await self.setup_owner();self.value['profile']['validated_duration_factor']=1.2345678912345678
        self.output=json.loads(synthetic([{'content':json.dumps(self.value)}]));self.seed()
        with patch('app.ai.provider.fetch_estimate') as upstream:saved=self.run_cached();upstream.assert_not_called()
        self.assertEqual(saved['result']['results'][0]['applied_duration_factor'],1.2345678912345678)
        with database() as c:stored=c.execute('SELECT applied_duration_factor FROM walking_estimate_revisions').fetchone()
        self.assertEqual(str(stored['applied_duration_factor']),str(self.value['profile']['validated_duration_factor']))


if __name__=='__main__':unittest.main()
