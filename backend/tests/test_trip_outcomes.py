"""Manual terminal reports are atomic, replayable and never inferred movement."""
import asyncio,unittest
from unittest.mock import patch
from datetime import datetime,timezone
from uuid import uuid4
import test_stage_guidance as fixture
from app.common.database import database
from app.trips import repository

class TripOutcomeTests(unittest.IsolatedAsyncioTestCase):
 async def finish_vehicles(self):
  await self.prepare_stages()
  for _ in range(3):
   self.assertEqual((await self.report('boarded'))[0][0],201)
   self.assertEqual((await self.report('alighted'))[0][0],201)
 async def test_arrived_requires_last_alighting_and_preserves_original_history(self):
  await self.finish_vehicles();before=await self.detail();self.assertIsNone(before['outcome'])
  self.assertEqual(before['trip']['status'],'active')
  result,body=await self.report('arrived');self.assertEqual(result[0],201)
  detail=await self.detail();self.assertEqual(detail['outcome'],'completed');self.assertEqual(detail['trip']['version'],2)
  self.assertEqual(detail['trip']['progress']['stage'],'completed');self.assertEqual(detail['trip']['progress']['actions'],{})
  self.assertEqual(detail['trip']['terminal_event'],result[2]['data']);self.assertEqual(detail['guidance'],before['guidance'])
  self.assertEqual(detail['events'][:-1],before['events']);self.assertEqual((await self.call('/trips?status=completed'))[2]['data']['items'][0],detail['trip'])
  self.assertEqual((await self.call('/trips?status=active'))[2]['data']['items'],[])
  self.assertEqual((await self.call('/trips/'+self.trip['trip_id']+'/events',body))[0],200)
  self.assertEqual((await self.call('/trips/'+self.trip['trip_id']+'/events',{**body,'client_event_id':str(uuid4())}))[0],409)
  self.assertEqual((await self.patch_trip(self.trip['trip_id'],2))[0],409)
 async def test_missed_before_boarding_and_after_transfer_releases_active_slot(self):
  await self.transfer();before=await self.detail()
  one,body=await self.report('missed');self.assertEqual(one[0],201)
  detail=await self.detail();self.assertEqual((detail['outcome'],detail['trip']['version']),('missed',2))
  self.assertEqual(detail['trip']['progress']['stage'],'missed');self.assertEqual(detail['trip']['terminal_event']['type'],'missed')
  self.assertEqual(detail['events'][:-1],before['events'])
  replay=await self.call('/trips',self.body);self.assertEqual(replay[0],200);self.assertEqual(replay[2]['data']['status'],'missed')
  from app.arrivals import provider,service as arrivals
  from test_first_arrivals import mapping
  from uuid import UUID
  # Use the saved multi-vehicle shape again, otherwise the fresh result is a different route.
  from test_connections import transfer_route
  accepted,_=await self.refresh(key='after-missed-route',version=2,data={'status':'OK','routes':[transfer_route(2)]})
  candidate=(await self.call('/journey-searches/'+accepted[2]['data']['search_id']))[2]['data']['candidates'][0]
  with patch.object(arrivals.public_mapping,'resolve',return_value=mapping(UUID(candidate['ordered_legs'][1]['leg_id']))),patch.object(provider,'fetch',return_value=[('123',780)]),patch('app.guidance.connections.following_arrivals',side_effect=fixture.no_following):
   guidance=(await self.call(self.path(accepted,2)))[2]['data']['departure']
  new=await self.call('/trips',{**self.body,'guidance_id':guidance['guidance_id']});self.assertEqual(new[0],201)
  self.assertNotEqual(new[2]['data']['trip_id'],self.trip['trip_id'])
 async def test_no_early_arrival_or_onboard_missed_wrong_leg_or_future(self):
  await self.prepare_stages();legs=(await self.detail())['guidance']['candidate']['ordered_legs']
  self.assertEqual((await self.report('arrived',legs[-1]['leg_id']))[0][0],409)
  self.assertEqual((await self.report('missed',str(uuid4())))[0][0],422)
  await self.report('boarded');self.assertEqual((await self.report('missed',legs[1]['leg_id']))[0][0],409)
  self.assertEqual((await self.report('arrived',legs[-1]['leg_id']))[0][0],409)
 async def test_concurrent_terminal_reports_store_only_one_and_replay_same_id(self):
  await self.prepare_stages();p=(await self.detail())['trip']['progress']
  body={'client_event_id':str(uuid4()),'type':'missed','leg_id':p['next_leg_id'],'source':'manual','occurred_at':datetime.now(timezone.utc).isoformat()}
  path='/trips/'+self.trip['trip_id']+'/events'
  replies=await asyncio.gather(self.call(path,body),self.call(path,{**body,'client_event_id':str(uuid4())}))
  self.assertEqual(sorted(r[0] for r in replies),[201,409])
  detail=await self.detail();self.assertEqual(detail['trip']['version'],2)
  saved=detail['trip']['terminal_event'];body['client_event_id']=saved['client_event_id']
  self.assertEqual((await self.call(path,body))[0],200)
  self.assertEqual((await self.call(path,{**body,'occurred_at':datetime.now(timezone.utc).isoformat()}))[0],409)
 async def test_terminal_failure_rolls_back_event_and_status_and_clears_old_guidance(self):
  await self.prepare_stages();p=(await self.detail())['trip']['progress']
  with patch.object(repository,'finish',side_effect=RuntimeError('synthetic transaction failure')):
   response,_=await self.report('missed');self.assertEqual(response[0],500)
  current=await self.detail();self.assertEqual(current['trip']['status'],'active');self.assertIsNone(current['trip']['terminal_event'])
  self.assertEqual(len(current['events']),1)
  self.query['stage']='before_first_boarding';search,_=await self.admit(routes=[self.suffix(0)])
  self.assertEqual(search[0],202)
  self.assertEqual((await self.report('missed'))[0][0],201)
  self.assertEqual((await self.call(self.result_path(search)))[0],409)
  response,fetch=await self.admit();self.assertEqual(response[0],409);fetch.assert_not_called()
 async def test_auth_csrf_and_foreign_terminal_report(self):
  await self.prepare_stages();p=(await self.detail())['trip']['progress'];path='/trips/'+self.trip['trip_id']+'/events'
  body={'client_event_id':str(uuid4()),'type':'missed','leg_id':p['next_leg_id'],'source':'manual','occurred_at':datetime.now(timezone.utc).isoformat()}
  self.assertEqual((await self.call(path,body,csrf=False))[0],403)
  from test_api_contract import request
  self.assertEqual((await request('/api/v1'+path,'POST',headers=[(b'content-type',b'application/json')],body=__import__('json').dumps(body).encode()))[0],401)
  self.assertEqual((await self.call('/trips/'+str(uuid4())+'/events',body))[0],404)

# Reuse preparation helpers without collecting the fixture's tests a second time.
for name in ('setUp tearDown call prepare credentials signup_login saved create search completed saved_search routine_body save ready refresh path configured guidance start event_body patch_trip departed admit calculate calculate_base fresh_candidate result_path prepare_stages detail report transfer suffix').split():
 setattr(TripOutcomeTests,name,getattr(fixture.StageGuidanceTests,name))
