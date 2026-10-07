"""Real PostgreSQL/ASGI with synthetic provider inputs; no real device location."""
import asyncio
import copy
import io
import json
import logging
import unittest
import urllib.error
from unittest.mock import patch
from uuid import uuid4
import test_places
from test_api_contract import request
from app import auth, places, journeys, journey_provider


def route(seconds=900, transfers=0, walking=100, kind='BUS'):
    def step(kind,time):
        return {'properties':{'type':kind,'time':time,'distance':100,
            'stops':[{'name':'합성 승차'},{'name':'합성 하차'}],'vehicles':[{'name':'합성 10'}]},
            'path':{'points':[[127.0276,37.4979],[126.9726,37.5547]]}}
    return {'properties':{'type':kind,'totalTime':seconds,'totalDistance':1000,'transfers':transfers},
        'steps':[step('WALKING',walking),step('SUBWAY' if kind=='SUBWAY' else 'BUS',500),step('WALKING',50)]}


BODY={'origin':{'type':'map_pin','latitude':37.4979,'longitude':127.0276},
      'destination':{'type':'map_pin','latitude':37.5547,'longitude':126.9726},
      'timing':{'mode':'depart_now','timezone':'Asia/Seoul'}}


class JourneyTests(unittest.IsolatedAsyncioTestCase):
    setUp=test_places.PlaceTests.setUp
    tearDown=test_places.PlaceTests.tearDown
    call=test_places.PlaceTests.call
    prepare=test_places.PlaceTests.prepare
    credentials=test_places.PlaceTests.credentials
    signup_login=test_places.PlaceTests.signup_login
    saved=test_places.PlaceTests.saved
    create=test_places.PlaceTests.create

    async def search(self,body=BODY,key=None,csrf=True):
        headers=[(b'origin',b'http://127.0.0.1:5173'),(b'content-type',b'application/json')]
        if self.cookie: headers.append((b'cookie',self.cookie.encode()))
        if csrf and self.csrf: headers.append((b'x-csrf-token',self.csrf.encode()))
        if key is not None: headers.append((b'idempotency-key',key.encode()))
        return await request('/api/v1/journey-searches','POST',headers=headers,body=json.dumps(body).encode())

    async def completed(self,body=BODY,key=None,data=None):
        with patch.object(places,'region_for_location',return_value='서울 합성동'),patch.object(journey_provider,'fetch_routes',return_value=data or {'status':'OK','routes':[route()]}) as provider:
            accepted=await self.search(body,key)
        self.assertEqual(accepted[0],202)
        result=await self.call('/journey-searches/'+accepted[2]['data']['search_id'])
        return accepted,result,provider

    async def test_async_contract_privacy_and_idempotency(self):
        await self.signup_login()
        from app.request_logging import logger, RequestJsonFormatter, RequestEventFilter
        output=io.StringIO();handler=logging.StreamHandler(output)
        handler.setFormatter(RequestJsonFormatter());handler.addFilter(RequestEventFilter())
        previous,level=logger.handlers[:],logger.level;logger.handlers[:]=[handler];logger.setLevel(logging.INFO)
        try: accepted,result,provider=await self.completed(key='safe-retry')
        finally: logger.handlers[:]=previous;logger.setLevel(level)
        self.assertEqual(accepted[1][b'cache-control'],b'no-store')
        self.assertEqual(result[2]['data']['status'],'succeeded')
        candidate=result[2]['data']['candidates'][0]
        self.assertEqual(candidate['validity'],'insufficient_data');self.assertIsNone(candidate['estimated_arrival_at'])
        self.assertEqual(candidate['walking_seconds'],150);provider.assert_called_once()
        job=await self.call('/jobs/'+accepted[2]['data']['job_id'])
        self.assertEqual(job[2]['data']['status'],'succeeded');self.assertNotIn('candidates',job[2]['data'])
        self.assertEqual(job[2]['data']['result_ref'],'/api/v1/journey-searches/'+accepted[2]['data']['search_id'])
        from app.main import app
        self.assertIn('202',app.openapi()['paths']['/api/v1/journey-searches']['post']['responses'])
        with patch.object(journey_provider,'fetch_routes') as upstream:
            replay=await self.search(key='safe-retry');upstream.assert_not_called()
        self.assertEqual(replay[2]['data'],accepted[2]['data'])
        changed=copy.deepcopy(BODY);changed['origin']['latitude']=37.5
        self.assertEqual((await self.search(changed,key='safe-retry'))[0],409)
        with auth.database() as c:
            row=c.execute('SELECT * FROM journey_searches').fetchone()
            text=json.dumps(row,default=str)
            hashed=c.execute('SELECT body_hash FROM journey_search_keys').fetchone()['body_hash'];self.assertEqual(len(hashed),64)
        for private in ['37.4979','127.0276','37.5547','126.9726','captured_at','accuracy_meters','guidance','landingURL']:
            self.assertNotIn(private,text);self.assertNotIn(private,output.getvalue())

    async def test_auth_csrf_inputs_and_manual_gps(self):
        with patch.object(journey_provider,'fetch_routes') as provider:
            self.assertEqual((await self.search())[0],401)
            await self.signup_login();self.assertEqual((await self.search(csrf=False))[0],403)
            current={**BODY['origin'],'type':'current_location','accuracy_meters':50000,'captured_at':'2099-01-01T00:00:00Z'}
            for value in [None,False,1,'true']:
                origin=dict(current)
                if value is not None: origin['location_confirmed']=value
                self.assertEqual((await self.search({**BODY,'origin':origin}))[0],422)
            self.assertEqual((await self.search({**BODY,'user_id':str(uuid4())}))[0],422)
            self.assertEqual((await self.search(key='bad key'))[0],422)
            self.assertEqual((await self.search({**BODY,'timing':{'mode':'arrive_by','timezone':'Asia/Seoul','arrive_by':'2099-01-01T00:00:00Z'}}))[2]['error']['code'],'UNSUPPORTED_TIMING')
            provider.assert_not_called()
        _,result,_=await self.completed({**BODY,'origin':{**current,'location_confirmed':True}})
        self.assertEqual(result[2]['data']['status'],'succeeded')

    async def test_saved_version_name_changes_deletion_and_foreign_owner(self):
        await self.signup_login();_,created=await self.saved();place=created[2]['data']
        body={**BODY,'origin':{'type':'saved_place','place_id':place['place_id'],'location_version':1}}
        accepted,_,_=await self.completed(body,key='saved-key');path='/journey-searches/'+accepted[2]['data']['search_id']
        with auth.database() as c:c.execute('UPDATE saved_places SET label=%s,version=version+1 WHERE id=%s',('다른 이름',place['place_id']))
        self.assertEqual((await self.call(path))[0],200)
        with auth.database() as c:c.execute('UPDATE saved_places SET location_version=location_version+1 WHERE id=%s',(place['place_id'],))
        self.assertEqual((await self.call(path))[0],409);self.assertEqual((await self.search(body,key='saved-key'))[0],409)
        with auth.database() as c:c.execute('DELETE FROM saved_places WHERE id=%s',(place['place_id'],))
        self.assertEqual((await self.call(path))[0],404)
        self.cookie=None;self.csrf=None;await self.prepare()
        credentials=self.credentials('other@example.invalid');await self.call('/auth/register',credentials)
        logged=await self.call('/auth/login',{'email':credentials['email'],'password':credentials['password']})
        self.cookie=logged[1][b'set-cookie'].decode().split(';')[0];self.csrf=logged[2]['data']['csrf_token']
        self.assertEqual((await self.call(path))[0],404)
        self.assertEqual((await self.call('/jobs/'+accepted[2]['data']['job_id']))[0],404)

    async def test_expiry_restart_and_late_worker_cannot_resurrect(self):
        await self.signup_login();accepted,_,_=await self.completed(key='expiry')
        identifier=accepted[2]['data']['search_id'];job_id=accepted[2]['data']['job_id']
        with auth.database() as c:c.execute("UPDATE journey_searches SET expires_at=now(),status='running',worker_deadline=now()-interval '1 second'")
        self.assertEqual((await self.call('/journey-searches/'+identifier))[0],404)
        job=(await self.call('/jobs/'+job_id))[2]['data']
        self.assertEqual(job['error']['code'],'JOB_INTERRUPTED');self.assertTrue(job['result_expired'])
        self.assertIsNone(job['result_ref'])
        self.assertEqual((await self.search(key='expiry'))[0],404)
        with auth.database() as c:
            row=c.execute('SELECT * FROM journey_searches').fetchone();self.assertEqual(row['candidates'],[])
            user_id=row['user_id']
        with patch.object(journey_provider,'fetch_routes') as provider:
            journeys.execute(identifier,user_id,None,None,'balanced')
            provider.assert_not_called()
        with auth.database() as c:c.execute('UPDATE journey_searches SET job_expires_at=now()')
        self.assertEqual((await self.call('/jobs/'+job_id))[0],404)

    async def test_failed_worker_and_empty_results_are_distinct(self):
        await self.signup_login()
        for failure in [auth.AuthError(504,'PROVIDER_TIMEOUT','합성 실패'),auth.AuthError(503,'PROVIDER_UNAVAILABLE','합성 실패'),ValueError('private raw payload')]:
            with patch.object(places,'region_for_location',return_value='서울 합성동'),patch.object(journey_provider,'fetch_routes',side_effect=failure):
                accepted=await self.search()
            data=(await self.call('/journey-searches/'+accepted[2]['data']['search_id']))[2]['data']
            self.assertEqual(data['status'],'failed');self.assertEqual(data['candidates'],[])
            self.assertNotIn('private',json.dumps(data));self.assertEqual(data['error']['code'],failure.code if isinstance(failure,auth.AuthError) else 'INTERNAL_ERROR')
        _,result,_=await self.completed(data={'status':'NO_RESULTS'})
        self.assertEqual(result[2]['data']['status'],'succeeded');self.assertEqual(result[2]['data']['unavailable_reasons'],['NO_ROUTE'])

    async def test_concurrent_keys_admission_and_quota(self):
        await self.signup_login()
        with patch.object(journeys,'execute'),patch.object(journey_provider,'fetch_routes') as upstream:
            first,second=await asyncio.gather(self.search(key='concurrent'),self.search(key='concurrent'))
            self.assertEqual(first[0],202);self.assertEqual(second[0],202);self.assertEqual(first[2]['data'],second[2]['data'])
            pending=await self.call('/journey-searches/'+first[2]['data']['search_id'])
            self.assertEqual(pending[1][b'retry-after'],b'2')
            self.assertEqual((await self.search())[0],202);self.assertEqual((await self.search())[0],429)
            upstream.assert_not_called()
        with auth.database() as c:c.execute("UPDATE journey_searches SET status='failed'")
        with patch.object(places,'region_for_location',side_effect=auth.AuthError(422,'UNSUPPORTED_REGION','합성 실패')):
            for _ in range(10): last=await self.search()
        self.assertEqual(last[0],429)

    async def test_worker_rechecks_location_after_provider_returns(self):
        await self.signup_login();_,created=await self.saved();place=created[2]['data']
        body={**BODY,'origin':{'type':'saved_place','place_id':place['place_id'],'location_version':1}}
        def changed(*args):
            with auth.database() as c:c.execute('UPDATE saved_places SET location_version=2 WHERE id=%s',(place['place_id'],))
            return {'status':'OK','routes':[route()]}
        with patch.object(places,'region_for_location',return_value='서울 합성동'),patch.object(journey_provider,'fetch_routes',side_effect=changed):
            accepted=await self.search(body)
        job=(await self.call('/jobs/'+accepted[2]['data']['job_id']))[2]['data']
        self.assertEqual(job['status'],'failed');self.assertEqual(job['error']['code'],'VERSION_CONFLICT')
        with auth.database() as c:self.assertEqual(c.execute('SELECT candidates FROM journey_searches').fetchone()['candidates'],[])

    async def test_cached_legacy_models_upgrade_without_provider_or_id_changes(self):
        from app.journey_models import LegacyCandidate, LegacyLeg, SearchEnvelope
        from app.main import app
        from psycopg.types.json import Jsonb
        await self.signup_login()
        value=route(seconds=1500,transfers=1)
        value['steps'].insert(2,copy.deepcopy(value['steps'][0]))
        value['steps'].insert(3,copy.deepcopy(value['steps'][1]))
        accepted,result,_=await self.completed(data={'status':'OK','routes':[value]})
        SearchEnvelope.model_validate(result[2])
        self.assertIn('Candidate',app.openapi()['components']['schemas'])
        original=result[2]['data']['candidates'][0]
        old={key:copy.deepcopy(original[key]) for key in LegacyCandidate.model_fields}
        old['ordered_legs']=[{key:copy.deepcopy(leg[key]) for key in LegacyLeg.model_fields} for leg in original['ordered_legs']]
        identifier=accepted[2]['data']['search_id'];path='/journey-searches/'+identifier
        with auth.database() as c:c.execute('UPDATE journey_searches SET candidates=%s WHERE id=%s',(Jsonb([old]),identifier))
        with patch.object(journey_provider,'fetch_routes') as provider:
            first=(await self.call(path))[2]['data']['candidates'][0]
            second=(await self.call(path))[2]['data']['candidates'][0]
            self.assertEqual(first,second);self.assertEqual(first['candidate_id'],old['candidate_id'])
            self.assertEqual(first['connections'],original['connections'])
            self.assertIsNone(first['ordered_legs'][1]['vehicle_options'][0]['provider_type']);provider.assert_not_called()
        with auth.database() as c:
            persisted=c.execute('SELECT candidates FROM journey_searches WHERE id=%s',(identifier,)).fetchone()['candidates'][0]
            self.assertNotIn('model_version',persisted)
            old['ordered_legs'][0]['latitude']=37.5
            c.execute('UPDATE journey_searches SET candidates=%s WHERE id=%s',(Jsonb([old]),identifier))
        failed=await self.call(path);self.assertEqual(failed[0],502)
        self.assertNotIn('37.5',json.dumps(failed[2]))


class ProviderTests(unittest.TestCase):
    def test_normalize_sort_cap_and_discard_raw_coordinates(self):
        rows=[route(800,1,50),route(1000,0,300),route(700,3,20)]
        for preference,expected in [('balanced',800),('fewer_transfers',1000),('less_walking',800)]:
            candidates,reasons=journey_provider.normalize({'status':'OK','routes':rows},preference)
            self.assertEqual(candidates[0]['total_seconds'],expected);self.assertEqual(len(candidates),2)
            self.assertIn('TRANSFER_LIMIT',reasons);self.assertNotIn('127.0276',json.dumps(candidates))

    def test_rejects_corrupt_payloads_without_leaking(self):
        invalid=[None,{'status':'INVALID_REQUEST'},{'status':'OK','routes':'bad'}]
        for field,value in [('totalTime',True),('totalDistance',-1),('transfers',1.2)]:
            item=route();item['properties'][field]=value;invalid.append({'status':'OK','routes':[item]})
        item=route();item['steps'][0]['path']['points']=[[float('nan'),37]];invalid.append({'status':'OK','routes':[item]})
        for data in invalid:
            with self.assertRaises(auth.AuthError) as error:journey_provider.normalize(data,'balanced')
            self.assertEqual(error.exception.code,'PROVIDER_RESPONSE_INVALID')

    def test_transport_timeout_and_redirect_failure_are_safe(self):
        for failure,code in [(TimeoutError('private'),'PROVIDER_TIMEOUT'),
                             (urllib.error.URLError(TimeoutError('private')),'PROVIDER_TIMEOUT'),
                             (urllib.error.HTTPError('private',302,'private',{},None),'PROVIDER_UNAVAILABLE'),
                             (ValueError('private'),'PROVIDER_RESPONSE_INVALID')]:
            with patch.dict(auth.os.environ,{'KAKAO_REST_API_KEY':'synthetic'}),patch('urllib.request.build_opener') as opener:
                opener.return_value.open.side_effect=failure
                with self.assertRaises(auth.AuthError) as error:journey_provider.fetch_routes(places.Location(latitude=37.5,longitude=127),places.Location(latitude=37.6,longitude=127))
            self.assertEqual(error.exception.code,code);self.assertNotIn('private',error.exception.message)

    def test_oversized_response_is_rejected(self):
        with patch.dict(auth.os.environ,{'KAKAO_REST_API_KEY':'synthetic'}),patch('urllib.request.build_opener') as opener:
            response=opener.return_value.open.return_value.__enter__.return_value
            response.read.return_value=b'x'*2097153
            with self.assertRaises(auth.AuthError) as error:journey_provider.fetch_routes(places.Location(latitude=37.5,longitude=127),places.Location(latitude=37.6,longitude=127))
        self.assertEqual(error.exception.code,'PROVIDER_RESPONSE_INVALID');response.read.assert_called_once_with(2097153)
