import copy,json,unittest,urllib.error
from datetime import datetime,timedelta,timezone
from unittest.mock import patch,MagicMock
from uuid import uuid4
import test_first_arrivals as previous
import test_walking as walking
from app.arrivals import cache,mapping,provider,service
from app.common.database import database
from app.common.errors import AuthError
from app.journeys import provider as journeys
REAL_RESOLVE=mapping.resolve


def context(leg=None):
    return {'first_leg_id':str(leg or uuid4()),'stops':[{'name':'합성 승차'},{'name':'합성 하차'}],
            'points':[[127.0276,37.4979],[126.9726,37.5547]],'vehicle':'합성 10'}


def query_fixture(kind,params,deadline):
    if kind=='stations':return [{'stationId':'10','stationName':'합성 승차','x':127.0276,'y':37.4979}]
    if kind=='via':return [{'routeId':'99','routeName':'합성 10','staOrder':1,'routeDestId':'30'}]
    if kind=='stops':return [{'stationId':sid,'stationName':name,'stationSeq':i+1,'turnSeq':3,
                             'turnYn':'Y' if i==2 else 'N','x':126.9726 if i==1 else 127.0276,
                             'y':37.5547 if i==1 else 37.4979}
                            for i,(sid,name) in enumerate(zip(['10','20','30','40','50'],
                                  ['합성 승차','합성 하차','회차','복귀','끝']))]
    if kind=='info':return [{'routeId':'99','startStationId':'10','endStationId':'30','turnStID':'30'}]
    raise AssertionError(kind)


class MappingUnitTests(unittest.TestCase):
    def setUp(self):cache.clear();self.addCleanup(cache.clear)

    def test_diagnostic_counts_and_reason_never_include_public_identity(self):
        trace={}
        def fake(kind,params,deadline):
            return [] if kind=='via' else query_fixture(kind,params,deadline)
        with patch.object(mapping,'query',side_effect=fake):
            self.assertIsNone(mapping.resolve(context(),datetime.now(timezone.utc)+timedelta(seconds=200),diagnostics=trace))
        self.assertEqual(trace,{'stage':'station_routes','reason':'NO_ROUTE_AT_BOARDING_STOP','station_count':1,'route_count':0})
        with patch.object(mapping,'query',side_effect=query_fixture):
            self.assertIsNotNone(mapping.resolve(context(),datetime.now(timezone.utc)+timedelta(seconds=200),diagnostics=trace))
        self.assertEqual(trace['reason'],'MAPPING_CONFIRMED')
        self.assertEqual(set(trace),{'stage','reason','station_count','route_count','matched_count'})

    def test_strict_mapping_uses_public_direction_not_return_endpoint_alias(self):
        at=datetime.now(timezone.utc)+timedelta(seconds=200)
        with patch.object(mapping,'query',side_effect=query_fixture) as q:
            value=mapping.resolve(context(),at)
        self.assertEqual(q.call_count,4);self.assertEqual(value.route_dest_id,'30')
        self.assertEqual(value.valid_until,at);self.assertIn('30m.ordered',value.mapping_version)

    def test_extra_public_stops_allowed_and_endpoints_within_thirty_meters(self):
        for mode in ['gap','far']:
            def fake(kind,params,deadline):
                rows=query_fixture(kind,params,deadline)
                if kind=='stops':
                    if mode=='gap':
                        rows.insert(1,dict(rows[0],stationId='77',stationName='추가'))
                        for i,row in enumerate(rows):row['stationSeq']=i+1;row['turnSeq']=4
                    else:rows[0]['x']+=0.0004
                return rows
            with patch.object(mapping,'query',side_effect=fake):
                value=mapping.resolve(context(),datetime.now(timezone.utc)+timedelta(seconds=200))
            self.assertEqual(value is not None,mode=='gap')

    def test_ambiguous_route_budget_and_direction_conflict_are_not_selected(self):
        def fake(kind,params,deadline):
            if kind=='via':return [dict(query_fixture(kind,params,deadline)[0],routeId=str(i)) for i in (1,2,3)]
            return query_fixture(kind,params,deadline)
        with patch.object(mapping,'query',side_effect=fake) as q:
            self.assertIsNone(mapping.resolve(context(),datetime.now(timezone.utc)+timedelta(seconds=200)))
            self.assertEqual(q.call_count,2)
        def conflict(kind,params,deadline):
            rows=query_fixture(kind,params,deadline)
            if kind=='via':rows[0]['routeDestId']='999'
            return rows
        with patch.object(mapping,'query',side_effect=conflict):self.assertIsNone(mapping.resolve(context(),datetime.now(timezone.utc)+timedelta(seconds=200)))

    def test_fixed_https_transport_size_duplicate_json_timeout_and_safe_errors(self):
        response=MagicMock();response.__enter__.return_value=response
        opener=MagicMock();opener.open.return_value=response
        valid=json.dumps({'response':{'msgHeader':{'resultCode':4}}}).encode()
        with patch.object(mapping,'dotenv_values',return_value={'DATA_GO_KR_SERVICE_KEY':'private'}),patch.dict(mapping.os.environ,{},clear=True),patch.object(mapping.urllib.request,'build_opener',return_value=opener):
            response.read.return_value=valid
            self.assertEqual(mapping.query('stations',{'keyword':'공개'},mapping.time.monotonic()+5),[])
            request=opener.open.call_args.args[0];self.assertTrue(request.startswith('https://apis.data.go.kr/6410000/busstationservice/v2/'))
            for raw in [b'x'*1048577,b'{"response":{},"response":{}}',b'{"response":NaN}']:
                response.read.return_value=raw
                with self.assertRaises(AuthError) as e:mapping.query('stations',{},mapping.time.monotonic()+5)
                self.assertEqual(e.exception.status,502)
            opener.open.side_effect=urllib.error.URLError(TimeoutError('private-url'))
            with self.assertRaises(AuthError) as e:mapping.query('stations',{},mapping.time.monotonic()+5)
            self.assertEqual(e.exception.status,504);self.assertNotIn('private',e.exception.message)

    def test_expired_deadline_and_missing_key_do_not_send(self):
        with patch.object(mapping.urllib.request,'build_opener') as open,patch.object(mapping,'dotenv_values',return_value={}),patch.dict(mapping.os.environ,{},clear=True):
            with self.assertRaises(AuthError) as e:mapping.query('stations',{},mapping.time.monotonic()-1)
            self.assertEqual(e.exception.status,504)
            with self.assertRaises(AuthError) as e:mapping.query('stations',{},mapping.time.monotonic()+5)
            self.assertEqual(e.exception.status,503);open.assert_not_called()

    def test_normalizer_context_contains_only_first_bus_endpoints_not_device_walk(self):
        data={'status':'OK','routes':[walking.route()]};contexts={}
        candidates,_=journeys.normalize(data,'balanced',mapping_contexts=contexts)
        first=next(l for l in candidates[0]['ordered_legs'] if l['type']=='BUS')
        value=contexts[candidates[0]['candidate_id']]
        self.assertEqual(value['first_leg_id'],first['leg_id']);self.assertEqual(len(value['points']),2)
        self.assertNotIn('points',json.dumps(candidates))
        self.assertNotIn('origin',value);self.assertNotIn('destination',value)
        subway={'status':'OK','routes':[walking.route(kind='SUBWAY')]}
        journeys.normalize(subway,'balanced',mapping_contexts=contexts);self.assertEqual(contexts,{})
        multiple={'status':'OK','routes':[walking.route()]};multiple['routes'][0]['steps'][1]['properties']['vehicles'].append({'name':'다른'})
        journeys.normalize(multiple,'balanced',mapping_contexts=contexts);self.assertEqual(contexts,{})

    def test_cache_owner_fingerprint_ttl_and_capacity_are_bound(self):
        at=datetime.now(timezone.utc);owner=uuid4();ids=[]
        candidate={'candidate_id':str(uuid4())};contexts={candidate['candidate_id']:context()}
        for i in range(33):
            identifier=uuid4();ids.append(identifier)
            cache.publish(owner,identifier,[candidate],contexts,at+timedelta(seconds=200))
        fp=cache.fingerprint(candidate)
        self.assertIsNone(cache.lookup(owner,ids[0],candidate['candidate_id'],fp,at))
        self.assertIsNotNone(cache.lookup(owner,ids[-1],candidate['candidate_id'],fp,at))
        self.assertIsNone(cache.lookup(uuid4(),ids[-1],candidate['candidate_id'],fp,at))
        self.assertIsNone(cache.lookup(owner,ids[-1],candidate['candidate_id'],'changed',at))
        self.assertIsNone(cache.lookup(owner,ids[-1],candidate['candidate_id'],fp,at+timedelta(seconds=200)))


class ConnectedArrivalTests(unittest.IsolatedAsyncioTestCase):
    setUp=previous.ArrivalApiTests.setUp
    tearDown=previous.ArrivalApiTests.tearDown
    setup_route=previous.ArrivalApiTests.setup_route
    call=previous.ArrivalApiTests.call
    prepare=previous.ArrivalApiTests.prepare
    credentials=previous.ArrivalApiTests.credentials
    signup_login=previous.ArrivalApiTests.signup_login
    saved=previous.ArrivalApiTests.saved
    create=previous.ArrivalApiTests.create
    search=previous.ArrivalApiTests.search
    completed=previous.ArrivalApiTests.completed
    evidence_path=previous.ArrivalApiTests.evidence_path

    def entry(self):
        _,_,_,fp=service.owned(self.owner,self.search_id,self.candidate_id)
        return cache.lookup(self.owner,self.search_id,self.candidate_id,fp,service.now())

    async def test_public_get_resolves_then_reuses_receipt_without_db_writes(self):
        await self.setup_route();self.assertIsNotNone(self.entry())
        with database() as c:before=c.execute('SELECT * FROM journey_searches WHERE id=%s',(self.search_id,)).fetchone()
        with patch.object(service.public_mapping,'resolve',return_value=self.mapping) as resolve,patch.object(provider,'fetch',return_value=[('123',300)]) as fetch:
            one=await self.call(self.path);two=await self.call(self.path)
        self.assertEqual((one[0],two[0],resolve.call_count,fetch.call_count),(200,200,1,1))
        self.assertEqual(one[2]['data']['received_at'],two[2]['data']['received_at']);self.assertEqual(one[2]['data']['expires_at'],two[2]['data']['expires_at']);self.assertEqual(one[2]['data']['status'],'estimated')
        self.assertTrue(one[2]['data']['valid_for_guidance']);self.assertEqual(one[2]['data']['timing_basis'],'receipt_estimate');self.assertIsNotNone(one[2]['data']['candidates'][0]['predicted_arrival_at'])
        with database() as c:after=c.execute('SELECT * FROM journey_searches WHERE id=%s',(self.search_id,)).fetchone()
        self.assertEqual(before,after)
        for private in ['200000177','latitude','points','serviceKey']:self.assertNotIn(private,json.dumps(one[2]))

    async def test_full_resolver_connection_with_synthetic_public_sources(self):
        await self.setup_route()
        actual_resolve=REAL_RESOLVE
        def extra_stops(kind,params,deadline):
            rows=query_fixture(kind,params,deadline)
            if kind=='stops':
                rows.insert(1,dict(rows[0],stationId='77',stationName='추가'))
                rows.insert(5,dict(rows[2]))
                for i,row in enumerate(rows):row['stationSeq']=i+1;row['turnSeq']=4
            return rows
        with patch.object(service.public_mapping,'resolve',side_effect=actual_resolve),patch.object(mapping,'query',side_effect=extra_stops) as q,patch.object(provider,'fetch',return_value=[('123',300)]) as fetch:
            response=await self.call(self.path)
        self.assertEqual(response[0],200);self.assertEqual(q.call_count,4);self.assertEqual(fetch.call_count,1)
        self.assertEqual(response[2]['data']['source_status'],'unknown')

    async def test_restart_or_changed_snapshot_never_fetches(self):
        await self.setup_route();entry=self.entry();cache.clear()
        with patch.object(provider,'fetch') as fetch:self.assertEqual((await self.call(self.path))[2]['data']['status'],'mapping_required');fetch.assert_not_called()
        with database() as c:stored=c.execute('SELECT * FROM journey_searches WHERE id=%s',(self.search_id,)).fetchone()
        cache.publish(self.owner,self.search_id,stored['candidates'],{str(self.candidate_id):entry.context},stored['expires_at'])
        from psycopg.types.json import Jsonb
        with database() as c:
            row=c.execute('SELECT candidates FROM journey_searches WHERE id=%s',(self.search_id,)).fetchone();values=row['candidates'];values[0]['missing_segments'].append('SYNTHETIC_CHANGED')
            c.execute('UPDATE journey_searches SET candidates=%s WHERE id=%s',(Jsonb(values),self.search_id))
        with patch.object(provider,'fetch') as fetch:self.assertEqual((await self.call(self.path))[2]['data']['status'],'mapping_required');fetch.assert_not_called()

    async def test_lock_contention_and_refresh_quota_prevent_network(self):
        await self.setup_route();entry=self.entry();entry.lock.acquire()
        try:
            with patch.object(provider,'fetch') as fetch:self.assertEqual((await self.call(self.path))[0],429);fetch.assert_not_called()
        finally:entry.lock.release()
        with database() as c:frozen=service.security.repository.clock_now(c)
        with patch.object(service.security.repository,'clock_now',return_value=frozen),patch.object(service.public_mapping,'resolve',return_value=None) as resolve:
            for i in range(10):
                entry.evidence=None
                self.assertEqual((await self.call(self.path))[0],200)
            entry.evidence=None;self.assertEqual((await self.call(self.path))[0],429)
            self.assertEqual(resolve.call_count,10)

    async def test_refresh_reuses_mapping_but_not_old_receipt(self):
        await self.setup_route()
        with patch.object(service.public_mapping,'resolve',return_value=self.mapping) as resolve,patch.object(provider,'fetch',return_value=[('123',300)]) as fetch:
            one=await self.call(self.path);entry=self.entry();entry.attempted_at-=timedelta(seconds=61)
            two=await self.call(self.path)
        self.assertEqual((resolve.call_count,fetch.call_count),(1,2));self.assertNotEqual(one[2]['data']['received_at'],two[2]['data']['received_at'])
        self.assertEqual(entry.mapping.valid_until,self.mapping.valid_until)

    async def test_candidate_changes_during_mapping_block_before_arrival_fetch(self):
        await self.setup_route()
        def changed(*args):
            from psycopg.types.json import Jsonb
            with database() as c:
                row=c.execute('SELECT candidates FROM journey_searches WHERE id=%s',(self.search_id,)).fetchone()
                values=row['candidates'];values[0]['missing_segments'].append('SYNTHETIC_CHANGED')
                c.execute('UPDATE journey_searches SET candidates=%s WHERE id=%s',(Jsonb(values),self.search_id))
            return self.mapping
        with patch.object(service.public_mapping,'resolve',side_effect=changed),patch.object(provider,'fetch') as fetch:
            response=await self.call(self.path)
        self.assertEqual(response[0],409);fetch.assert_not_called()

    async def test_search_expires_during_mapping_and_cached_result_cannot_bypass_expiry(self):
        await self.setup_route()
        def expire(*args):
            with database() as c:c.execute("UPDATE journey_searches SET expires_at=clock_timestamp()-interval '1 second' WHERE id=%s",(self.search_id,))
            return self.mapping
        with patch.object(service.public_mapping,'resolve',side_effect=expire),patch.object(provider,'fetch') as fetch:
            self.assertEqual((await self.call(self.path))[0],404);fetch.assert_not_called()

    async def test_cached_receipt_cannot_outlive_shortened_search(self):
        await self.setup_route()
        with patch.object(service.public_mapping,'resolve',return_value=self.mapping),patch.object(provider,'fetch',return_value=[('123',300)]) as fetch:
            one=await self.call(self.path)
            shortened=service.now()+timedelta(seconds=30)
            with database() as c:c.execute('UPDATE journey_searches SET expires_at=%s WHERE id=%s',(shortened,self.search_id))
            two=await self.call(self.path)
        self.assertEqual(fetch.call_count,1)
        self.assertEqual(two[2]['data']['received_at'],one[2]['data']['received_at'])
        from datetime import datetime
        self.assertEqual(datetime.fromisoformat(two[2]['data']['expires_at'].replace('Z','+00:00')),shortened)

    async def test_missing_mapping_result_is_throttled_without_arrival_call(self):
        await self.setup_route()
        with patch.object(service.public_mapping,'resolve',return_value=None) as resolve,patch.object(provider,'fetch') as fetch:
            self.assertEqual((await self.call(self.path))[2]['data']['status'],'mapping_required')
            self.assertEqual((await self.call(self.path))[0],200)
            self.assertEqual(resolve.call_count,1);fetch.assert_not_called()


if __name__=='__main__':unittest.main()
