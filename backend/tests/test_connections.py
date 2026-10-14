import copy,unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from uuid import UUID,uuid4
from test_departure import DepartureApiTests,DepartureCalculationTests
from test_journeys import route
from app.journeys.provider import normalize
from app.arrivals import service as arrivals,provider,cache
from app.guidance import service
from app.guidance.connections import evaluate,following_arrivals
from app.common.database import database


def transfer_route(count=1):
    data=route(seconds=5000,transfers=count)
    transit=copy.deepcopy(data['steps'][1]);walk=copy.deepcopy(data['steps'][0]);tail=data['steps'][-1]
    data['steps']=data['steps'][:-1]
    for _ in range(count):data['steps'] += [copy.deepcopy(walk),copy.deepcopy(transit)]
    data['steps'].append(tail)
    return data

calculation_fixture=DepartureCalculationTests.fixture

class ConnectionUnitTests(unittest.TestCase):
    def fixture(self,count=1):
        raw=transfer_route(count);candidates,_=normalize({'status':'OK','routes':[raw]},'balanced')
        candidate=candidates[0];at,e,p=calculation_fixture(self);p['transfer_buffer']=120
        departure=service.calculate(e,300,300,p,at)
        return at,candidate,departure,p

    def evidence(self,at,leg,seconds):
        from test_first_arrivals import mapping
        return arrivals.normalize(mapping(UUID(leg['leg_id'])),[('123',seconds)],at,at,uuid4(),uuid4(),at+timedelta(seconds=300))

    def test_minimum_boundary_selects_supplied_next_vehicle(self):
        at,route,dep,p=self.fixture();minimum=780+500+100+120
        result=evaluate(route,dep,p,at,lambda leg:self.evidence(at,leg,minimum))
        check=result.transfers[0]
        self.assertEqual(check.minimum_boarding_at,at+timedelta(seconds=minimum))
        self.assertEqual(check.next_boarding_at,check.minimum_boarding_at)
        self.assertEqual(check.feasibility,'estimated_feasible');self.assertEqual(check.time_source,'receipt_estimate')
        self.assertEqual(result.estimated_final_alighting_at,at+timedelta(seconds=minimum+500))

    def test_early_current_candidates_are_unavailable_without_invented_timetable(self):
        at,route,dep,p=self.fixture();value=evaluate(route,dep,p,at,lambda leg:self.evidence(at,leg,1499))
        self.assertEqual(value.connection_status,'unavailable');self.assertIsNone(value.estimated_final_alighting_at)
        self.assertIsNone(value.transfers[0].next_boarding_at)
        self.assertEqual(value.transfers[0].reasons,['NO_SUPPLIED_VEHICLE_AFTER_MINIMUM'])

    def test_sequential_second_transfer_uses_selected_first_transfer_time(self):
        at,route,dep,p=self.fixture(2);times=iter([2000,3000])
        result=evaluate(route,dep,p,at,lambda leg:self.evidence(at,leg,next(times)))
        self.assertEqual(result.transfers[1].estimated_alighting_at,at+timedelta(seconds=2500))
        self.assertEqual(result.transfers[1].minimum_boarding_at,at+timedelta(seconds=2720))
        self.assertEqual(result.estimated_final_alighting_at,at+timedelta(seconds=3500))

    def test_failed_link_stops_later_upstream_and_times(self):
        at,route,dep,p=self.fixture(2)
        calls=[]
        def fetch(leg):calls.append(leg);return self.evidence(at,leg,1000)
        result=evaluate(route,dep,p,at,fetch)
        self.assertEqual(len(calls),1);self.assertEqual(result.connection_status,'unavailable')
        self.assertIsNone(result.transfers[1].estimated_alighting_at);self.assertEqual(result.transfers[1].feasibility,'unknown')

    def test_missing_zero_or_unsupported_transfer_never_fetches(self):
        for kind in ('missing','zero','subway','ride_zero'):
            at,route,dep,p=self.fixture()
            if kind=='missing':route['connections'][0]['walking_seconds']=None
            if kind=='zero':route['connections'][0]['walking_seconds']=0
            if kind=='subway':route['ordered_legs'][3]['type']='SUBWAY'
            if kind=='ride_zero':route['ordered_legs'][1]['seconds']=0
            with patch('app.arrivals.provider.fetch') as fetch:
                result=evaluate(route,dep,p,at,fetch)
                fetch.assert_not_called()
            self.assertEqual(result.connection_status,'unknown');self.assertIsNone(result.transfers[0].next_boarding_at)

    def test_missing_first_vehicle_does_not_query_future_legs(self):
        at,route,dep,p=self.fixture();dep.valid_for_guidance=False
        with patch('app.arrivals.provider.fetch') as fetch:result=evaluate(route,dep,p,at,fetch);fetch.assert_not_called()
        self.assertEqual(result.connection_status,'unknown');self.assertIsNone(result.transfers[0].minimum_boarding_at)

    def test_personal_factor_only_applies_once_to_transfer_walk(self):
        at,route,dep,p=self.fixture();p['factor']=1.1;route['connections'][0]['walking_seconds']=101
        value=evaluate(route,dep,p,at,lambda leg:self.evidence(at,leg,2000))
        self.assertEqual(value.transfers[0].transfer_walk_seconds,112)
        self.assertEqual(value.transfers[0].transfer_buffer_seconds,120)

    def test_following_contexts_are_bound_and_not_persisted_in_candidates(self):
        contexts={};candidates,_=normalize({'status':'OK','routes':[transfer_route(2)]},'balanced',mapping_contexts=contexts)
        context=contexts[candidates[0]['candidate_id']]
        self.assertEqual(len(context['following']),2)
        import json
        self.assertNotIn('following',json.dumps(candidates));self.assertNotIn('points',json.dumps(candidates))

    def test_stale_leg_and_no_transfer_route_are_distinct(self):
        at,route,dep,p=self.fixture()
        def expired(leg):
            value=self.evidence(at,leg,2000);value.expires_at=at-timedelta(seconds=1);value.valid_for_guidance=False;return value
        result=evaluate(route,dep,p,at,expired);self.assertEqual(result.connection_status,'unknown')
        at,route,dep,p=self.fixture(0)
        with patch('app.arrivals.provider.fetch') as fetch:result=evaluate(route,dep,p,at,fetch);fetch.assert_not_called()
        self.assertEqual(result.connection_status,'estimated_feasible');self.assertEqual(result.transfers,[])

class ConnectionApiTests(unittest.IsolatedAsyncioTestCase):
    setUp=DepartureApiTests.setUp
    tearDown=DepartureApiTests.tearDown
    call=DepartureApiTests.call
    prepare=DepartureApiTests.prepare
    credentials=DepartureApiTests.credentials
    signup_login=DepartureApiTests.signup_login
    saved=DepartureApiTests.saved
    create=DepartureApiTests.create
    search=DepartureApiTests.search
    completed=DepartureApiTests.completed
    evidence_path=DepartureApiTests.evidence_path

    async def setup_transfer(self,count=1):
        await self.signup_login();path,identifier=await self.evidence_path(data={'status':'OK','routes':[transfer_route(count)]})
        from test_api_contract import request
        self.path='/api/v1'+path.replace('walking-evidence','first-departure')
        self.request=request;self.search_id=UUID(identifier)
        with database() as c:row=c.execute('SELECT * FROM journey_searches WHERE id=%s',(self.search_id,)).fetchone()
        self.owner=row['user_id'];self.candidate_id=UUID(row['candidates'][0]['candidate_id'])
        _,route,first,_=arrivals.owned(self.owner,self.search_id,self.candidate_id);self.first_id=first['leg_id']
        from test_first_arrivals import mapping
        def resolve(context,expires_at,**kwargs):
            value=mapping(UUID(context['first_leg_id']));value.valid_until=expires_at;return value
        return patch.object(arrivals.public_mapping,'resolve',side_effect=resolve)

    async def get(self):
        return await self.request(self.path,query=b'include_connections=true',headers=[(b'cookie',self.cookie.encode())])

    async def test_owned_two_transfers_use_leg_cache_without_db_route_writes(self):
        guard=await self.setup_transfer(2)
        with database() as c:before=c.execute('SELECT * FROM journey_searches WHERE id=%s',(self.search_id,)).fetchone()
        times=iter([780,2000,3000])
        with guard,patch.object(provider,'fetch',side_effect=lambda m:[('123',next(times))]) as fetch:
            one=await self.get();two=await self.get()
        self.assertEqual((one[0],two[0],fetch.call_count),(200,200,3))
        self.assertEqual(one[2]['data']['connection_status'],'estimated_feasible')
        self.assertEqual(len(one[2]['data']['transfers']),2)
        with database() as c:self.assertEqual(before,c.execute('SELECT * FROM journey_searches WHERE id=%s',(self.search_id,)).fetchone())

    async def test_provider_failure_keeps_original_child_receipt_and_expiry(self):
        guard=await self.setup_transfer()
        with guard,patch.object(provider,'fetch',side_effect=[ [('123',780)],[('123',2000)] ]):one=await self.get()
        _,_,_,fp=arrivals.owned(self.owner,self.search_id,self.candidate_id)
        root=cache.lookup(self.owner,self.search_id,self.candidate_id,fp,arrivals.now());child=next(iter(root.following.values()))
        original=child.evidence.model_dump();child.attempted_at-=timedelta(seconds=61)
        from app.common.errors import AuthError
        with patch.object(provider,'fetch',side_effect=AuthError(504,'PROVIDER_TIMEOUT','safe')):failed=await self.get()
        self.assertEqual(failed[0],504);self.assertEqual(child.evidence.model_dump(),original)

    async def test_changed_transfer_buffer_during_next_leg_lookup_blocks_result(self):
        guard=await self.setup_transfer()
        def fetch(mapping):
            if str(mapping.first_leg_id)!=self.first_id:
                with database() as c:c.execute('UPDATE user_profiles SET transfer_buffer_seconds=0,version=version+1 WHERE user_id=%s',(self.owner,))
                return [('123',2000)]
            return [('123',780)]
        with guard,patch.object(provider,'fetch',side_effect=fetch):result=await self.get()
        self.assertEqual(result[0],409)

    async def test_restart_missing_following_context_is_unknown_and_does_not_fetch(self):
        await self.setup_transfer();cache.clear()
        with patch.object(provider,'fetch') as fetch:result=await self.get();fetch.assert_not_called()
        self.assertEqual(result[0],200);self.assertEqual(result[2]['data']['connection_status'],'unknown')

    async def test_deadline_stops_child_before_network(self):
        await self.setup_transfer();_,route,_,snapshot=arrivals.owned(self.owner,self.search_id,self.candidate_id)
        leg=[l for l in route['ordered_legs'] if l['type']!='WALKING'][1]
        import time
        with patch.object(provider,'fetch') as fetch,patch.object(arrivals.public_mapping,'resolve') as resolve:
            result=following_arrivals(self.owner,self.search_id,self.candidate_id,leg,snapshot,time.monotonic()+1)
            fetch.assert_not_called();resolve.assert_not_called()
        self.assertEqual(result.reasons,['CONNECTION_TIME_LIMIT'])

del DepartureApiTests,DepartureCalculationTests
if __name__=='__main__':unittest.main()
