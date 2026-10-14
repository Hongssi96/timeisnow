"""Routine selection to fresh search and departure; isolated DB, synthetic upstream."""
import copy,json,unittest
from unittest.mock import patch
from uuid import UUID,uuid4
from psycopg.types.json import Jsonb
from test_routines import RoutineTests
from test_api_contract import request
from test_first_arrivals import mapping
from test_journeys import route
from app.guidance import routine
from app.arrivals import provider as arrivals_provider,service as arrivals
from app.journeys import provider as journey_provider
from app.places import provider as places_provider
from app.common.database import database
from app.common.errors import AuthError

class RoutineDepartureTests(unittest.IsolatedAsyncioTestCase):
    setUp=RoutineTests.setUp;tearDown=RoutineTests.tearDown;call=RoutineTests.call
    prepare=RoutineTests.prepare;credentials=RoutineTests.credentials;signup_login=RoutineTests.signup_login
    saved=RoutineTests.saved;create=RoutineTests.create;search=RoutineTests.search;completed=RoutineTests.completed
    saved_search=RoutineTests.saved_search;routine_body=RoutineTests.routine_body;save=RoutineTests.save

    async def ready(self):
        routine._bindings.clear()
        await self.signup_login()
        home,work,search,candidate=await self.saved_search()
        created=await self.save(self.routine_body(home,work,search,candidate))
        self.rid=created[2]['data']['routine_id'];self.candidate=candidate
        return created[2]['data']

    async def refresh(self,key='fresh',version=1,data=None,csrf=True):
        headers=[(b'origin',b'http://127.0.0.1:5173'),(b'content-type',b'application/json'),(b'idempotency-key',key.encode())]
        if self.cookie:headers.append((b'cookie',self.cookie.encode()))
        if csrf:headers.append((b'x-csrf-token',self.csrf.encode()))
        with patch.object(places_provider,'region_for_location',return_value='서울 합성동'),patch.object(journey_provider,'fetch_routes',return_value=data if data is not None else {'status':'OK','routes':[route(walking=300)]}) as fetch:
            reply=await request(f'/api/v1/routines/{self.rid}/departure-searches','POST',headers=headers,body=json.dumps({'expected_version':version}).encode())
        return reply,fetch.call_count

    def path(self,accepted,version=1):
        return f"/routines/{self.rid}/departure-searches/{accepted[2]['data']['search_id']}/first-departure?expected_version={version}"

    async def test_fresh_search_matching_route_departure_no_routine_mutation_and_cached_poll(self):
        before=await self.ready();accepted,count=await self.refresh();self.assertEqual((accepted[0],count),(202,1))
        sid=accepted[2]['data']['search_id'];search=(await self.call('/journey-searches/'+sid))[2]['data'];candidate=search['candidates'][0]
        self.assertNotEqual(candidate['candidate_id'],self.candidate['candidate_id'])
        with patch.object(arrivals.public_mapping,'resolve',return_value=mapping(UUID(candidate['ordered_legs'][1]['leg_id']))),patch.object(arrivals_provider,'fetch',return_value=[('123',780)]) as upstream:
            one=await self.call(self.path(accepted));two=await self.call(self.path(accepted))
        self.assertEqual((one[0],two[0],upstream.call_count),(200,200,1))
        data=one[2]['data'];self.assertEqual(data['status'],'ready');self.assertEqual(data['departure']['approach_seconds'],300)
        self.assertTrue(data['departure']['valid_for_guidance']);self.assertEqual(data['departure']['slack_seconds'],300)
        self.assertEqual((await self.call('/routines/'+self.rid))[2]['data'],before)
        for key in ('latitude','longitude','station_id','vehId','serviceKey'):self.assertNotIn(key,json.dumps(one[2]))

    async def test_route_changed_or_ambiguous_no_arrival_fetch_or_silent_route_change(self):
        await self.ready()
        changed=route();changed['steps'][1]['properties']['vehicles']=[{'name':'다른 노선'}]
        for routes,expected in (([changed],'route_changed'),([route(),route(seconds=1000)],'ambiguous_route'),([],'no_routes')):
            accepted,_=await self.refresh(str(uuid4()),data={'status':'OK','routes':routes})
            with patch.object(arrivals_provider,'fetch') as fetch:reply=await self.call(self.path(accepted))
            self.assertEqual(reply[0],200);self.assertEqual(reply[2]['data']['status'],expected)
            self.assertIsNone(reply[2]['data']['departure']);fetch.assert_not_called()

    async def test_auth_csrf_and_version_block_before_provider(self):
        await self.ready()
        for version,csrf,status in ((2,True,409),(1,False,403)):
            reply,count=await self.refresh(str(uuid4()),version=version,csrf=csrf)
            self.assertEqual((reply[0],count),(status,0))
        cookie=self.cookie;self.cookie=None;reply,count=await self.refresh();self.cookie=cookie
        self.assertEqual((reply[0],count),(401,0))

    async def test_idempotent_replay_never_restarts_routes_and_missing_binding_requires_new_key(self):
        await self.ready();one,_=await self.refresh();two,count=await self.refresh()
        self.assertEqual((two[0],count),(202,0));self.assertEqual(one[2]['data'],two[2]['data'])
        routine._bindings.clear();three,count=await self.refresh();self.assertEqual((three[0],count),(404,0))
        four,count=await self.refresh('new-key');self.assertEqual((four[0],count),(202,1))

    async def test_restart_and_different_routine_or_owner_cannot_reuse_search(self):
        await self.ready();accepted,_=await self.refresh();path=self.path(accepted)
        with patch.object(arrivals_provider,'fetch') as upstream:
            wrong=path.replace(self.rid,str(uuid4()));self.assertEqual((await self.call(wrong))[0],404)
            self.assertEqual((await request('/api/v1'+path.split('?')[0],query=b'expected_version=1'))[0],401)
            routine._bindings.clear();self.assertEqual((await self.call(path))[0],404)
            upstream.assert_not_called()

    async def test_version_change_during_arrival_rejects_old_result(self):
        await self.ready();accepted,_=await self.refresh();sid=accepted[2]['data']['search_id']
        candidate=(await self.call('/journey-searches/'+sid))[2]['data']['candidates'][0]
        def mutate(_):
            with database() as connection:connection.execute('UPDATE routines SET version=version+1 WHERE id=%s',(self.rid,))
            return [('123',780)]
        with patch.object(arrivals.public_mapping,'resolve',return_value=mapping(UUID(candidate['ordered_legs'][1]['leg_id']))),patch.object(arrivals_provider,'fetch',side_effect=mutate):reply=await self.call(self.path(accepted))
        self.assertEqual(reply[0],409)

    async def test_saved_place_change_and_search_refs_change_block(self):
        await self.ready();accepted,_=await self.refresh();sid=accepted[2]['data']['search_id']
        with database() as connection:
            row=connection.execute('SELECT place_refs FROM journey_searches WHERE id=%s',(sid,)).fetchone()
            connection.execute('UPDATE journey_searches SET place_refs=%s WHERE id=%s',(Jsonb(list(reversed(row['place_refs']))),sid))
        with patch.object(arrivals_provider,'fetch') as fetch:reply=await self.call(self.path(accepted))
        self.assertEqual(reply[0],409);fetch.assert_not_called()

    async def test_expired_search_and_failed_worker_never_guide(self):
        await self.ready();accepted,_=await self.refresh();sid=accepted[2]['data']['search_id']
        with database() as connection:connection.execute("UPDATE journey_searches SET status='failed',candidates='[]',error=%s WHERE id=%s",(Jsonb({'code':'PROVIDER_TIMEOUT'}),sid))
        reply=await self.call(self.path(accepted));self.assertEqual((reply[0],reply[2]['error']['code']),(503,'PROVIDER_TIMEOUT'))
        with database() as connection:connection.execute("UPDATE journey_searches SET expires_at=now()-interval '1 second' WHERE id=%s",(sid,))
        self.assertEqual((await self.call(self.path(accepted)))[0],404)

    async def test_routine_changed_during_admission_never_starts_provider(self):
        await self.ready()
        original=routine.journeys.search
        def change(*args,**kwargs):
            outcome=original(*args,**kwargs)
            with database() as connection:connection.execute('UPDATE routines SET version=version+1 WHERE id=%s',(self.rid,))
            return outcome
        with patch.object(routine.journeys,'search',side_effect=change):reply,count=await self.refresh()
        self.assertEqual((reply[0],count),(409,0))
        self.assertFalse(routine._bindings)

    def test_binding_capacity_and_expiry_fail_closed(self):
        from datetime import datetime,timedelta,timezone
        routine._bindings.clear();now=datetime.now(timezone.utc)
        identifiers=[str(uuid4()) for _ in range(33)]
        expired=str(uuid4());binding=routine.Binding(uuid4(),uuid4(),1,uuid4(),'signature',now-timedelta(seconds=1),())
        routine.put(expired,binding)
        for identifier in identifiers:routine.put(identifier,routine.Binding(binding.user_id,binding.routine_id,1,binding.plan_id,'signature',now+timedelta(seconds=300),()))
        self.assertEqual(len(routine._bindings),32);self.assertNotIn(expired,routine._bindings);self.assertNotIn(identifiers[0],routine._bindings)
        routine._bindings.clear()

    def test_signature_ignores_fresh_ids_times_but_not_order_or_mode(self):
        from app.journeys.provider import normalize
        one=normalize({'status':'OK','routes':[route()]},'balanced')[0][0]
        two=normalize({'status':'OK','routes':[route(walking=301,seconds=1800)]},'balanced')[0][0]
        self.assertEqual(routine.signature(one),routine.signature(two))
        raw=route();raw['steps'][1]['properties']['vehicles']=[{'name':'다른 차량'}]
        two=normalize({'status':'OK','routes':[raw]},'balanced')[0][0]
        self.assertNotEqual(routine.signature(one),routine.signature(two))

del RoutineTests
