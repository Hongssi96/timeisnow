"""Explicit AI application on owned mapped access, normal auth and real isolated DB."""
import json,unittest
from decimal import Decimal,ROUND_CEILING
from unittest.mock import patch
from uuid import uuid4
from test_routine_departure import RoutineDepartureTests as Base
from test_arrival_mapping_connection import query_fixture
from test_api_contract import request
from app.arrivals import mapping,provider,cache
from app.ai import provider as ai_provider
from app.guidance import walk_provider,routine
from app.common.database import database

def output(messages):
    value=json.loads(messages[-1]['content']);results=[]
    for c in value['candidates']:
        factor=value['profile']['validated_duration_factor'] or 1.0
        seconds=int((Decimal(str(c['provider_duration_seconds']))*Decimal(str(factor))).to_integral_value(rounding=ROUND_CEILING))
        results.append({k:c[k] for k in ('candidate_id','origin_ref','destination_ref','direction','scope','evidence_ids','missing_segments')}|{
            'status':'ok','base_seconds':c['provider_duration_seconds'],'applied_duration_factor':factor,
            'estimated_seconds':seconds,'method':'provider_duration','reason':'검증한 경로 기준 산정'})
    return json.dumps({'request_id':value['request_id'],'prompt_version':'walking_estimate.v1','results':results})

class PersonalWalkTests(unittest.IsolatedAsyncioTestCase):
    setUp=Base.setUp;tearDown=Base.tearDown;call=Base.call
    prepare=Base.prepare;credentials=Base.credentials;signup_login=Base.signup_login
    saved=Base.saved;create=Base.create;search=Base.search;completed=Base.completed
    saved_search=Base.saved_search;routine_body=Base.routine_body;save=Base.save
    ready=Base.ready;refresh=Base.refresh;path=Base.path

    async def mapped(self):
        await self.ready();self.accepted,_=await self.refresh();self.sid=self.accepted[2]['data']['search_id']
        with patch.object(mapping,'query',side_effect=query_fixture),patch.object(provider,'fetch',return_value=[('123',1800)]):
            result=await self.call(self.path(self.accepted))
        self.assertEqual(result[0],200)

    async def estimate(self,identifier=None,csrf=True,body_extra=None):
        headers=[(b'origin',b'http://127.0.0.1:5173'),(b'content-type',b'application/json'),(b'cookie',self.cookie.encode())]
        if csrf:headers.append((b'x-csrf-token',self.csrf.encode()))
        body={'expected_version':1,'client_request_id':str(identifier or uuid4()),**(body_extra or {})}
        result=await request(f'/api/v1/routines/{self.rid}/departure-searches/{self.sid}/walking-estimates','POST',headers=headers,body=json.dumps(body).encode(),timeout=80)
        return result

    def details(self):return {'seconds':436,'distance_meters':463,'path_fingerprint':'a'*64}

    async def test_real_auth_save_apply_and_no_model_on_departure_get(self):
        await self.mapped()
        with patch.object(walk_provider,'fetch',return_value=self.details()),patch.object(ai_provider,'fetch_estimate',side_effect=output) as model:
            result=await self.estimate();get=await self.call(self.path(self.accepted))
        self.assertEqual(result[0],200);self.assertEqual(result[2]['data']['status'],'validated')
        d=get[2]['data']['departure'];self.assertEqual(d['approach_basis'],'ai_validated');self.assertEqual(d['approach_seconds'],436)
        self.assertEqual(model.call_count,1)
        sent=json.loads(model.call_args.args[0][-1]['content'])
        self.assertEqual(sent['candidates'][0]['origin_ref'],'saved_origin')
        for forbidden in (self.rid,self.sid,'latitude','longitude','station_id','path_fingerprint'):
            self.assertNotIn(forbidden,json.dumps(sent))
        with database() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM walking_estimates').fetchone()['n'],1)

    async def test_replay_and_physical_reuse_and_factor_recalculation_never_repeat_model(self):
        await self.mapped();identifier=uuid4()
        with patch.object(walk_provider,'fetch',return_value=self.details()) as walk,patch.object(ai_provider,'fetch_estimate',side_effect=output) as model:
            one=await self.estimate(identifier);self.assertEqual(one[0],200,one[2]);two=await self.estimate(identifier);reused=await self.estimate()
            with database() as c:c.execute('UPDATE user_profiles SET walking_duration_factor=1.1,version=version+1')
            stale=await self.call(self.path(self.accepted))
            self.assertIsNone(stale[2]['data']['departure']['personal_walk'])
            conflict=await self.estimate(identifier);self.assertEqual(conflict[0],409)
            changed=await self.estimate();get=await self.call(self.path(self.accepted))
        self.assertEqual([x[0] for x in (one,two,reused,changed)],[200]*4)
        self.assertEqual(walk.call_count,1);self.assertEqual(model.call_count,1)
        self.assertTrue(reused[2]['data']['estimate']['reused'])
        self.assertEqual(changed[2]['data']['estimate']['source'],'profile_recalculation')
        self.assertEqual(get[2]['data']['departure']['approach_seconds'],480)
        self.assertEqual(one[2]['data']['estimate']['expires_at'],changed[2]['data']['estimate']['expires_at'])

    async def test_unmapped_and_csrf_and_extra_input_do_not_call_model(self):
        await self.ready();self.accepted,_=await self.refresh();self.sid=self.accepted[2]['data']['search_id']
        with patch.object(ai_provider,'fetch_estimate') as model,patch.object(walk_provider,'fetch') as walk:
            missing=await self.estimate();denied=await self.estimate(csrf=False);extra=await self.estimate(body_extra={'verified':True})
        self.assertEqual(missing[2]['data']['status'],'needs_data');self.assertEqual(denied[0],403);self.assertEqual(extra[0],422)
        model.assert_not_called();walk.assert_not_called()

    async def test_changes_during_ai_prevent_numeric_history_and_application(self):
        await self.mapped()
        def changed(messages):
            with database() as c:c.execute('UPDATE routines SET version=version+1 WHERE id=%s',(self.rid,))
            return output(messages)
        with patch.object(walk_provider,'fetch',return_value=self.details()),patch.object(ai_provider,'fetch_estimate',side_effect=changed):result=await self.estimate()
        self.assertEqual(result[0],409)
        with database() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM walking_estimates').fetchone()['n'],0)

    async def test_invalid_ai_does_not_replace_provider_departure(self):
        await self.mapped()
        def invalid(messages):
            data=json.loads(output(messages));data['results'][0]['estimated_seconds']=999;return json.dumps(data)
        with patch.object(walk_provider,'fetch',return_value=self.details()),patch.object(ai_provider,'fetch_estimate',side_effect=invalid):
            rejected=await self.estimate();get=await self.call(self.path(self.accepted))
        self.assertEqual(rejected[0],502)
        self.assertEqual(get[2]['data']['departure']['approach_basis'],'provider_personalized')

del Base
