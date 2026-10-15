"""Owned manual reports over actual isolated DB/auth APIs, synthetic transport."""
import asyncio,json,unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from uuid import uuid4
from app.common.database import database
from app.guidance import issued
from app.arrivals import service as arrivals,provider
from test_target_arrival import TargetApiTests
from test_api_contract import request

class ManualTripTests(unittest.IsolatedAsyncioTestCase):
 setUp=TargetApiTests.setUp;tearDown=TargetApiTests.tearDown;call=TargetApiTests.call
 prepare=TargetApiTests.prepare;credentials=TargetApiTests.credentials;signup_login=TargetApiTests.signup_login
 saved=TargetApiTests.saved;create_place=TargetApiTests.create;search=TargetApiTests.search;completed=TargetApiTests.completed
 create=TargetApiTests.create
 saved_search=TargetApiTests.saved_search;routine_body=TargetApiTests.routine_body;save=TargetApiTests.save;ready=TargetApiTests.ready
 refresh=TargetApiTests.refresh;path=TargetApiTests.path;configured=TargetApiTests.configured
 async def guidance(self):
  accepted,m=await self.configured()
  self.lastpath=self.path(accepted,2)
  with patch.object(arrivals.public_mapping,'resolve',return_value=m),patch.object(provider,'fetch',return_value=[('123',780)]) as fetch:
   response=await self.call(self.path(accepted,2))
  self.assertEqual(response[0],200);self.d=response[2]['data']['departure'];self.assertIsNotNone(self.d['guidance_id'])
  self.body={'guidance_id':self.d['guidance_id'],'measurement_mode':'assisted'}
  return response
 async def start(self):
  await self.guidance();response=await self.call('/trips',self.body)
  self.assertEqual(response[0],201);self.trip=response[2]['data'];return self.trip
 async def event_body(self):
  detail=await self.call('/trips/'+self.trip['trip_id'])
  return {'client_event_id':str(uuid4()),'type':'departed','source':'manual','occurred_at':datetime.now(timezone.utc).isoformat(),'leg_id':detail[2]['data']['guidance']['candidate']['ordered_legs'][0]['leg_id']}
 async def test_create_pins_immutable_guidance_but_not_departure_and_replay_after_memory_loss(self):
  trip=await self.start();self.assertIsNone(trip['departure_event'])
  issued._items.clear();again=await self.call('/trips',self.body)
  self.assertEqual(again[0],200);self.assertEqual(again[2]['data'],trip)
  changed=await self.call('/trips',{**self.body,'measurement_mode':'baseline'});self.assertEqual(changed[0],409)
  detail=(await self.call('/trips/'+trip['trip_id']))[2]['data'];self.assertEqual(detail['events'],[])
  self.assertEqual(detail['guidance']['departure']['arrival_candidate_id'],self.d['arrival_candidate_id'])
  self.assertIsNone(detail['outcome'])
  text=json.dumps(detail)
  for key in ('latitude','longitude','serviceKey','vehId'):self.assertNotIn(key,text)
 async def test_duplicate_event_replay_different_body_and_second_departure(self):
  await self.start();body=await self.event_body();path='/trips/'+self.trip['trip_id']+'/events'
  one=await self.call(path,body);two=await self.call(path,body)
  self.assertEqual((one[0],two[0]),(201,200));self.assertEqual(one[2]['data'],two[2]['data'])
  self.assertEqual(one[2]['data']['source'],'manual');self.assertGreaterEqual(one[2]['data']['input_delay_seconds'],0)
  self.assertEqual((await self.call(path,{**body,'occurred_at':datetime.now(timezone.utc).isoformat()}))[0],409)
  self.assertEqual((await self.call(path,{**body,'client_event_id':str(uuid4())}))[2]['error']['code'],'INVALID_EVENT_ORDER')
  detail=(await self.call('/trips/'+self.trip['trip_id']))[2]['data'];self.assertEqual(len(detail['events']),1)
 async def test_cancel_version_conflict_keeps_event_and_allows_new_session(self):
  await self.start();body=await self.event_body();tid=self.trip['trip_id']
  self.assertEqual((await self.call('/trips/'+tid+'/events',body))[0],201)
  self.assertEqual((await self.patch_trip(tid,2))[0],409)
  response=await self.patch_trip(tid,1);self.assertEqual(response[0],200);self.assertEqual(response[2]['data']['version'],2)
  self.assertIsNotNone(response[2]['data']['departure_event'])
  self.assertEqual((await self.call('/trips/'+tid+'/events',body))[0],200)
  self.assertEqual((await self.call('/trips/'+tid+'/events',{**body,'client_event_id':str(uuid4())}))[0],409)
  new_id=(await self.call(self.lastpath))[2]['data']['departure']['guidance_id']
  newer=await self.call('/trips',{**self.body,'guidance_id':new_id});self.assertEqual(newer[0],201)
 async def patch_trip(self,tid,version):
  return await request('/api/v1/trips/'+tid,'PATCH',headers=[(b'origin',b'http://127.0.0.1:5173'),(b'cookie',self.cookie.encode()),(b'x-csrf-token',self.csrf.encode()),(b'content-type',b'application/json')],body=json.dumps({'outcome':'cancelled','expected_version':version}).encode())
 async def test_active_unique_and_parallel_same_guidance_requests(self):
  await self.guidance();responses=await asyncio.gather(self.call('/trips',self.body),self.call('/trips',self.body))
  self.assertEqual(sorted(r[0] for r in responses),[200,201]);self.assertEqual(responses[0][2]['data']['trip_id'],responses[1][2]['data']['trip_id'])
  new_id=(await self.call(self.lastpath))[2]['data']['departure']['guidance_id']
  self.assertEqual((await self.call('/trips',{**self.body,'guidance_id':new_id}))[2]['error']['code'],'ACTIVE_TRIP_EXISTS')
 async def test_current_profile_and_place_changes_reject_unpersisted_token(self):
  await self.guidance()
  with database() as c:c.execute('UPDATE user_profiles SET version=version+1')
  self.assertEqual((await self.call('/trips',self.body))[0],409)
  with database() as c:
   self.assertEqual(c.execute('SELECT count(*) AS n FROM guidance_snapshots').fetchone()['n'],0)
   c.execute('UPDATE user_profiles SET version=version-1')
   c.execute('UPDATE saved_places SET location_version=location_version+1')
  self.assertEqual((await self.call('/trips',self.body))[0],409)
 async def test_route_version_change_and_expired_or_missing_token(self):
  await self.guidance()
  with database() as c:c.execute('UPDATE routines SET version=version+1')
  self.assertEqual((await self.call('/trips',self.body))[0],409)
  with database() as c:c.execute('UPDATE routines SET version=version-1')
  item=issued._items[self.d['guidance_id']];item['expires_at']=datetime.now(timezone.utc)-timedelta(seconds=1)
  self.assertEqual((await self.call('/trips',self.body))[0],404)
  self.assertEqual((await self.call('/trips',{**self.body,'guidance_id':str(uuid4())}))[0],404)
 async def test_auth_csrf_foreign_owner_and_no_store(self):
  await self.start();tid=self.trip['trip_id']
  self.assertEqual((await self.call('/trips',self.body,csrf=False))[0],403)
  self.assertEqual((await request('/api/v1/trips'))[0],401)
  await self.prepare();credentials=self.credentials('other@example.invalid')
  await self.call('/auth/register',credentials);logged=await self.call('/auth/login',{'email':credentials['email'],'password':credentials['password']})
  self.cookie=logged[1][b'set-cookie'].decode().split(';')[0];self.csrf=logged[2]['data']['csrf_token']
  self.assertEqual((await self.call('/trips/'+tid))[0],404)
  self.assertEqual((await self.call('/trips',self.body))[0],404)
  listed=await self.call('/trips');self.assertEqual(listed[2]['data']['items'],[]);self.assertEqual(listed[1][b'cache-control'],b'no-store')
 async def test_event_time_leg_and_source_validation(self):
  await self.start();body=await self.event_body();path='/trips/'+self.trip['trip_id']+'/events'
  for change in ({'occurred_at':123},{'occurred_at':'2026-01-01T00:00:00'},{'occurred_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()},{'occurred_at':'2000-01-01T00:00:00Z'},{'leg_id':str(uuid4())},{'source':'gps'},{'type':'unknown'},{'unknown':True}):
   self.assertEqual((await self.call(path,{**body,**change}))[0],422)
  self.assertEqual((await self.call(path,body))[0],201)
 async def test_event_retry_normalizes_timezone_and_retains_first_receipt(self):
  await self.start();body=await self.event_body();path='/trips/'+self.trip['trip_id']+'/events'
  one=await self.call(path,body);body['occurred_at']=datetime.fromisoformat(body['occurred_at']).astimezone(timezone(timedelta(hours=9))).isoformat()
  two=await self.call(path,body);self.assertEqual(two[0],200);self.assertEqual(one[2]['data'],two[2]['data'])
 async def test_creation_header_key_replay_and_changed_body_conflict(self):
  await self.guidance()
  async def keyed(body):
   return await request('/api/v1/trips','POST',headers=[(b'origin',b'http://127.0.0.1:5173'),(b'cookie',self.cookie.encode()),(b'x-csrf-token',self.csrf.encode()),(b'idempotency-key',b'manual-key'),(b'content-type',b'application/json')],body=json.dumps(body).encode())
  one=await keyed(self.body);issued._items.clear();two=await keyed(self.body)
  self.assertEqual((one[0],two[0]),(201,200));self.assertEqual(one[2]['data'],two[2]['data'])
  self.assertEqual((await keyed({**self.body,'guidance_id':str(uuid4())}))[0],409)
 async def test_baseline_session_does_not_require_following_recommendation(self):
  await self.guidance();created=await self.call('/trips',{**self.body,'measurement_mode':'baseline'})
  self.assertEqual(created[0],201);self.assertEqual(created[2]['data']['measurement_mode'],'baseline');self.assertIsNone(created[2]['data']['departure_event'])
 async def test_retention_hides_expired_rows_and_write_cleanup_cascades(self):
  await self.start();await self.call('/trips/'+self.trip['trip_id']+'/events',await self.event_body())
  with database() as c:
   c.execute("UPDATE manual_trips SET expires_at=clock_timestamp()-interval '1 second'")
   c.execute("UPDATE guidance_snapshots SET expires_at=clock_timestamp()-interval '1 second'")
  self.assertEqual((await self.call('/trips/'+self.trip['trip_id']))[0],404)
  self.assertEqual((await self.call('/trips'))[2]['data']['items'],[])
  self.assertEqual((await self.call('/trips',self.body))[0],201)
  with database() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM manual_trip_events').fetchone()['n'],0)

 async def progress_body(self,kind):
  body=await self.event_body();body['type']=kind
  detail=(await self.call('/trips/'+self.trip['trip_id']))[2]['data']
  legs=detail['guidance']['candidate']['ordered_legs'];index=next(i for i,l in enumerate(legs) if l['type'] in ('BUS','SUBWAY'))
  body['leg_id']=legs[index-1 if kind=='approach_arrived' and index>0 else index]['leg_id']
  return body
 async def report_departure(self):
  await self.start();body=await self.event_body()
  self.assertEqual((await self.call('/trips/'+self.trip['trip_id']+'/events',body))[0],201)
  return '/trips/'+self.trip['trip_id']+'/events'
 async def test_approach_boarding_recovery_and_immutable_departure(self):
  path=await self.report_departure();before=(await self.call('/trips/'+self.trip['trip_id']))[2]['data']
  for kind in ('approach_arrived','boarded'):
   body=await self.progress_body(kind);one=await self.call(path,body);two=await self.call(path,body)
   self.assertEqual((one[0],two[0]),(201,200));self.assertEqual(one[2]['data'],two[2]['data'])
   self.assertEqual((await self.call(path,{**body,'leg_id':str(uuid4())}))[0],409)
  saved=(await self.call('/trips/'+self.trip['trip_id']))[2]['data']
  self.assertEqual([e['type'] for e in saved['events']],['departed','approach_arrived','boarded'])
  self.assertEqual(saved['guidance'],before['guidance']);self.assertEqual(saved['trip']['departure_event'],before['trip']['departure_event'])
  self.assertEqual(saved['trip']['approach_event']['type'],'approach_arrived');self.assertEqual(saved['trip']['boarding_event']['type'],'boarded')
  listed=(await self.call('/trips'))[2]['data']['items'][0];self.assertEqual(listed,saved['trip'])
 async def test_board_without_approach_does_not_invent_walking_observation(self):
  path=await self.report_departure();body=await self.progress_body('boarded')
  self.assertEqual((await self.call(path,body))[0],201)
  saved=(await self.call('/trips/'+self.trip['trip_id']))[2]['data'];self.assertIsNone(saved['trip']['approach_event'])
  late=await self.progress_body('approach_arrived');self.assertEqual((await self.call(path,late))[2]['error']['code'],'INVALID_EVENT_ORDER')
  self.assertEqual((await self.call(path,{**body,'client_event_id':str(uuid4())}))[0],409)
 async def test_progress_requires_departure_and_correct_first_leg_and_time(self):
  await self.start();path='/trips/'+self.trip['trip_id']+'/events'
  body=await self.progress_body('approach_arrived');self.assertEqual((await self.call(path,body))[0],409)
  self.assertEqual((await self.call(path,await self.event_body()))[0],201)
  body=await self.progress_body('boarded')
  self.assertEqual((await self.call(path,{**body,'leg_id':str(uuid4())}))[0],422)
  earlier=datetime.fromisoformat(self.d['calculated_at'])-timedelta(seconds=1)
  self.assertEqual((await self.call(path,{**body,'occurred_at':earlier.isoformat()}))[0],422)
  self.assertEqual((await self.call(path,{**body,'occurred_at':(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()}))[0],422)
  approach=await self.progress_body('approach_arrived');self.assertEqual((await self.call(path,approach))[0],201)
  self.assertEqual((await self.call(path,{**body,'occurred_at':approach['occurred_at']}))[0],201)
 async def test_concurrent_boarding_serialized_and_cancel_keeps_replay(self):
  path=await self.report_departure();body=await self.progress_body('boarded')
  results=await asyncio.gather(self.call(path,body),self.call(path,{**body,'client_event_id':str(uuid4())}))
  self.assertEqual(sorted(r[0] for r in results),[201,409])
  saved=next(r[2]['data'] for r in results if r[0]==201)
  self.assertEqual((await self.patch_trip(self.trip['trip_id'],1))[0],200)
  replay={**body,'client_event_id':saved['client_event_id']}
  self.assertEqual((await self.call(path,replay))[0],200)
  self.assertEqual((await self.call(path,await self.progress_body('approach_arrived')))[0],409)
 async def test_progress_stops_remaining_approach_and_departure_suppression_survives(self):
  path=await self.report_departure();body=await self.progress_body('approach_arrived')
  self.assertEqual((await self.call(path,body))[0],201)
  payload={'expected_version':1,'stage':'before_first_boarding','position_confirmed':True,'origin':{'type':'map_pin','latitude':37.5,'longitude':127.0}}
  self.assertEqual((await self.call('/trips/'+self.trip['trip_id']+'/remaining-searches',payload))[2]['error']['code'],'INVALID_EVENT_ORDER')
  response=await self.call(self.lastpath);self.assertEqual(response[2]['data']['departure']['departure_state'],'reported_departed')

del TargetApiTests
