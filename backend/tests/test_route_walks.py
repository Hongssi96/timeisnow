"""Routine gap recovery through authenticated ASGI and isolated real PostgreSQL."""
import copy,json,time,unittest
from datetime import timedelta
from unittest.mock import patch
from uuid import UUID

from test_routine_departure import RoutineDepartureTests as Base
from test_journeys import route
from test_arrival_mapping_connection import query_fixture
from app.arrivals import cache,mapping,provider,service as arrivals
from app.guidance import route_walks,walk_provider,routine
from app.common.database import database
from app.common.errors import AuthError
from test_api_contract import request
base_call=Base.call


class RouteWalkTests(unittest.IsolatedAsyncioTestCase):
    setUp=Base.setUp;tearDown=Base.tearDown
    prepare=Base.prepare;credentials=Base.credentials;signup_login=Base.signup_login
    saved=Base.saved;create=Base.create;search=Base.search;completed=Base.completed
    routine_body=Base.routine_body;save=Base.save;refresh=Base.refresh;path=Base.path

    async def call(self,path,body=None,**options):
        if '/first-departure?' in path and body is None:
            pathname,query=path.split('?',1)
            return await request('/api/v1'+pathname,query=query.encode(),headers=[(b'cookie',self.cookie.encode())],timeout=25)
        return await base_call(self,path,body,**options)

    async def ready(self,provided=False,count=1):
        await self.signup_login()
        _,home=await self.saved('집');_,work=await self.saved('회사')
        raw=route(seconds=6000,transfers=count,walking=200)
        bus=copy.deepcopy(raw['steps'][1])
        raw['steps']=raw['steps'][:2]+sum([([copy.deepcopy(raw['steps'][0])] if provided else [])+[copy.deepcopy(bus)] for _ in range(count)],[])
        if provided:raw['steps'].append(copy.deepcopy(raw['steps'][0]))
        body={'origin':{'type':'saved_place','place_id':home[2]['data']['place_id'],'location_version':1},
              'destination':{'type':'saved_place','place_id':work[2]['data']['place_id'],'location_version':1},
              'timing':{'mode':'depart_now','timezone':'Asia/Seoul'}}
        accepted,result,_=await self.completed(body,data={'status':'OK','routes':[raw]})
        created=await self.save(self.routine_body(home[2]['data'],work[2]['data'],accepted[2]['data']['search_id'],result[2]['data']['candidates'][0]))
        self.rid=created[2]['data']['routine_id']
        with database() as c:c.execute("UPDATE routines SET target_arrival_local_time='23:59',version=2 WHERE id=%s",(self.rid,))
        self.accepted,_=await self.refresh(version=2,data={'status':'OK','routes':[raw]})
        self.sid=self.accepted[2]['data']['search_id']

    async def guidance(self,walk=90,arrival_seconds=2400):
        def arrival(value):
            ids=[l['leg_id'] for l in self.candidate['ordered_legs'] if l['type']=='BUS'];index=ids.index(str(value.first_leg_id))
            seconds=780 if index==0 else arrival_seconds[index-1] if isinstance(arrival_seconds,tuple) else arrival_seconds
            return [('123',seconds)]
        with patch.object(mapping,'query',side_effect=query_fixture),patch.object(provider,'fetch',side_effect=arrival),patch.object(walk_provider,'fetch',return_value=walk) as fetch:
            response=await self.call(self.path(self.accepted,2))
        return response,fetch.call_count

    async def setup_route(self,provided=False,count=1):
        await self.ready(provided,count)
        result=await self.call('/journey-searches/'+self.sid)
        self.candidate=result[2]['data']['candidates'][0]
        self.first_id=next(l['leg_id'] for l in self.candidate['ordered_legs'] if l['type']=='BUS')

    async def test_missing_transfer_and_egress_recover_goal_without_mutating_candidate(self):
        await self.setup_route();before=copy.deepcopy(self.candidate)
        result,count=await self.guidance();self.assertEqual(result[0],200);self.assertEqual(count,2)
        d=result[2]['data']['departure'];self.assertTrue(d['valid_for_guidance'])
        self.assertEqual([w['role'] for w in d['supplemental_walks']],['transfer','egress'])
        self.assertEqual(d['transfers'][0]['transfer_walk_seconds'],90)
        self.assertEqual(d['connection_status'],'estimated_feasible')
        self.assertIn(d['target_evaluation']['status'],('estimated_meets','estimated_late'))
        self.assertEqual(d['target_evaluation']['egress_seconds'],90)
        self.assertIn('SUPPLEMENTAL_EGRESS_WALK',d['target_evaluation']['reasons'])
        after=(await self.call('/journey-searches/'+self.sid))[2]['data']['candidates'][0]
        self.assertEqual(before,after)
        for private in ('latitude','longitude','mapping_identity','alighting_point','station_id'):
            self.assertNotIn(private,json.dumps(result[2]))

    async def test_two_transfers_recover_exactly_three_walks_and_full_timeline(self):
        await self.setup_route(count=2);result,count=await self.guidance(arrival_seconds=(2400,3600))
        self.assertEqual(result[0],200);self.assertEqual(count,3)
        d=result[2]['data']['departure'];self.assertEqual(len(d['supplemental_walks']),3)
        self.assertEqual(d['connection_status'],'estimated_feasible')
        self.assertIn(d['target_evaluation']['status'],('estimated_meets','estimated_late'))

    async def test_following_provider_failure_does_not_remove_first_departure(self):
        await self.setup_route()
        def failed(value):
            if str(value.first_leg_id)!=self.first_id:raise AuthError(503,'PROVIDER_UNAVAILABLE','private')
            return [('123',780)]
        with patch.object(mapping,'query',side_effect=query_fixture),patch.object(provider,'fetch',side_effect=failed) as fetch,patch.object(walk_provider,'fetch',return_value=90):
            one=await self.call(self.path(self.accepted,2));two=await self.call(self.path(self.accepted,2))
        self.assertEqual((one[0],two[0],fetch.call_count),(200,200,2))
        self.assertTrue(one[2]['data']['departure']['valid_for_guidance'])
        self.assertEqual(one[2]['data']['departure']['transfers'][0]['reasons'],['TRANSFER_ARRIVAL_UNAVAILABLE'])

    async def test_cached_seconds_reapply_profile_once_and_preserve_original_times(self):
        await self.setup_route();one,_=await self.guidance(walk=100)
        original=one[2]['data']['departure']['supplemental_walks']
        with database() as c:c.execute('UPDATE user_profiles SET walking_duration_factor=1.1,version=version+1')
        two,count=await self.guidance(walk=999);self.assertEqual(count,0)
        values=two[2]['data']['departure']['supplemental_walks']
        self.assertTrue(all(w['provider_seconds']==100 and w['walking_seconds']==110 for w in values))
        self.assertEqual([w['fetched_at'] for w in values],[w['fetched_at'] for w in original])
        self.assertEqual([w['valid_until'] for w in values],[w['valid_until'] for w in original])

    async def test_provided_positive_walks_never_request_replacement(self):
        await self.setup_route(provided=True);result,count=await self.guidance()
        self.assertEqual(result[0],200);self.assertEqual(count,0)
        self.assertEqual(result[2]['data']['departure']['supplemental_walks'],[])

    async def test_no_walk_result_stays_unknown_and_failure_is_cached(self):
        await self.setup_route();one,count=await self.guidance(walk=None);self.assertEqual(count,2)
        self.assertTrue(one[2]['data']['departure']['valid_for_guidance'])
        self.assertEqual(one[2]['data']['departure']['supplemental_walks'],[])
        self.assertEqual(one[2]['data']['departure']['target_evaluation']['status'],'unknown')
        two,count=await self.guidance();self.assertEqual(count,0)
        self.assertEqual(two[2]['data']['departure']['supplemental_walks'],[])

    async def test_supplied_transfer_vehicles_too_early_do_not_create_timetable(self):
        await self.setup_route();result,_=await self.guidance(arrival_seconds=30)
        d=result[2]['data']['departure'];self.assertEqual(d['connection_status'],'unavailable')
        self.assertEqual(d['transfers'][0]['reasons'],['NO_SUPPLIED_VEHICLE_AFTER_MINIMUM'])
        self.assertIsNone(d['target_evaluation']['estimated_destination_arrival_at'])

    async def test_destination_changed_during_walk_blocks_result(self):
        await self.setup_route();calls=0
        def changed(*args):
            nonlocal calls
            calls+=1
            if calls==2:
                with database() as c:c.execute('UPDATE saved_places SET location_version=location_version+1 WHERE id=(SELECT destination_place_id FROM routines WHERE id=%s)',(self.rid,))
            return 90
        with patch.object(mapping,'query',side_effect=query_fixture),patch.object(provider,'fetch',return_value=[('123',780)]),patch.object(walk_provider,'fetch',side_effect=changed):
            result=await self.call(self.path(self.accepted,2))
        self.assertEqual(result[0],409)

    async def test_mapping_failure_and_deadline_do_not_fill_walk_with_defaults(self):
        await self.setup_route()
        with patch.object(mapping,'resolve',return_value=None),patch.object(walk_provider,'fetch') as fetch:
            result=await self.call(self.path(self.accepted,2))
        self.assertEqual(result[2]['data']['departure']['supplemental_walks'],[]);fetch.assert_not_called()

    async def test_walk_timeout_retains_first_departure_and_suppresses_retry(self):
        await self.setup_route()
        with patch.object(mapping,'query',side_effect=query_fixture),patch.object(provider,'fetch',return_value=[('123',780)]),patch.object(walk_provider,'fetch',side_effect=AuthError(504,'PROVIDER_TIMEOUT','private')) as fetch:
            one=await self.call(self.path(self.accepted,2));two=await self.call(self.path(self.accepted,2))
        self.assertEqual(fetch.call_count,2)
        self.assertEqual((one[0],two[0]),(200,200))
        self.assertTrue(one[2]['data']['departure']['valid_for_guidance'])
        self.assertIn('TRANSFER_WALK_TIME_LIMIT',one[2]['data']['departure']['reasons'])

    async def test_same_official_stop_skips_walk_but_keeps_transfer_buffer(self):
        await self.setup_route();resolve=mapping.resolve
        def same_stop(context,expires_at,**kwargs):
            value=resolve(context,expires_at,**kwargs);sink=kwargs.get('boarding_endpoint')
            if sink and context['first_leg_id']==self.first_id:
                sink['alighting_station_id']=sink['station_id'];sink['alighting_point']=sink['point']
            return value
        with patch.object(mapping,'resolve',side_effect=same_stop):result,count=await self.guidance()
        self.assertEqual(count,1)
        d=result[2]['data']['departure'];walk=d['supplemental_walks'][0]
        self.assertEqual((walk['source'],walk['walking_seconds']),('same_stop',0))
        check=d['transfers'][0];self.assertEqual(check['transfer_walk_seconds'],0)
        self.assertEqual(check['transfer_buffer_seconds'],120)
        self.assertEqual(check['feasibility'],'estimated_feasible')

    async def test_same_coordinates_with_different_stop_id_do_not_prove_zero_walk(self):
        await self.setup_route();resolve=mapping.resolve
        def same_coordinates(context,expires_at,**kwargs):
            value=resolve(context,expires_at,**kwargs);sink=kwargs.get('boarding_endpoint')
            if sink and context['first_leg_id']==self.first_id:sink['alighting_point']=sink['point']
            return value
        with patch.object(mapping,'resolve',side_effect=same_coordinates):result,count=await self.guidance(walk=None)
        self.assertEqual(count,2);self.assertEqual(result[2]['data']['departure']['supplemental_walks'],[])

    async def test_profile_changes_during_extra_walk_block_old_factor(self):
        await self.setup_route()
        def changed(*args):
            with database() as c:c.execute('UPDATE user_profiles SET version=version+1')
            return 90
        with patch.object(mapping,'query',side_effect=query_fixture),patch.object(provider,'fetch',return_value=[('123',780)]),patch.object(walk_provider,'fetch',side_effect=changed):
            result=await self.call(self.path(self.accepted,2))
        self.assertEqual(result[0],409)

    async def test_deadline_and_duplicate_lock_send_no_external_request(self):
        await self.setup_route();await self.guidance()
        binding=routine._bindings[self.sid];sid=UUID(self.sid);cid=UUID(self.candidate['candidate_id'])
        _,route,_,fp=arrivals.owned(binding.user_id,sid,cid)
        root=cache.lookup(binding.user_id,sid,cid,fp,arrivals.now());root.supplemental_walks.clear()
        with patch.object(walk_provider,'fetch') as fetch:
            walks,reasons=route_walks.get(binding.user_id,sid,cid,route,fp,binding.place_refs[1],1,time.monotonic()+1)
            self.assertEqual(walks,[]);self.assertIn('TRANSFER_WALK_TIME_LIMIT',reasons);fetch.assert_not_called()
        root.lock.acquire()
        try:
            with self.assertRaises(AuthError) as e:route_walks.get(binding.user_id,sid,cid,route,fp,binding.place_refs[1],1,time.monotonic()+20)
            self.assertEqual(e.exception.status,429)
        finally:root.lock.release()

class MappingBudgetTests(unittest.TestCase):
    def test_failed_extra_mapping_is_not_retried_by_transfer_arrival(self):
        from app.guidance.connections import following_arrivals
        from uuid import uuid4
        at=arrivals.now();expiry=at+timedelta(seconds=200)
        root=cache.Entry({},expiry,'snapshot');child=cache.Entry({},expiry,'snapshot')
        child.mapping_attempted_at=at;leg={'leg_id':str(uuid4())}
        with patch.object(arrivals,'owned',return_value=({'expires_at':expiry},None,None,'snapshot')),patch.object(cache,'lookup',return_value=root),patch.object(cache,'following_entry',return_value=child),patch.object(mapping,'resolve') as resolve,patch.object(provider,'fetch') as fetch:
            result=following_arrivals(uuid4(),uuid4(),uuid4(),leg,'snapshot',time.monotonic()+20)
        self.assertEqual(result.status,'mapping_required');resolve.assert_not_called();fetch.assert_not_called()

del Base
