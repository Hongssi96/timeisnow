"""Missing routine access recovery with official mapping, isolated DB and no network."""
import copy,json,time,unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch,MagicMock
from uuid import UUID
from app.guidance import walk_provider,access,routine
from app.arrivals import mapping,provider as arrivals_provider,cache,service as arrivals
from app.common.database import database
from app.common.errors import AuthError
from test_routine_departure import RoutineDepartureTests
from test_arrival_mapping_connection import query_fixture
from test_journeys import route

START=(127.,37.);END=(127.001,37.)
def packet(seconds=300):
 return {'status':'OK','route':{'properties':{'totalTime':seconds,'totalDistance':200},'legs':[{'properties':{'time':seconds,'distance':200},'steps':[{'properties':{'time':seconds,'distance':200},'path':{'points':[list(START),list(END)]}}]}]}}

class WalkProviderTests(unittest.TestCase):
 def test_seconds_geometry_and_leg_sums_are_validated(self):
  self.assertEqual(walk_provider.parse(packet(),START,END),300)
  for mutate in (lambda d:d['route']['properties'].update(totalTime=True),lambda d:d['route']['legs'][0]['properties'].update(time=301),lambda d:d['route']['legs'][0]['steps'][0]['path'].update(points=[[127.,float('nan')],list(END)])):
   d=packet();mutate(d)
   with self.assertRaises(AuthError):walk_provider.parse(d,START,END)
 def test_endpoint_direction_and_path_continuity_are_not_guessed(self):
  with self.assertRaises(AuthError):walk_provider.parse(packet(),END,START)
  d=packet();d['route']['legs'][0]['steps'][0]['path']['points']=[list(START),[127.01,37.]]
  with self.assertRaises(AuthError):walk_provider.parse(d,START,END)
 def test_no_route_and_zero_never_become_a_default_time(self):
  for status in walk_provider.NO_ROUTE:self.assertIsNone(walk_provider.parse({'status':status},START,END))
  self.assertIsNone(walk_provider.parse(packet(0),START,END))
  with self.assertRaises(AuthError):walk_provider.parse({'status':'unknown'},START,END)
 def test_transport_is_fixed_https_bounded_and_uses_ephemeral_response(self):
  opener=MagicMock();response=MagicMock();opener.open.return_value.__enter__.return_value=response;response.read.return_value=json.dumps(packet()).encode()
  with patch.object(walk_provider,'dotenv_values',return_value={'KAKAO_REST_API_KEY':'synthetic'}),patch.dict(walk_provider.os.environ,{},clear=True),patch.object(walk_provider.urllib.request,'build_opener',return_value=opener):
   self.assertEqual(walk_provider.fetch(START,END,time.monotonic()+20),300)
  request=opener.open.call_args.args[0];self.assertTrue(request.full_url.startswith('https://dapi.kakao.com/v2/routing/walk?'));self.assertLessEqual(opener.open.call_args.kwargs['timeout'],3);response.read.assert_called_once_with(1048577)
 def test_mapping_endpoint_is_the_official_row_and_never_diagnostics(self):
  from test_arrival_mapping_connection import context
  sink={};diagnostics={}
  def shifted(kind,params,deadline):
   rows=query_fixture(kind,params,deadline)
   if kind=='stops':rows[0]['x']+=.0001
   return rows
  with patch.object(mapping,'query',side_effect=shifted):value=mapping.resolve(context(),datetime.now(timezone.utc)+timedelta(seconds=200),boarding_endpoint=sink,diagnostics=diagnostics)
  self.assertIsNotNone(value);self.assertAlmostEqual(sink['point'][0],127.0277);self.assertEqual(sink['mapping_identity'],cache.mapping_identity(value));self.assertNotIn('point',str(diagnostics));self.assertNotIn('boarding_endpoint',value.model_dump())
 def test_duplicate_json_and_oversize_are_rejected_without_raw_errors(self):
  for raw in (b'{"status":"OK","status":"OK"}',b'x'*1048577):
   opener=MagicMock();opener.open.return_value.__enter__.return_value.read.return_value=raw
   with patch.object(walk_provider,'dotenv_values',return_value={'KAKAO_REST_API_KEY':'synthetic'}),patch.dict(walk_provider.os.environ,{},clear=True),patch.object(walk_provider.urllib.request,'build_opener',return_value=opener),self.assertRaises(AuthError) as error:walk_provider.fetch(START,END,time.monotonic()+20)
   self.assertEqual(error.exception.code,'PROVIDER_RESPONSE_INVALID')

class AccessWalkTests(unittest.IsolatedAsyncioTestCase):
 setUp=RoutineDepartureTests.setUp;tearDown=RoutineDepartureTests.tearDown;call=RoutineDepartureTests.call
 prepare=RoutineDepartureTests.prepare;credentials=RoutineDepartureTests.credentials;signup_login=RoutineDepartureTests.signup_login
 saved=RoutineDepartureTests.saved;create=RoutineDepartureTests.create;search=RoutineDepartureTests.search;completed=RoutineDepartureTests.completed
 routine_body=RoutineDepartureTests.routine_body;save=RoutineDepartureTests.save;refresh=RoutineDepartureTests.refresh;path=RoutineDepartureTests.path
 async def ready_missing(self):
  routine._bindings.clear();await self.signup_login();_,home=await self.saved('집');_,work=await self.saved('회사')
  home=home[2]['data'];work=work[2]['data'];self.home_id=home['place_id']
  raw=route();raw['steps']=raw['steps'][1:];self.raw=raw
  body={'origin':{'type':'saved_place','place_id':home['place_id']},'destination':{'type':'saved_place','place_id':work['place_id']},'timing':{'mode':'depart_now','timezone':'Asia/Seoul'}}
  accepted,result,_=await self.completed(body=body,data={'status':'OK','routes':[raw]});candidate=result[2]['data']['candidates'][0]
  created=await self.save(self.routine_body(home,work,accepted[2]['data']['search_id'],candidate));self.rid=created[2]['data']['routine_id']
  self.accepted,_=await self.refresh(data={'status':'OK','routes':[raw]});self.sid=self.accepted[2]['data']['search_id']
 async def reply(self,walk=300):
  with patch.object(mapping,'query',side_effect=query_fixture),patch.object(arrivals_provider,'fetch',return_value=[('123',1800)]),patch.object(walk_provider,'fetch',return_value=walk) as upstream:
   result=await self.call(self.path(self.accepted))
  return result,upstream.call_count
 async def test_owned_routine_recovers_missing_access_and_keeps_database_snapshot(self):
  await self.ready_missing()
  with database() as c:before=c.execute('SELECT * FROM journey_searches WHERE id=%s',(self.sid,)).fetchone()
  response,count=await self.reply();self.assertEqual((response[0],count),(200,1));d=response[2]['data']['departure'];self.assertTrue(d['valid_for_guidance']);self.assertEqual(d['provider_approach_source'],'boarding_walk');self.assertEqual(d['provider_approach_seconds'],300);self.assertEqual(d['approach_seconds'],300)
  with database() as c:after=c.execute('SELECT * FROM journey_searches WHERE id=%s',(self.sid,)).fetchone()
  self.assertEqual(before,after)
  for private in ('latitude','longitude','station_id','mapping_identity','boarding_endpoint'):self.assertNotIn(private,json.dumps(response[2]))
 async def test_profile_change_recalculates_original_walk_once_without_another_provider_call(self):
  await self.ready_missing();first,_=await self.reply(walk=301)
  with database() as c:c.execute('UPDATE user_profiles SET walking_duration_factor=1.1,version=version+1')
  second,count=await self.reply(walk=999)
  self.assertEqual(count,0);d=second[2]['data']['departure'];self.assertEqual(d['approach_seconds'],332);self.assertEqual(d['provider_approach_seconds'],301)
  self.assertEqual(d['approach_fetched_at'],first[2]['data']['departure']['approach_fetched_at']);self.assertEqual(d['approach_valid_until'],first[2]['data']['departure']['approach_valid_until'])
 async def test_unmapped_station_or_absent_endpoint_never_requests_walk(self):
  await self.ready_missing()
  with patch.object(mapping,'resolve',return_value=None),patch.object(walk_provider,'fetch') as fetch:response=await self.call(self.path(self.accepted))
  fetch.assert_not_called();self.assertFalse(response[2]['data']['departure']['valid_for_guidance'])
 async def test_walk_failure_cache_has_no_default_seconds_or_repeated_request(self):
  await self.ready_missing()
  with patch.object(mapping,'query',side_effect=query_fixture),patch.object(arrivals_provider,'fetch',return_value=[('123',1800)]),patch.object(walk_provider,'fetch',side_effect=AuthError(504,'PROVIDER_TIMEOUT','synthetic')) as fetch:
   one=await self.call(self.path(self.accepted));two=await self.call(self.path(self.accepted))
  self.assertEqual(fetch.call_count,1)
  for reply in (one,two):
   d=reply[2]['data']['departure'];self.assertIsNone(d['approach_seconds']);self.assertIsNone(d['selected_departure_at']);self.assertIn('ACCESS_WALK_TIMEOUT',d['reasons'])
 async def test_place_or_profile_changed_during_walk_blocks_result(self):
  await self.ready_missing()
  def change(*args):
   with database() as c:c.execute('UPDATE user_profiles SET version=version+1')
   return 300
  with patch.object(mapping,'query',side_effect=query_fixture),patch.object(arrivals_provider,'fetch',return_value=[('123',1800)]),patch.object(walk_provider,'fetch',side_effect=change):reply=await self.call(self.path(self.accepted))
  self.assertEqual(reply[0],409)
 async def test_original_candidate_get_cannot_infer_a_saved_origin(self):
  await self.ready_missing();search=(await self.call('/journey-searches/'+self.sid))[2]['data'];candidate=search['candidates'][0]
  path=f"/journey-searches/{self.sid}/candidates/{candidate['candidate_id']}/first-departure"
  with patch.object(mapping,'query',side_effect=query_fixture),patch.object(arrivals_provider,'fetch',return_value=[('123',1800)]),patch.object(walk_provider,'fetch') as fetch:reply=await self.call(path)
  fetch.assert_not_called();self.assertIsNone(reply[2]['data']['approach_seconds'])
 async def test_missing_endpoint_and_insufficient_deadline_fail_without_walk(self):
  await self.ready_missing();await self.reply()
  candidate=(await self.call('/journey-searches/'+self.sid))[2]['data']['candidates'][0];sid=UUID(self.sid);cid=UUID(candidate['candidate_id'])
  binding=routine._bindings[self.sid];row,route,first,fp=arrivals.owned(binding.user_id,sid,cid);entry=cache.lookup(binding.user_id,sid,cid,fp,arrivals.now());entry.access_walk=None
  with patch.object(walk_provider,'fetch') as fetch:
   value,reason=access.get(binding.user_id,sid,cid,first,fp,binding.place_refs[0],time.monotonic()+1);self.assertEqual(reason,'ACCESS_WALK_TIME_LIMIT')
   entry.boarding_endpoint=None;value,reason=access.get(binding.user_id,sid,cid,first,fp,binding.place_refs[0],time.monotonic()+20);self.assertEqual(reason,'ACCESS_WALK_MAPPING_REQUIRED');fetch.assert_not_called()

 async def test_place_version_change_during_walk_blocks_and_does_not_cache(self):
  await self.ready_missing()
  def change(*args):
   with database() as c:c.execute('UPDATE saved_places SET location_version=location_version+1 WHERE id=%s',(self.home_id,))
   return 300
  with patch.object(mapping,'query',side_effect=query_fixture),patch.object(arrivals_provider,'fetch',return_value=[('123',1800)]),patch.object(walk_provider,'fetch',side_effect=change):reply=await self.call(self.path(self.accepted))
  self.assertEqual(reply[0],409)
 async def test_duplicate_access_lock_blocks_another_walk(self):
  await self.ready_missing();await self.reply();binding=routine._bindings[self.sid]
  candidate=(await self.call('/journey-searches/'+self.sid))[2]['data']['candidates'][0];sid=UUID(self.sid);cid=UUID(candidate['candidate_id']);row,route,first,fp=arrivals.owned(binding.user_id,sid,cid)
  entry=cache.lookup(binding.user_id,sid,cid,fp,arrivals.now());entry.access_walk=None;entry.lock.acquire()
  try:
   with patch.object(walk_provider,'fetch') as fetch,self.assertRaises(AuthError) as error:access.get(binding.user_id,sid,cid,first,fp,binding.place_refs[0],time.monotonic()+20)
   self.assertEqual(error.exception.status,429);fetch.assert_not_called()
  finally:entry.lock.release()
 async def test_zero_walk_result_has_no_departure_or_placeholder_minutes(self):
  await self.ready_missing();reply,count=await self.reply(walk=0);self.assertEqual(count,1);d=reply[2]['data']['departure'];self.assertIsNone(d['selected_departure_at']);self.assertIsNone(d['approach_seconds']);self.assertIn('ACCESS_WALK_UNAVAILABLE',d['reasons'])

del RoutineDepartureTests
