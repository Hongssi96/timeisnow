"""Owned decimal recalculations preserve baseline, provenance and expiry; no real AI."""
import copy
import json
import unittest
from datetime import datetime,timedelta,timezone
from decimal import Decimal,ROUND_CEILING
from unittest.mock import patch
from uuid import uuid4
import test_walking_cache as cache_tests
from app.common.database import database
from app.common.errors import AuthError
from app.walking import history_service as service,history_repository as repository


class WalkingRecalculationTests(unittest.IsolatedAsyncioTestCase):
    setUp=cache_tests.WalkingCacheTests.setUp
    tearDown=cache_tests.WalkingCacheTests.tearDown
    call=cache_tests.WalkingCacheTests.call
    prepare=cache_tests.WalkingCacheTests.prepare
    credentials=cache_tests.WalkingCacheTests.credentials
    signup_login=cache_tests.WalkingCacheTests.signup_login
    saved=cache_tests.WalkingCacheTests.saved
    create=cache_tests.WalkingCacheTests.create
    setup_owner=cache_tests.WalkingCacheTests.setup_owner
    counts=cache_tests.WalkingCacheTests.counts
    seed=cache_tests.WalkingCacheTests.seed
    next_value=cache_tests.WalkingCacheTests.next_value
    run_cached=cache_tests.WalkingCacheTests.run_cached

    def changed(self,factor=1.1,version=2,name='req_changed'):
        with database() as c:c.execute('UPDATE user_profiles SET version=%s WHERE user_id=%s',(version,self.owner))
        value=self.next_value(name);value['profile']['version']=version
        value['profile']['validated_duration_factor']=factor
        return value

    async def test_recalculation_same_estimate_new_revision_and_public_source(self):
        await self.setup_owner();original=self.seed();value=self.changed()
        with patch('app.ai.provider.fetch_estimate') as upstream:saved=self.run_cached(value)
        upstream.assert_not_called();self.assertEqual(saved['result']['results'][0]['estimated_seconds'],330)
        old=original['estimates'][0];new=saved['estimates'][0]
        self.assertEqual(old['estimate_id'],new['estimate_id']);self.assertNotEqual(old['revision_id'],new['revision_id'])
        self.assertEqual(old['expires_at'],new['expires_at']);self.assertFalse(new['reused'])
        self.assertEqual(new['source'],'profile_recalculation');self.assertEqual(new['candidate_id'],'walk_new')
        self.assertEqual(self.counts(),(2,1,1,2))
        with database() as c:
            rows=c.execute('SELECT * FROM walking_estimate_revisions ORDER BY revision_no').fetchall()
            execution=c.execute("SELECT * FROM ai_executions WHERE request_id='req_changed'").fetchone()
        self.assertEqual(int(rows[0]['estimated_seconds']),360);self.assertEqual(rows[1]['parent_revision_id'],rows[0]['id'])
        self.assertEqual(rows[1]['revision_no'],2);self.assertEqual(rows[1]['retained_until'],rows[0]['retained_until'])
        self.assertGreater(rows[1]['calculated_at'],rows[0]['calculated_at'])
        for key in ['model_version','latency_ms','usage']:self.assertIsNone(execution[key])
        status,_,body=await self.call('/walking-estimates/'+new['estimate_id'])
        self.assertEqual(status,200);self.assertEqual(body['data']['source'],'profile_recalculation')
        self.assertEqual(body['data']['estimated_seconds'],330);self.assertFalse(body['data']['reused'])

    async def test_chain_replay_and_same_profile_reuse_never_double_apply(self):
        await self.setup_owner();self.seed();v2=self.changed();v3=self.changed(.8,3,'req_v3')
        # Restore active profile for the first execution.
        with database() as c:c.execute('UPDATE user_profiles SET version=2 WHERE user_id=%s',(self.owner,))
        with patch('app.ai.provider.fetch_estimate') as upstream:
            first=self.run_cached(v2);replay=self.run_cached(v2)
            with database() as c:c.execute('UPDATE user_profiles SET version=3 WHERE user_id=%s',(self.owner,))
            second=self.run_cached(v3)
            next_value=copy.deepcopy(v3);next_value['request_id']='req_v3_reuse';next_value['candidates'][0]['evidence_ids']=['new_evidence']
            reused=self.run_cached(next_value)
        upstream.assert_not_called();self.assertEqual(first['estimates'],replay['estimates'])
        self.assertEqual(second['result']['results'][0]['estimated_seconds'],240)
        self.assertEqual(reused['estimates'][0]['revision_id'],second['estimates'][0]['revision_id']);self.assertTrue(reused['estimates'][0]['reused'])
        self.assertEqual(self.counts(),(4,1,1,3))
        with database() as c:rows=c.execute('SELECT * FROM walking_estimate_revisions ORDER BY revision_no').fetchall()
        self.assertEqual(rows[2]['parent_revision_id'],rows[1]['id']);self.assertEqual([float(row['base_seconds']) for row in rows],[300,300,300])

    async def test_factor_defaults_bounds_and_invalid_values(self):
        await self.setup_owner();self.seed()
        for version,(factor,seconds) in enumerate([(None,300),(.5,150),(2.0,600)],2):
            value=self.changed(factor,version,'req_factor_'+str(version))
            with patch('app.ai.provider.fetch_estimate') as upstream:saved=self.run_cached(value)
            upstream.assert_not_called();self.assertEqual(saved['result']['results'][0]['estimated_seconds'],seconds)
        for factor in (.49,2.01,float('nan')):
            value=self.changed(factor,5,'req_invalid')
            with patch('app.ai.provider.fetch_estimate') as upstream,self.assertRaises(AuthError) as error:self.run_cached(value)
            self.assertEqual(error.exception.status,422);upstream.assert_not_called()

    async def test_already_personalized_provider_is_not_multiplied_again(self):
        await self.setup_owner();self.value['candidates'][0]['provider_duration_includes_personalization']=True
        self.output=json.loads(cache_tests.synthetic([{'content':json.dumps(self.value)}]));self.seed()
        with patch('app.ai.provider.fetch_estimate') as upstream:saved=self.run_cached(self.changed(1.3))
        upstream.assert_not_called();result=saved['result']['results'][0]
        self.assertEqual(result['estimated_seconds'],300);self.assertEqual(result['applied_duration_factor'],1.0)

    async def test_decimal_baseline_ceil_and_fallback_reuse(self):
        await self.setup_owner();self.value['candidates'][0]['provider_duration_seconds']=None
        self.value['profile']['fallback_speed_mps']=1.2
        self.output=json.loads(cache_tests.synthetic([{'content':json.dumps(self.value)}]));self.seed()
        value=self.changed(1.0)
        with database() as c:base=c.execute('SELECT base_seconds FROM walking_estimate_revisions').fetchone()['base_seconds']
        with patch('app.ai.provider.fetch_estimate') as upstream:
            first=self.run_cached(value)
            second=self.run_cached(self.changed(1.2,3,'req_decimal'))
            same=self.changed(1.2,3,'req_decimal_reuse');reused=self.run_cached(same)
        upstream.assert_not_called();self.assertEqual(first['result']['results'][0]['estimated_seconds'],int(base.to_integral_value(rounding=ROUND_CEILING)))
        seconds=int((base*Decimal('1.2')).to_integral_value(rounding=ROUND_CEILING))
        self.assertEqual(second['result']['results'][0]['estimated_seconds'],seconds)
        self.assertEqual(reused['result']['results'][0]['estimated_seconds'],seconds);self.assertTrue(reused['estimates'][0]['reused'])

    async def test_current_revision_reuse_ignores_reversed_calculation_clock(self):
        await self.setup_owner();self.seed()
        with patch('app.ai.provider.fetch_estimate') as upstream:
            self.run_cached(self.changed(1.1,2,'req_clock_first'))
            latest=self.run_cached(self.changed(1.2,3,'req_clock_latest'))
            with database() as c:
                # A later revision may have an earlier wall-clock timestamp.
                c.execute("UPDATE walking_estimate_revisions SET calculated_at=clock_timestamp()-CASE WHEN revision_no=3 THEN interval '1 second' ELSE interval '0 second' END WHERE revision_no>=2")
            reused=self.run_cached(self.changed(1.2,3,'req_clock_reuse'))
        upstream.assert_not_called()
        self.assertTrue(reused['estimates'][0]['reused'])
        self.assertEqual(reused['estimates'][0]['revision_id'],latest['estimates'][0]['revision_id'])

    async def test_mixed_reuse_recalculation_and_fresh_only_fresh_calls_ai(self):
        await self.setup_owner();self.seed();value=self.changed()
        second=copy.deepcopy(value);second['request_id']='req_seed_current';second['candidates'][0]['destination_ref']='stop_current'
        second['candidates'][0]['candidate_id']='walk_current'
        with patch('app.ai.provider.fetch_estimate',side_effect=cache_tests.synthetic):self.run_cached(second,[cache_tests.source('walk_current')])
        third=copy.deepcopy(value['candidates'][0]);third['candidate_id']='walk_fresh';third['direction']='inbound'
        value['candidates']+=[second['candidates'][0],third]
        sources=[cache_tests.source(candidate['candidate_id']) for candidate in value['candidates']]
        with patch('app.ai.provider.fetch_estimate',side_effect=cache_tests.synthetic) as upstream:
            saved=self.run_cached(value,sources);replay=self.run_cached(value,sources)
        self.assertEqual(upstream.call_count,1);sent=json.loads(upstream.call_args.args[0][-1]['content'])
        self.assertEqual([item['candidate_id'] for item in sent['candidates']],['walk_fresh'])
        self.assertEqual(saved['estimates'],replay['estimates']);self.assertEqual(self.counts(),(3,3,3,4))
        entries={item['candidate_id']:item for item in saved['estimates']}
        self.assertEqual(entries['walk_new']['source'],'profile_recalculation');self.assertTrue(entries['walk_current']['reused'])

    async def test_parent_corruption_blocks_without_ai_or_partial_writes(self):
        await self.setup_owner();self.seed();value=self.changed()
        with database() as c:c.execute('UPDATE walking_estimate_revisions SET estimated_seconds=999')
        with patch('app.ai.provider.fetch_estimate') as upstream,self.assertRaises(AuthError) as error:self.run_cached(value)
        self.assertEqual(error.exception.code,'AI_OUTPUT_INVALID');upstream.assert_not_called();self.assertEqual(self.counts(),(1,1,1,1))

    async def test_shorter_context_caps_derived_expiry(self):
        await self.setup_owner();original=self.seed();value=self.changed()
        context={**self.context,'valid_until':datetime.now(timezone.utc)+timedelta(hours=1)}
        with patch('app.ai.provider.fetch_estimate') as upstream:saved=self.run_cached(value,context=context)
        upstream.assert_not_called();self.assertEqual(saved['estimates'][0]['expires_at'],context['valid_until'].isoformat())
        with database() as c:rows=c.execute('SELECT expires_at FROM walking_estimate_revisions ORDER BY revision_no').fetchall()
        self.assertEqual(rows[0]['expires_at'].isoformat(),original['estimates'][0]['expires_at'])

    async def test_expired_parent_or_changed_direction_use_new_estimate(self):
        await self.setup_owner();old=self.seed();value=self.changed()
        with database() as c:c.execute("UPDATE walking_estimate_revisions SET calculated_at=clock_timestamp()-interval '2 seconds',expires_at=clock_timestamp()-interval '1 second'")
        with patch('app.ai.provider.fetch_estimate',side_effect=cache_tests.synthetic) as upstream:saved=self.run_cached(value)
        self.assertEqual(upstream.call_count,1);self.assertEqual(saved['estimates'][0]['source'],'ai_estimate')
        self.assertNotEqual(saved['estimates'][0]['estimate_id'],old['estimates'][0]['estimate_id'])
        value=self.changed(.9,3,'req_direction');value['candidates'][0]['direction']='inbound'
        with patch('app.ai.provider.fetch_estimate',side_effect=cache_tests.synthetic) as upstream:saved=self.run_cached(value)
        self.assertEqual(upstream.call_count,1);self.assertEqual(saved['estimates'][0]['source'],'ai_estimate')

    async def test_stale_profile_and_place_version_block_before_recalculation(self):
        await self.setup_owner();_,saved=await self.saved();place_id=saved[2]['data']['place_id']
        # This test isolates version conflicts from unrelated wall-clock adjustments.
        with patch.object(repository,'clock',return_value=self.context['verified_at']+timedelta(seconds=1)):
            self.context['place_refs']=[dict(place_id=place_id,location_version=1)];self.seed()
            value=self.changed();stale=copy.deepcopy(value);stale['profile']['version']=1
            with patch('app.ai.provider.fetch_estimate') as upstream,self.assertRaises(AuthError) as error:self.run_cached(stale)
            self.assertEqual(error.exception.code,'VERSION_CONFLICT');upstream.assert_not_called()
            with database() as c:c.execute('UPDATE saved_places SET location_version=2 WHERE id=%s',(place_id,))
            with patch('app.ai.provider.fetch_estimate') as upstream,self.assertRaises(AuthError) as error:self.run_cached(value)
            self.assertEqual(error.exception.status,409);upstream.assert_not_called();self.assertEqual(self.counts(),(1,1,1,1))

    async def test_expiry_during_other_miss_rolls_back_recalculation(self):
        await self.setup_owner();self.seed();value=self.changed()
        other=copy.deepcopy(value['candidates'][0]);other['candidate_id']='walk_other';other['direction']='inbound';value['candidates'].append(other)
        def expired(messages):
            with database() as c:c.execute("UPDATE walking_estimate_revisions SET calculated_at=clock_timestamp()-interval '2 seconds',expires_at=clock_timestamp()-interval '1 second'")
            return cache_tests.synthetic(messages)
        with patch('app.ai.provider.fetch_estimate',side_effect=expired),self.assertRaises(AuthError) as error:
            self.run_cached(value,[cache_tests.source('walk_new'),cache_tests.source('walk_other')])
        self.assertEqual(error.exception.status,404);self.assertEqual(self.counts(),(1,1,1,1))

    async def test_revision_failure_rolls_back_and_releases_lock(self):
        await self.setup_owner();self.seed();value=self.changed()
        with patch.object(repository,'insert_recalculation',side_effect=RuntimeError('synthetic')),self.assertRaises(RuntimeError):self.run_cached(value)
        self.assertEqual(self.counts(),(1,1,1,1))
        with patch('app.ai.provider.fetch_estimate') as upstream:saved=self.run_cached(value)
        upstream.assert_not_called();self.assertEqual(saved['estimates'][0]['source'],'profile_recalculation')

    async def test_same_physical_key_overlap_creates_one_derived_revision(self):
        await self.setup_owner();self.seed();value=self.changed();original=repository.insert_recalculation
        def overlapping(connection,values):
            other=copy.deepcopy(value);other['request_id']='req_overlap'
            with self.assertRaises(AuthError) as error:self.run_cached(other)
            self.assertEqual(error.exception.code,'EXECUTION_IN_PROGRESS')
            return original(connection,values)
        with patch.object(repository,'insert_recalculation',side_effect=overlapping),patch('app.ai.provider.fetch_estimate') as upstream:self.run_cached(value)
        upstream.assert_not_called();self.assertEqual(self.counts(),(2,1,1,2))

    async def test_other_profile_fields_are_not_silently_recalculated(self):
        await self.setup_owner();self.seed();value=self.changed();value['profile']['fallback_speed_mps']=1.2
        with patch('app.ai.provider.fetch_estimate') as upstream,self.assertRaises(AuthError) as error:self.run_cached(value)
        self.assertEqual(error.exception.code,'PROFILE_RECALCULATION_REQUIRED');upstream.assert_not_called()

    async def test_parent_deleted_blocks_replay_and_source_fk_cascades(self):
        await self.setup_owner();self.seed();value=self.changed();saved=self.run_cached(value)
        with database() as c:c.execute('DELETE FROM walking_estimate_revisions WHERE revision_no=1')
        with patch('app.ai.provider.fetch_estimate') as upstream,self.assertRaises(AuthError) as error:self.run_cached(value)
        self.assertEqual(error.exception.status,404);upstream.assert_not_called();self.assertEqual(self.counts()[3],0)

    async def test_parent_fk_rejects_different_estimate(self):
        await self.setup_owner();first=self.seed();other=copy.deepcopy(self.value)
        other['request_id']='req_other_estimate';other['candidates'][0]['destination_ref']='stop_other'
        output=json.loads(cache_tests.synthetic([{'content':json.dumps(other)}]))
        service.persist(self.owner,other,output,context=self.context,metadata=self.metadata,cache_sources=[cache_tests.source()])
        saved=self.run_cached(self.changed())
        with database() as c:other_parent=c.execute('SELECT id FROM walking_estimate_revisions WHERE estimate_id<>%s',(first['estimates'][0]['estimate_id'],)).fetchone()['id']
        from app.common.database import connect_db
        import psycopg
        with connect_db() as c:
            with self.assertRaises(psycopg.errors.ForeignKeyViolation):
                with c.transaction():c.execute('UPDATE walking_estimate_revisions SET parent_revision_id=%s WHERE id=%s',(other_parent,saved['estimates'][0]['revision_id']))
        self.assertEqual(self.counts(),(3,2,2,3))

    async def test_migration_rollback_preserves_original_snapshot(self):
        await self.setup_owner();original=self.seed();self.run_cached(self.changed())
        from pathlib import Path
        from alembic import command
        from alembic.config import Config
        from sqlalchemy import create_engine,pool,text
        from app.common.database import connect_db
        engine=create_engine('postgresql+psycopg://',creator=connect_db,poolclass=pool.NullPool)
        try:
            with engine.connect() as c:
                config=Config(str(Path(__file__).resolve().parents[2]/'alembic.ini'));config.attributes['connection']=c
                command.downgrade(config,'0010_walking_cache')
                row=c.execute(text('SELECT id,source,estimated_seconds FROM walking_estimate_revisions')).one()
                self.assertEqual(str(row[0]),original['estimates'][0]['revision_id']);self.assertEqual(row[1],'ai_estimate');self.assertEqual(int(row[2]),360)
                c.commit();command.upgrade(config,'head')
                self.assertIsNone(c.execute(text('SELECT parent_revision_id FROM walking_estimate_revisions')).scalar_one());c.commit()
        finally:engine.dispose()

    def test_public_source_enum_includes_recalculation(self):
        from app.main import app
        self.assertEqual(set(app.openapi()['components']['schemas']['EstimateSummary']['properties']['source']['enum']),{'ai_estimate','profile_recalculation'})

    async def test_direct_persistence_output_identity_errors_remain_502(self):
        await self.setup_owner()
        for key in ('request_id','candidate_id'):
            output=copy.deepcopy(self.output)
            if key=='request_id':output[key]='wrong'
            else:output['results'][0][key]='wrong'
            with self.assertRaises(AuthError) as error:service.persist(self.owner,self.value,output,context=self.context,metadata=self.metadata)
            self.assertEqual(error.exception.code,'AI_OUTPUT_INVALID');self.assertEqual(error.exception.status,502)
        self.assertEqual(self.counts(),(0,0,0,0))


if __name__=='__main__':unittest.main()
