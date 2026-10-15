"""Owned onboard guidance, same-vehicle evidence, no inferred progress."""
import json,unittest
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4
from app.guidance import onboard
from app.arrivals import mapping,provider
from app.common.database import database
from test_manual_trips import ManualTripTests as Base
from test_arrival_mapping_connection import query_fixture
from test_api_contract import request

def binding():
 return {'route_id':'99','board_station_id':'10','board_order':1,'alight_station_id':'20','alight_order':2,'route_dest_id':'30'}
def location(vehicle='123',plate='경기76아1234',seq=1):
 return {'routeId':'99','vehId':vehicle,'plateNo':plate,'stationSeq':seq,'stationId':'10' if seq==1 else '20','stateCd':2}

class OnboardTests(unittest.IsolatedAsyncioTestCase):
 async def onboard(self):
  onboard._entries.clear()
  def collect(owner,sid,candidate):return {l['leg_id']:binding() for l in candidate['ordered_legs'] if l['type']=='BUS'}
  with patch.object(onboard,'collect',side_effect=collect):path=await self.report_departure()
  body=await self.progress_body('boarded');self.assertEqual((await self.call(path,body))[0],201)
  self.url='/trips/'+self.trip['trip_id']
  self.current=(await self.call(self.url))[2]['data']['trip']
  self.input={'expected_version':1,'anchor_event_id':self.current['progress']['anchor_event_id'],
    'leg_id':self.current['progress']['current_leg_id'],'plate_suffix':'1234'}
 def query(self,kind,params,deadline):
  return [location()] if kind=='locations' else query_fixture(kind,params,deadline)
 async def test_explicit_match_uses_same_vehicle_at_alighting_and_cache_never_extends(self):
  await self.onboard()
  with patch.object(mapping,'query',side_effect=self.query) as query,patch.object(provider,'fetch',return_value=[('123',600),('456',900)]) as fetch:
   missing=await self.call(self.url+'/onboard-guidance?expected_version=1');query.assert_not_called();fetch.assert_not_called()
   one=await self.call(self.url+'/onboard-confirmations',self.input)
   two=await self.call(self.url+'/onboard-guidance?expected_version=1')
   repeat=await self.call(self.url+'/onboard-confirmations',self.input)
  self.assertEqual(missing[2]['data']['status'],'needs_data');self.assertEqual(one[0],200,one[2])
  d=one[2]['data'];self.assertEqual(d['status'],'estimated');self.assertGreater(d['remaining_seconds'],590)
  self.assertEqual(d['expires_at'],two[2]['data']['expires_at']);self.assertEqual(d['expires_at'],repeat[2]['data']['expires_at'])
  self.assertEqual(query.call_count,2);self.assertEqual(fetch.call_count,1)
  self.assertEqual(fetch.call_args.args[0].station_id,'20');self.assertEqual(fetch.call_args.args[0].sta_order,2)
  detail=(await self.call(self.url))[2]['data']
  for forbidden in ('transit_bindings','plateNo','vehId','route_id','경기76아1234'):
   self.assertNotIn(forbidden,json.dumps({'detail':detail,'guidance':d}))
 async def test_duplicate_number_reverse_passed_and_other_vehicle_never_produce_eta(self):
  await self.onboard()
  for rows,predictions in [([location(),location('456')],[('123',600)]),([location(seq=2)],[('123',600)]),([location()],[('456',600)])]:
   onboard._entries.clear()
   def query(kind,params,deadline):return rows if kind=='locations' else query_fixture(kind,params,deadline)
   with patch.object(mapping,'query',side_effect=query),patch.object(provider,'fetch',return_value=predictions):r=await self.call(self.url+'/onboard-confirmations',self.input)
   self.assertEqual(r[0],200);self.assertEqual(r[2]['data']['status'],'needs_data');self.assertIsNone(r[2]['data']['estimated_alighting_at'])
 async def test_handoff_during_io_and_profile_change_block_application(self):
  await self.onboard()
  def changes(m):
   with database() as c:c.execute('UPDATE user_profiles SET version=version+1')
   return [('123',600)]
  with patch.object(mapping,'query',side_effect=self.query),patch.object(provider,'fetch',side_effect=changes):r=await self.call(self.url+'/onboard-confirmations',self.input)
  self.assertEqual(r[0],409)
  self.assertTrue(all(e.evidence is None for e in onboard._entries.values()))
 async def test_csrf_owner_wrong_anchor_and_extra_vehicle_id_rejected_before_io(self):
  await self.onboard()
  with patch.object(mapping,'query') as query:
   for body,status in [(self.input|{'anchor_event_id':str(uuid4())},409),(self.input|{'vehicle_id':'123'},422),(self.input|{'plate_suffix':'１２３４'},422)]:
    self.assertEqual((await self.call(self.url+'/onboard-confirmations',body))[0],status)
   headers=[(b'cookie',self.cookie.encode()),(b'content-type',b'application/json'),(b'origin',b'http://127.0.0.1:5173')]
   denied=await request('/api/v1'+self.url+'/onboard-confirmations','POST',headers=headers,body=json.dumps(self.input).encode())
   self.assertEqual(denied[0],403)
   self.assertEqual((await request('/api/v1'+self.url+'/onboard-guidance',query=b'expected_version=1'))[0],401)
   query.assert_not_called()
 async def test_alighting_and_confirmation_expiry_invalidate_guidance(self):
  await self.onboard()
  with patch.object(mapping,'query',side_effect=self.query),patch.object(provider,'fetch',return_value=[('123',600)]):
   self.assertEqual((await self.call(self.url+'/onboard-confirmations',self.input))[2]['data']['status'],'estimated')
  entry=next(iter(onboard._entries.values()));entry.confirmed_until=onboard.arrivals.now()-timedelta(seconds=1)
  self.assertEqual((await self.call(self.url+'/onboard-guidance?expected_version=1'))[2]['data']['status'],'needs_data')
  body={'client_event_id':str(uuid4()),'type':'alighted','leg_id':self.input['leg_id'],'occurred_at':onboard.arrivals.now().isoformat(),'source':'manual'}
  self.assertEqual((await self.call(self.url+'/events',body))[0],201)
  self.assertEqual((await self.call(self.url+'/onboard-guidance?expected_version=1'))[0],409)

 async def test_prediction_missing_keeps_explicit_match_but_never_changes_to_another_vehicle(self):
  await self.onboard()
  with patch.object(mapping,'query',side_effect=self.query),patch.object(provider,'fetch',return_value=[('456',600)]):
   one=await self.call(self.url+'/onboard-confirmations',self.input)
  self.assertEqual(one[2]['data']['status'],'needs_data')
  entry=next(iter(onboard._entries.values()));self.assertEqual(entry.vehicle,'123')
  entry.attempted_at=onboard.arrivals.now()-timedelta(seconds=61)
  def query(kind,params,deadline):return [location('456')] if kind=='locations' else query_fixture(kind,params,deadline)
  with patch.object(mapping,'query',side_effect=query),patch.object(provider,'fetch') as fetch:
   changed=await self.call(self.url+'/onboard-guidance?expected_version=1')
  self.assertEqual(changed[2]['data']['status'],'needs_data');fetch.assert_not_called()

class CaptureTests(unittest.TestCase):
 def test_only_verified_official_ids_are_captured_without_geometry_or_private_vehicle(self):
  from app.arrivals import cache
  from test_arrival_mapping_connection import context
  from uuid import UUID
  cache.clear();self.addCleanup(cache.clear)
  owner=uuid4();sid=uuid4();cid=uuid4();lid=uuid4();expiry=onboard.arrivals.now()+timedelta(seconds=200)
  candidate={'candidate_id':str(cid),'ordered_legs':[{'leg_id':str(lid),'type':'BUS'}]};ctx=context(lid)
  cache.publish(owner,sid,[candidate],{str(cid):ctx},expiry)
  entry=cache.lookup(owner,sid,cid,cache.fingerprint(candidate),onboard.arrivals.now());end={}
  with patch.object(mapping,'query',side_effect=query_fixture):entry.mapping=mapping.resolve(ctx,expiry,boarding_endpoint=end)
  entry.boarding_endpoint=end;stored=onboard.collect(owner,sid,candidate)
  self.assertEqual(stored,{str(lid):binding()})
  for key in ('point','latitude','longitude','vehId','plateNo'):self.assertNotIn(key,json.dumps(stored))

for name,value in Base.__dict__.items():
 if callable(value) and not name.startswith('test_') and not name.startswith('__'):setattr(OnboardTests,name,value)
del Base
