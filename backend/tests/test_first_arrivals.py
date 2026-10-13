"""First boarding ownership, provider identity and strict freshness; synthetic upstream."""
import copy,json,unittest,urllib.error
from datetime import datetime,timedelta,timezone
from unittest.mock import patch,MagicMock
from uuid import UUID,uuid4
import test_walking as walking
from app.arrivals import service,provider
from app.arrivals.dto import Mapping
from app.common.database import database
from app.common.errors import AuthError


def mapping(leg=None):
    at=datetime.now(timezone.utc)
    return Mapping(provider='gyeonggi-bus',first_leg_id=leg or uuid4(),station_id='200000177',route_id='200000037',sta_order=19,
        route_dest_id='200000999',mapping_version='map.v1',verified_at=at-timedelta(seconds=1),valid_until=at+timedelta(minutes=10))

def packet(**changes):
    row={'stationId':'200000177','routeId':'200000037','staOrder':19,'routeDestId':'200000999','flag':'RUN',
        'predictTimeSec1':300,'predictTimeSec2':600,'vehId1':123,'vehId2':456};row.update(changes)
    return json.dumps({'response':{'msgHeader':{'resultCode':0,'queryTime':'2030-01-01 12:00:00'},'msgBody':{'busArrivalItem':row}}})


class ParserTests(unittest.TestCase):
    def test_seconds_not_minutes_and_identity_filter(self):
        self.assertEqual(provider.parse(packet(predictTime1=99),mapping()),[('123',300),('456',600)])
        for key in ('stationId','routeId','staOrder','routeDestId'):
            with self.subTest(key),self.assertRaises(AuthError) as error:provider.parse(packet(**{key:'wrong'}),mapping())
            self.assertEqual(error.exception.code,'PROVIDER_RESPONSE_INVALID')

    def test_empty_business_error_and_malformed_schema(self):
        self.assertEqual(provider.parse('{"response":{"msgHeader":{"resultCode":4}}}',mapping()),[])
        with self.assertRaises(AuthError) as error:provider.parse('{"response":{"msgHeader":{"resultCode":2}}}',mapping())
        self.assertEqual(error.exception.code,'PROVIDER_UNAVAILABLE')
        for raw in ('[]','bad','{"response":null}','{"response":{"msgHeader":{"resultCode":0},"msgBody":[1]}}'):
            with self.assertRaises(AuthError) as error:provider.parse(raw,mapping())
            self.assertEqual(error.exception.code,'PROVIDER_RESPONSE_INVALID')

    def test_operational_and_missing_predictions_never_become_zero(self):
        for value in (0,-1,None,'WAIT','3.1',True,86401):
            self.assertEqual(provider.parse(packet(predictTimeSec1=value,predictTimeSec2=value),mapping()),None)
        for flag in ('WAIT','PASS','unknown'):self.assertIsNone(provider.parse(packet(flag=flag),mapping()))
        self.assertEqual(provider.parse(packet(flag='STOP'),mapping()),[])
        with self.assertRaises(AuthError):provider.parse(packet(vehId2=123),mapping())

    def test_transport_bounded_https_without_logging(self):
        m=mapping();opener=MagicMock();reply=MagicMock();opener.open.return_value.__enter__.return_value=reply;reply.read.return_value=packet().encode()
        with patch.object(provider,'dotenv_values',return_value={'DATA_GO_KR_SERVICE_KEY':'synthetic%2Bkey'}),patch.object(provider.urllib.request,'build_opener',return_value=opener):
            self.assertEqual(provider.fetch(m),[('123',300),('456',600)])
        args=opener.open.call_args;self.assertTrue(args.args[0].startswith('https://apis.data.go.kr/'))
        self.assertEqual(args.kwargs['timeout'],3);reply.read.assert_called_once_with(262145)
        for error,code in [(TimeoutError(),'PROVIDER_TIMEOUT'),(urllib.error.URLError(TimeoutError()),'PROVIDER_TIMEOUT'),(urllib.error.URLError('private upstream'),'PROVIDER_UNAVAILABLE')]:
            opener.open.side_effect=error
            with patch.object(provider,'dotenv_values',return_value={'DATA_GO_KR_SERVICE_KEY':'synthetic'}),patch.object(provider.urllib.request,'build_opener',return_value=opener),self.assertRaises(AuthError) as raised:provider.fetch(m)
            self.assertEqual(raised.exception.code,code);self.assertNotIn('private',raised.exception.message)

    def test_oversized_duplicate_and_nonfinite_payloads_rejected(self):
        for raw in ('{"response":{},"response":{}}','{"response":{"msgHeader":{"resultCode":NaN}}}'):
            with self.assertRaises(AuthError) as error:provider.parse(raw,mapping())
            self.assertEqual(error.exception.code,'PROVIDER_RESPONSE_INVALID')
        opener=MagicMock();opener.open.return_value.__enter__.return_value.read.return_value=b'x'*262145
        with patch.dict(provider.os.environ,{},clear=True),patch.object(provider,'dotenv_values',return_value={'DATA_GO_KR_SERVICE_KEY':'synthetic'}),patch.object(provider.urllib.request,'build_opener',return_value=opener),self.assertRaises(AuthError) as error:provider.fetch(mapping())
        self.assertEqual(error.exception.code,'PROVIDER_RESPONSE_INVALID')

    def test_missing_key_does_not_call_and_zero_vehicle_is_unconfirmed(self):
        with patch.dict(provider.os.environ,{},clear=True),patch.object(provider,'dotenv_values',return_value={}),patch.object(provider.urllib.request,'build_opener') as opener,self.assertRaises(AuthError):provider.fetch(mapping())
        opener.assert_not_called()
        self.assertIsNone(provider.parse(packet(vehId1=0,vehId2=0),mapping()))

    def normalize(self,age=0,generated=True,values=None,received_age=0):
        at=datetime.now(timezone.utc);m=mapping();return service.normalize(m,values if values is not None else [('123',300),('456',100)],at-timedelta(seconds=received_age),at,
            uuid4(),uuid4(),at+timedelta(minutes=5),at-timedelta(seconds=age) if generated else None)

    def test_trusted_source_uses_generation_anchor_and_sorts(self):
        evidence=self.normalize(age=20);self.assertTrue(evidence.valid_for_guidance)
        self.assertEqual([value.provider_prediction_seconds for value in evidence.candidates],[100,300])
        self.assertEqual(evidence.candidates[0].predicted_arrival_at-evidence.generated_at,timedelta(seconds=100))

    def test_unknown_source_and_clock_mismatch_are_not_fresh(self):
        evidence=self.normalize(generated=False);self.assertEqual(evidence.status,'insufficient_data')
        self.assertFalse(evidence.valid_for_guidance);self.assertIsNone(evidence.candidates[0].predicted_arrival_at)
        evidence=self.normalize(age=-1);self.assertEqual(evidence.source_status,'clock_mismatch');self.assertFalse(evidence.valid_for_guidance)

    def test_120_second_boundary_and_receipt_expiry(self):
        self.assertTrue(self.normalize(age=120).valid_for_guidance)
        for evidence in (self.normalize(age=120.001),self.normalize(received_age=120.001)):
            self.assertEqual(evidence.status,'expired');self.assertFalse(evidence.valid_for_guidance)

    def test_expired_predictions_and_naive_generation_never_imply_boarding(self):
        at=datetime.now(timezone.utc);m=mapping()
        result=service.normalize(m,[('123',10)],at,at,uuid4(),uuid4(),at+timedelta(minutes=5),at-timedelta(seconds=20))
        self.assertEqual(result.candidates,[]);self.assertFalse(result.valid_for_guidance)
        result=service.normalize(m,[('123',10)],at,at,uuid4(),uuid4(),at+timedelta(minutes=5),at.replace(tzinfo=None))
        self.assertEqual(result.source_status,'unknown');self.assertIsNone(result.generated_at)


class ArrivalApiTests(unittest.IsolatedAsyncioTestCase):
    setUp=walking.WalkingTests.setUp
    tearDown=walking.WalkingTests.tearDown
    call=walking.WalkingTests.call
    prepare=walking.WalkingTests.prepare
    credentials=walking.WalkingTests.credentials
    signup_login=walking.WalkingTests.signup_login
    saved=walking.WalkingTests.saved
    create=walking.WalkingTests.create
    search=walking.WalkingTests.search
    completed=walking.WalkingTests.completed
    evidence_path=walking.WalkingTests.evidence_path

    async def setup_route(self):
        await self.signup_login();path,search_id=await self.evidence_path()
        _,_,body=await self.call(path);self.search_id=UUID(search_id);self.candidate_id=UUID(body['data']['candidate_id'])
        with database() as c:self.owner=c.execute('SELECT user_id FROM journey_searches WHERE id=%s',(self.search_id,)).fetchone()['user_id']
        _,_,first,_=service.owned(self.owner,self.search_id,self.candidate_id);self.mapping=mapping(UUID(first['leg_id']))
        self.path=path.replace('walking-evidence','first-arrivals')

    async def test_owned_read_mapping_required_no_fetch_or_writes(self):
        await self.setup_route()
        with database() as c:before=c.execute('SELECT * FROM journey_searches WHERE id=%s',(self.search_id,)).fetchone()
        with patch.object(provider,'fetch') as upstream:
            one=await self.call(self.path);two=await self.call(self.path+'?station_id=200000177&verified=true');upstream.assert_not_called()
        self.assertEqual(one[0],200);self.assertEqual(one[1][b'cache-control'],b'no-store')
        self.assertEqual(one[2]['data'],two[2]['data']);self.assertEqual(one[2]['data']['status'],'mapping_required')
        self.assertFalse(one[2]['data']['valid_for_guidance']);self.assertEqual(one[2]['data']['candidates'],[])
        with database() as c:after=c.execute('SELECT * FROM journey_searches WHERE id=%s',(self.search_id,)).fetchone()
        self.assertEqual(before,after)

    async def test_ownership_auth_expiry_and_no_provider(self):
        await self.setup_route()
        with patch.object(provider,'fetch') as upstream:
            self.assertEqual((await self.call(self.path.replace(str(self.search_id),str(uuid4()))))[0],404)
            self.cookie=None;self.csrf=None;self.assertEqual((await self.call(self.path))[0],401)
            with self.assertRaises(AuthError):service.first_arrivals(uuid4(),self.search_id,self.candidate_id,verified_mapping=self.mapping)
            with database() as c:c.execute("UPDATE journey_searches SET expires_at=clock_timestamp()-interval '1 second' WHERE id=%s",(self.search_id,))
            with self.assertRaises(AuthError):service.first_arrivals(self.owner,self.search_id,self.candidate_id,verified_mapping=self.mapping)
            upstream.assert_not_called()

    async def test_internal_verified_fetch_keeps_generation_unknown(self):
        await self.setup_route()
        with patch.object(provider,'fetch',return_value=[('123',300)]) as upstream:
            result=service.first_arrivals(self.owner,self.search_id,self.candidate_id,verified_mapping=self.mapping)
        self.assertEqual(upstream.call_count,1);self.assertEqual(result.source_status,'unknown');self.assertFalse(result.valid_for_guidance)
        self.assertIsNone(result.candidates[0].predicted_arrival_at)
        encoded=result.model_dump_json()
        for secret in ('200000177','200000037','plateNo','latitude','serviceKey'):self.assertNotIn(secret,encoded)

    async def test_wrong_or_expired_mapping_never_fetches(self):
        await self.setup_route()
        for value in (self.mapping.model_copy(update={'first_leg_id':uuid4()}),self.mapping.model_copy(update={'valid_until':datetime.now(timezone.utc)-timedelta(seconds=1),'verified_at':datetime.now(timezone.utc)-timedelta(seconds=10)})):
            with patch.object(provider,'fetch') as upstream,self.assertRaises(AuthError):service.first_arrivals(self.owner,self.search_id,self.candidate_id,verified_mapping=value)
            upstream.assert_not_called()

    async def test_search_changes_during_fetch_block_result(self):
        await self.setup_route()
        def expired(_):
            with database() as c:c.execute("UPDATE journey_searches SET expires_at=clock_timestamp()-interval '1 second' WHERE id=%s",(self.search_id,))
            return [('123',300)]
        with patch.object(provider,'fetch',side_effect=expired),self.assertRaises(AuthError):service.first_arrivals(self.owner,self.search_id,self.candidate_id,verified_mapping=self.mapping)

    async def test_saved_place_location_change_blocks_before_and_after_fetch(self):
        await self.signup_login();_,home=await self.saved('출발');_,work=await self.saved('도착')
        origin_id=home[2]['data']['place_id'];destination_id=work[2]['data']['place_id']
        body=copy.deepcopy(walking.BODY);body['origin']={'type':'saved_place','place_id':origin_id};body['destination']={'type':'saved_place','place_id':destination_id}
        path,search_id=await self.evidence_path(body=body);_,_,reply=await self.call(path)
        search_id=UUID(search_id);candidate_id=UUID(reply['data']['candidate_id'])
        with database() as c:owner=c.execute('SELECT user_id FROM journey_searches WHERE id=%s',(search_id,)).fetchone()['user_id']
        _,_,first,_=service.owned(owner,search_id,candidate_id);m=mapping(UUID(first['leg_id']))
        def changed(_):
            with database() as c:c.execute('UPDATE saved_places SET location_version=2 WHERE id=%s',(origin_id,))
            return [('123',300)]
        with patch.object(provider,'fetch',side_effect=changed),self.assertRaises(AuthError) as error:service.first_arrivals(owner,search_id,candidate_id,verified_mapping=m)
        self.assertEqual(error.exception.status,409)
        with patch.object(provider,'fetch') as upstream,self.assertRaises(AuthError):service.first_arrivals(owner,search_id,candidate_id,verified_mapping=m)
        upstream.assert_not_called()

    def test_openapi_read_only_contract(self):
        from app.main import app
        path=app.openapi()['paths']['/api/v1/journey-searches/{search_id}/candidates/{candidate_id}/first-arrivals']
        self.assertEqual(set(path),{'get'});self.assertEqual(path['get']['responses']['200']['content']['application/json']['schema']['$ref'],'#/components/schemas/Envelope')


if __name__=='__main__':unittest.main()
