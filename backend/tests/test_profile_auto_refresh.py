"""Atomic automatic refresh across verified walking bases; actual owned DB/ASGI."""
import asyncio,copy,json,unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from uuid import uuid4
from test_personalization import PersonalizationTests as Base
from test_ai_walking import fixture
from test_walking_cache import source,synthetic
from app.common.database import database
from app.walking import history_service
from app.personalization import derived
from app.ai import provider as ai_provider
from app.guidance import walk_provider

class ProfileAutoRefreshTests(unittest.IsolatedAsyncioTestCase):
    setUp=Base.setUp;tearDown=Base.tearDown;call=Base.call
    prepare=Base.prepare;credentials=Base.credentials;signup_login=Base.signup_login
    saved=Base.saved;create=Base.create;search=Base.search;completed=Base.completed
    saved_search=Base.saved_search;routine_body=Base.routine_body;save=Base.save
    ready=Base.ready;refresh=Base.refresh;path=Base.path;mapped=Base.mapped;estimate=Base.estimate;details=Base.details
    fixture=Base.fixture;observation=Base.observation;learn=Base.learn

    def seed(self,*,owner=None,refs=None,cached=True):
        value=fixture();value['request_id']='auto.seed.'+str(uuid4())
        value['profile'].update(validated_duration_factor=1.0,fallback_speed_mps=1.2)
        one=value['candidates'][0];one['provider_duration_seconds']=300.25
        two=copy.deepcopy(one);two.update(candidate_id='already_personal',provider_duration_seconds=200.75,provider_duration_includes_personalization=True)
        three=copy.deepcopy(one);three.update(candidate_id='distance_walk',provider_duration_seconds=None,distance_meters=300)
        value['candidates']=[one,two,three]
        result=json.loads(synthetic([{'content':json.dumps(value)}]))
        now=datetime.now(timezone.utc)
        context={'place_refs':refs or [],'verified_at':now-timedelta(seconds=1),'valid_until':now+timedelta(days=2)}
        stored=history_service.persist(owner or self.owner,value,result,context=context,metadata={'model_version':'gpt-5.6-luna'},
          cache_sources=[source(c['candidate_id']) for c in value['candidates']] if cached else None)
        return {v['candidate_id']:v for v in stored['estimates']}

    def rows(self):
        with database() as c:
            return c.execute('SELECT * FROM walking_estimate_revisions ORDER BY calculated_at,id').fetchall()

    async def five(self):
        self.tids=[self.observation() for _ in range(5)]
        for tid in self.tids:self.assertEqual((await self.learn(tid))[0],201)

    async def test_learning_refreshes_all_candidates_preserves_personal_base_and_replay(self):
        await self.fixture();links=self.seed();before=self.rows();self.tids=[self.observation() for _ in range(5)]
        with patch.object(ai_provider,'fetch_estimate') as ai,patch.object(walk_provider,'fetch') as walk:
            for tid in self.tids[:4]:self.assertEqual((await self.learn(tid))[0],201)
            self.assertEqual(len(self.rows()),len(before))
            learned=await self.learn(self.tids[-1]);self.assertTrue(learned[2]['data']['updated'])
            count=len(self.rows());self.assertEqual(count,len(before)*2)
            self.assertEqual((await self.learn(self.tids[-1]))[0],200);self.assertEqual(len(self.rows()),count)
            expected={'walk_001':313,'already_personal':201,'distance_walk':260}
            for candidate,link in links.items():
                response=await self.call('/walking-estimates/'+link['estimate_id']);self.assertEqual(response[0],200,response[2])
                value=response[2]['data'];self.assertEqual(value['estimated_seconds'],expected[candidate])
                self.assertEqual(value['source'],'profile_recalculation');self.assertEqual(value['expires_at'].replace('Z','+00:00'),link['expires_at'].replace('Z','+00:00'))
                self.assertEqual(value['applied_duration_factor'],1 if candidate=='already_personal' else 1.04)
            departure=(await self.call(self.path(self.accepted)))[2]['data']['departure']
            self.assertEqual(departure['approach_seconds'],454);self.assertEqual(departure['personal_walk']['profile_version'],2)
            ai.assert_not_called();walk.assert_not_called()
        with database() as c:
            self.assertEqual(c.execute('SELECT snapshot FROM guidance_snapshots WHERE id=(SELECT guidance_id FROM manual_trips WHERE id=%s)',(self.tid,)).fetchone()['snapshot'],self.snapshot)
            self.assertEqual(c.execute('SELECT first_boarding_buffer_seconds FROM user_profiles').fetchone()['first_boarding_buffer_seconds'],300)

    async def test_reset_restore_refreshes_all_once_and_never_extends_expiry(self):
        await self.fixture();links=self.seed();await self.five();before=self.rows()
        body={'expected_version':2,'client_request_id':str(uuid4())}
        with patch.object(ai_provider,'fetch_estimate') as ai,patch.object(walk_provider,'fetch') as walk:
            reset=await self.call('/me/personalization/reset',body);self.assertEqual(reset[0],200,reset[2])
            count=len(self.rows());self.assertEqual((await self.call('/me/personalization/reset',body))[2]['data'],reset[2]['data']);self.assertEqual(len(self.rows()),count)
            for candidate,link in links.items():
                value=(await self.call('/walking-estimates/'+link['estimate_id']))[2]['data']
                self.assertEqual(value['estimated_seconds'],{'walk_001':301,'already_personal':201,'distance_walk':250}[candidate])
            restore=await self.call('/me/personalization/restore',{'expected_version':3,'client_request_id':str(uuid4())});self.assertEqual(restore[0],200)
            value=(await self.call('/walking-estimates/'+links['walk_001']['estimate_id']))[2]['data'];self.assertEqual(value['estimated_seconds'],313)
            self.assertEqual(value['expires_at'].replace('Z','+00:00'),links['walk_001']['expires_at'].replace('Z','+00:00'))
            self.assertEqual(restore[2]['data']['sample_counts']['valid'],0);ai.assert_not_called();walk.assert_not_called()

    async def test_failed_learning_and_reset_roll_back_factor_samples_generation_and_revisions(self):
        await self.fixture();self.tids=[self.observation() for _ in range(5)]
        for tid in self.tids[:4]:await self.learn(tid)
        with patch.object(derived,'recalculate',side_effect=RuntimeError('synthetic refresh failure')):
            self.assertEqual((await self.learn(self.tids[-1]))[0],500)
        value=(await self.call('/me/personalization'))[2]['data'];self.assertEqual(value['sample_counts']['valid'],4);self.assertEqual(value['profile_version'],1)
        self.assertEqual(len(self.rows()),1);self.assertEqual((await self.learn(self.tids[-1]))[0],201)
        before=len(self.rows());body={'expected_version':2,'client_request_id':str(uuid4())}
        with patch.object(derived,'recalculate',side_effect=RuntimeError('synthetic reset failure')):
            self.assertEqual((await self.call('/me/personalization/reset',body))[0],500)
        value=(await self.call('/me/personalization'))[2]['data'];self.assertEqual(value['sample_counts']['valid'],5);self.assertEqual(value['profile_version'],2)
        self.assertEqual(len(self.rows()),before);self.assertEqual((await self.call('/me/personalization/reset',body))[0],200)

    async def test_invalid_expired_changed_location_and_other_owner_are_not_refreshed(self):
        await self.fixture();healthy=self.seed();uncached=self.seed(cached=False)
        refs=[{'place_id':self.snapshot['place_refs'][0][0],'location_version':self.snapshot['place_refs'][0][1]}]
        changed=self.seed(refs=refs)
        cookie,csrf=self.cookie,self.csrf
        self.cookie=None;self.csrf=None
        await self.prepare();registered=await self.call('/auth/register',self.credentials('other-auto@example.invalid'))
        other=self.seed(owner=registered[2]['data']['user_id']);self.cookie,self.csrf=cookie,csrf
        expired=healthy.pop('distance_walk')
        with database() as c:
            c.execute("UPDATE walking_paths SET calculated_at=clock_timestamp()-interval '3 seconds',expires_at=clock_timestamp()-interval '1 second' WHERE id=(SELECT walking_path_id FROM walking_estimates WHERE id=%s)",(expired['estimate_id'],))
            c.execute('UPDATE saved_places SET location_version=location_version+1 WHERE id=%s',(refs[0]['place_id'],))
        reset=await self.call('/me/personalization/reset',{'expected_version':1,'client_request_id':str(uuid4())});self.assertEqual(reset[0],200,reset[2])
        with database() as c:
            for link in [expired,*uncached.values(),*changed.values(),*other.values()]:
                self.assertEqual(c.execute('SELECT max(revision_no) AS n FROM walking_estimate_revisions WHERE estimate_id=%s',(link['estimate_id'],)).fetchone()['n'],1)
            for link in healthy.values():self.assertEqual(c.execute('SELECT max(revision_no) AS n FROM walking_estimate_revisions WHERE estimate_id=%s',(link['estimate_id'],)).fetchone()['n'],2)

    async def test_concurrent_identical_learning_and_reset_create_one_refresh_each(self):
        await self.fixture();self.tids=[self.observation() for _ in range(5)]
        for tid in self.tids[:4]:await self.learn(tid)
        responses=await asyncio.gather(self.learn(self.tids[-1]),self.learn(self.tids[-1]));self.assertEqual(sorted(r[0] for r in responses),[200,201])
        self.assertEqual(len(self.rows()),2)
        body={'expected_version':2,'client_request_id':str(uuid4())}
        responses=await asyncio.gather(self.call('/me/personalization/reset',body),self.call('/me/personalization/reset',body))
        self.assertEqual([r[0] for r in responses],[200,200]);self.assertEqual(len(self.rows()),3)

del Base
