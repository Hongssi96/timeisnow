"""Route stages and transfer suffixes over owned ASGI/DB; no real providers."""
import asyncio,unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from uuid import uuid4
from test_remaining_guidance import RemainingTests
from test_connections import transfer_route
from app.common.database import database
from app.guidance.connections import unconfirmed

def no_following(owner,sid,cid,leg,snapshot,deadline):
 return unconfirmed(sid,cid,leg,datetime.now(timezone.utc)+timedelta(seconds=120),'LEG_MAPPING_UNCONFIRMED')

class StageGuidanceTests(unittest.IsolatedAsyncioTestCase):
 setUp=RemainingTests.setUp;tearDown=RemainingTests.tearDown;call=RemainingTests.call
 prepare=RemainingTests.prepare;credentials=RemainingTests.credentials;signup_login=RemainingTests.signup_login
 saved=RemainingTests.saved;create=RemainingTests.create;search=RemainingTests.search;completed=RemainingTests.completed
 saved_search=RemainingTests.saved_search;routine_body=RemainingTests.routine_body;save=RemainingTests.save;ready=RemainingTests.ready
 refresh=RemainingTests.refresh;path=RemainingTests.path;configured=RemainingTests.configured
 guidance=RemainingTests.guidance;start=RemainingTests.start;event_body=RemainingTests.event_body;patch_trip=RemainingTests.patch_trip
 departed=RemainingTests.departed;admit=RemainingTests.admit
 calculate_base=RemainingTests.calculate
 fresh_candidate=RemainingTests.fresh_candidate;result_path=RemainingTests.result_path
 async def prepare_stages(self):
  with patch('test_journeys.route',side_effect=lambda **kw:transfer_route(2)),patch('test_routine_departure.route',side_effect=lambda **kw:transfer_route(2)),patch('app.guidance.connections.following_arrivals',side_effect=no_following):
   await self.departed()
  self.query['stage']='transfer'
  return (await self.detail())['trip']['progress']
 async def calculate(self,accepted,predictions=None):
  with patch('app.guidance.connections.following_arrivals',side_effect=no_following):return await self.calculate_base(accepted,predictions)
 async def detail(self):return (await self.call('/trips/'+self.trip['trip_id']))[2]['data']
 async def report(self,kind,leg=None,cid=None):
  p=(await self.detail())['trip']['progress']
  body={'client_event_id':cid or str(uuid4()),'type':kind,'source':'manual','leg_id':leg or p['actions'][kind],
      'occurred_at':datetime.now(timezone.utc).isoformat()}
  return await self.call('/trips/'+self.trip['trip_id']+'/events',body),body
 async def transfer(self):
  await self.prepare_stages();self.assertEqual((await self.report('boarded'))[0][0],201)
  self.assertEqual((await self.report('alighted'))[0][0],201)
  return (await self.detail())['trip']['progress']
 def suffix(self,completed=1):
  raw=transfer_route(2);raw['steps']=raw['steps'][completed*2:]
  raw['steps'][0]['properties']['time']=120
  raw['properties']['transfers']=2-completed
  raw['properties']['totalTime']=sum(s['properties']['time'] for s in raw['steps'])
  return raw
 async def test_three_vehicles_follow_manual_order_and_keep_first_summaries(self):
  p=await self.prepare_stages();self.assertEqual(p['stage'],'approaching')
  before=await self.detail();first_board=None
  for index in range(3):
   if index:self.assertEqual((await self.detail())['trip']['progress']['stage'],'transfer')
   self.assertEqual((await self.report('approach_arrived'))[0][0],201)
   self.assertIn((await self.detail())['trip']['progress']['stage'],('waiting','transfer_waiting'))
   boarded,body=await self.report('boarded');self.assertEqual(boarded[0],201)
   first_board=first_board or boarded[2]['data'];self.assertEqual((await self.detail())['trip']['progress']['stage'],'onboard')
   self.assertEqual((await self.call('/trips/'+self.trip['trip_id']+'/events',body))[0],200)
   self.assertEqual((await self.report('alighted'))[0][0],201)
  after=await self.detail();self.assertEqual(after['trip']['progress']['stage'],'transit_finished')
  self.assertEqual(after['trip']['progress']['actions'],{'arrived':after['guidance']['candidate']['ordered_legs'][-1]['leg_id']});self.assertEqual(after['guidance'],before['guidance'])
  self.assertEqual(after['trip']['boarding_event'],first_board);self.assertEqual(len(after['events']),10)
  self.assertIsNone(after['outcome'])
 async def test_out_of_order_wrong_vehicle_and_concurrent_alighting(self):
  await self.prepare_stages();legs=(await self.detail())['guidance']['candidate']['ordered_legs']
  self.assertEqual((await self.report('alighted',legs[1]['leg_id']))[0][0],409)
  self.assertEqual((await self.report('boarded',legs[3]['leg_id']))[0][0],422)
  await self.report('boarded')
  replies=await asyncio.gather(self.report('alighted'),self.report('alighted',legs[1]['leg_id']))
  self.assertEqual(sorted(x[0][0] for x in replies),[201,409])
  self.assertEqual((await self.detail())['trip']['progress']['stage'],'transfer')
 async def test_transfer_uses_new_access_transfer_buffer_and_remaining_suffix_only(self):
  progress=await self.transfer();before=await self.detail()
  a,_=await self.admit(routes=[self.suffix()]);self.assertEqual(a[0],202)
  r,_=await self.calculate(a);self.assertEqual(r[0],200);d=r[2]['data']
  self.assertTrue(d['valid_for_guidance']);self.assertEqual(d['stage'],'transfer')
  self.assertEqual(d['anchor_event_id'],progress['anchor_event_id']);self.assertEqual(d['next_leg_id'],progress['next_leg_id'])
  self.assertEqual(d['remaining_approach_seconds'],120);self.assertEqual(d['buffer_seconds'],120)
  self.assertEqual(len(d['transfers']),1)
  after=await self.detail();self.assertEqual(before,after)
  await self.report('approach_arrived')
  self.assertIsNone((await self.detail())['trip']['approach_event'])
 async def test_boarding_and_approach_invalidate_old_binding_before_and_during_get(self):
  await self.transfer();a,_=await self.admit(routes=[self.suffix()]);self.assertEqual(a[0],202)
  await self.report('approach_arrived')
  self.assertEqual((await self.call(self.result_path(a)))[0],409)
  b,_=await self.admit(routes=[self.suffix()]);self.assertEqual(b[0],202)
  from app.arrivals import provider
  from app.arrivals import service as arrivals
  from test_first_arrivals import mapping
  from uuid import UUID
  c=await self.fresh_candidate(b)
  def boarded(*args):
   # Simulate a concurrent legitimate report after the initial progress check.
   from app.trips import repository as repo
   from app.trips.dto import Event
   body=Event(client_event_id=uuid4(),type='boarded',leg_id=(self.trip_leg),source='manual',occurred_at=datetime.now(timezone.utc).isoformat())
   with database() as conn:
    repo.lock_owner(conn,self.owner);repo.add_event(conn,self.tid,uuid4(),body,'0'*64,datetime.now(timezone.utc))
   return [('123',780)]
  with database() as conn:
   row=conn.execute('SELECT id,user_id FROM manual_trips').fetchone();self.owner=row['user_id'];self.tid=row['id']
  self.trip_leg=(await self.detail())['trip']['progress']['actions']['boarded']
  with patch.object(arrivals.public_mapping,'resolve',return_value=mapping(UUID(c['ordered_legs'][1]['leg_id']))),patch.object(provider,'fetch',side_effect=boarded),patch('app.guidance.connections.following_arrivals',side_effect=no_following):
   self.assertEqual((await self.call(self.result_path(b)))[0],409)
 async def test_transfer_rejects_original_full_route_and_onboard_search(self):
  await self.prepare_stages();await self.report('boarded')
  denied,fetch=await self.admit();self.assertEqual(denied[0],409);fetch.assert_not_called()
  await self.report('alighted');a,_=await self.admit(routes=[transfer_route(2)])
  r,fetch=await self.calculate(a);self.assertEqual(r[2]['data']['status'],'route_changed');fetch.assert_not_called()

del RemainingTests
