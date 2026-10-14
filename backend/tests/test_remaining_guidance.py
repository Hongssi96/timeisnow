"""Actual owned ASGI/DB sessions with synthetic current-point transit."""
import json,unittest
from datetime import timedelta
from dataclasses import replace
from unittest.mock import patch
from uuid import UUID,uuid4
from test_manual_trips import ManualTripTests
from test_api_contract import request
from test_journeys import route
from test_first_arrivals import mapping
from app.guidance import remaining
from app.arrivals import service as arrivals,provider
from app.journeys import provider as journey_provider
from app.places import provider as places_provider
from app.common.database import database

class RemainingTests(unittest.IsolatedAsyncioTestCase):
 setUp=ManualTripTests.setUp;tearDown=ManualTripTests.tearDown;call=ManualTripTests.call
 prepare=ManualTripTests.prepare;credentials=ManualTripTests.credentials;signup_login=ManualTripTests.signup_login
 saved=ManualTripTests.saved;create=ManualTripTests.create;search=ManualTripTests.search;completed=ManualTripTests.completed
 saved_search=ManualTripTests.saved_search;routine_body=ManualTripTests.routine_body;save=ManualTripTests.save;ready=ManualTripTests.ready
 refresh=ManualTripTests.refresh;path=ManualTripTests.path;configured=ManualTripTests.configured
 guidance=ManualTripTests.guidance;start=ManualTripTests.start;event_body=ManualTripTests.event_body;patch_trip=ManualTripTests.patch_trip
 async def departed(self):
  remaining._bindings.clear();await self.start()
  self.assertEqual((await self.call('/trips/'+self.trip['trip_id']+'/events',await self.event_body()))[0],201)
  self.query={'expected_version':1,'stage':'before_first_boarding','position_confirmed':True,
      'origin':{'type':'map_pin','latitude':37.5001,'longitude':127.029}}
 async def admit(self,body=None,routes=None,key=None,csrf=True):
  headers=[(b'origin',b'http://127.0.0.1:5173'),(b'content-type',b'application/json'),(b'cookie',self.cookie.encode())]
  if csrf:headers.append((b'x-csrf-token',self.csrf.encode()))
  if key:headers.append((b'idempotency-key',key.encode()))
  with patch.object(places_provider,'region_for_location',return_value='서울 합성동'),patch.object(journey_provider,'fetch_routes',
      return_value={'status':'OK','routes':routes if routes is not None else [route(walking=120)]}) as fetch:
   r=await request('/api/v1/trips/'+self.trip['trip_id']+'/remaining-searches','POST',headers=headers,body=json.dumps(body or self.query).encode())
  return r,fetch
 async def fresh_candidate(self,accepted):
  sid=accepted[2]['data']['search_id'];r=await self.call('/journey-searches/'+sid)
  return r[2]['data']['candidates'][0]
 def result_path(self,accepted,tid=None,version=1):
  return '/trips/'+(tid or self.trip['trip_id'])+'/remaining-searches/'+accepted[2]['data']['search_id']+'/guidance?expected_version='+str(version)
 async def calculate(self,accepted,predictions=None):
  c=await self.fresh_candidate(accepted)
  with patch.object(arrivals.public_mapping,'resolve',return_value=mapping(UUID(c['ordered_legs'][1]['leg_id']))),patch.object(provider,'fetch',return_value=predictions or [('123',780)]) as fetch:
   r=await self.call(self.result_path(accepted))
  return r,fetch
 async def test_current_point_access_not_original_or_elapsed_and_snapshot_unchanged(self):
  await self.departed();before=(await self.call('/trips/'+self.trip['trip_id']))[2]['data']
  accepted,fetch=await self.admit();self.assertEqual(accepted[0],202);self.assertEqual(fetch.call_count,1)
  start=fetch.call_args.args[0];self.assertEqual(float(start.latitude),self.query['origin']['latitude'])
  r,upstream=await self.calculate(accepted);self.assertEqual(r[0],200);d=r[2]['data']
  self.assertTrue(d['valid_for_guidance']);self.assertEqual(d['remaining_approach_seconds'],120)
  self.assertNotEqual(d['remaining_approach_seconds'],self.d['approach_seconds'])
  self.assertGreater(d['slack_seconds'],600);self.assertEqual(d['timing_basis'],'receipt_estimate')
  self.assertEqual((await self.call('/trips/'+self.trip['trip_id']))[2]['data'],before)
  self.assertEqual(upstream.call_count,1)
  for secret in ['latitude','longitude','guidance_id','recommended_departure_at','station_id','vehId']:
   self.assertNotIn(secret,json.dumps(d))
 async def test_missing_confirmation_stage_saved_origin_and_csrf_are_blocked_before_routes(self):
  await self.departed()
  for change in [{'position_confirmed':False},{'position_confirmed':1},{'stage':'boarded'},
      {'origin':{'type':'saved_place','place_id':str(uuid4())}},{'slack_seconds':999},
      {'origin':{'type':'current_location','latitude':37.5,'longitude':127,'accuracy_meters':10,'captured_at':'2026-10-14T00:00:00Z','location_confirmed':False}}]:
   r,f=await self.admit({**self.query,**change});self.assertEqual(r[0],422);f.assert_not_called()
  r,f=await self.admit(csrf=False);self.assertEqual(r[0],403);f.assert_not_called()
 async def test_session_creation_and_cancel_are_not_valid_departure_context(self):
  await self.departed();await self.patch_trip(self.trip['trip_id'],1)
  r,f=await self.admit();self.assertEqual(r[0],409);f.assert_not_called()
  with database() as c:
   c.execute('DELETE FROM manual_trip_events');c.execute("UPDATE manual_trips SET status='active',version=1")
  r,f=await self.admit();self.assertEqual(r[0],409);f.assert_not_called()
 async def test_replay_preserves_point_expiry_and_restart_never_restarts_provider(self):
  await self.departed();one,_=await self.admit(key='same-point');two,f=await self.admit(key='same-point')
  self.assertEqual(two[0],202);self.assertEqual(one[2]['data'],two[2]['data']);f.assert_not_called()
  remaining._bindings.clear();r,f=await self.admit(key='same-point');self.assertEqual(r[0],404);f.assert_not_called()
 async def test_no_changed_or_ambiguous_route_has_no_numbers_or_arrival_lookup(self):
  await self.departed();changed=route();changed['steps'][1]['properties']['vehicles']=[{'name':'다른노선'}]
  for values,status in [([],'no_routes'),([changed],'route_changed'),([route(),route()],'ambiguous_route')]:
   a,_=await self.admit(routes=values)
   with patch.object(provider,'fetch') as f:r=await self.call(self.result_path(a))
   self.assertEqual((r[0],r[2]['data']['status']),(200,status));self.assertIsNone(r[2]['data']['slack_seconds']);f.assert_not_called()
 async def test_point_expiry_wrong_trip_version_profile_and_cancel_during_calculation(self):
  await self.departed();a,_=await self.admit();sid=a[2]['data']['search_id']
  self.assertEqual((await self.call(self.result_path(a,tid=str(uuid4()))))[0],404)
  self.assertEqual((await self.call(self.result_path(a,version=2)))[0],409)
  b=remaining._bindings[sid];remaining._bindings[sid]=replace(b,expires_at=arrivals.now()-timedelta(seconds=1))
  self.assertEqual((await self.call(self.result_path(a)))[0],404);remaining._bindings[sid]=b
  with database() as c:c.execute('UPDATE user_profiles SET version=version+1')
  self.assertEqual((await self.call(self.result_path(a)))[0],409)
 async def test_cancellation_during_upstream_never_returns_numbers(self):
  await self.departed();a,_=await self.admit();c=await self.fresh_candidate(a)
  def cancelled(*args,**kwargs):
   with database() as connection:connection.execute("UPDATE manual_trips SET status='cancelled',version=2")
   return [('123',780)]
  with patch.object(arrivals.public_mapping,'resolve',return_value=mapping(UUID(c['ordered_legs'][1]['leg_id']))),patch.object(provider,'fetch',side_effect=cancelled):
   r=await self.call(self.result_path(a))
  self.assertEqual(r[0],409)
 async def test_zero_walk_does_not_manufacture_remaining_time(self):
  await self.departed();a,_=await self.admit(routes=[route(walking=0)])
  r,_=await self.calculate(a);self.assertEqual(r[0],200);d=r[2]['data']
  self.assertFalse(d['valid_for_guidance']);self.assertIsNone(d['remaining_approach_seconds']);self.assertIsNone(d['slack_seconds'])

del ManualTripTests
