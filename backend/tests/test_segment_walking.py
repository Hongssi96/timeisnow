"""Owned manual timers over PostgreSQL/ASGI; synthetic transport, no external calls."""
import asyncio,copy,json,unittest
from datetime import datetime,timedelta,timezone,time
from types import SimpleNamespace
from uuid import uuid4,UUID
from unittest.mock import patch
from app.common.database import database
from app.trips import repository as trips
from app.personalization import segments,segments_repository as repo
from app.journeys.provider import normalize
from app.guidance.dto import PersonalSegmentWalk
from app.guidance.connections import evaluate
from app.guidance import target
from test_manual_trips import ManualTripTests as Helpers
from test_connections import transfer_route,ConnectionUnitTests
from test_api_contract import request

class SegmentTests(unittest.IsolatedAsyncioTestCase):
 setUp=Helpers.setUp;tearDown=Helpers.tearDown;call=Helpers.call
 prepare=Helpers.prepare;credentials=Helpers.credentials;signup_login=Helpers.signup_login
 saved=Helpers.saved;create=Helpers.create;search=Helpers.search;completed=Helpers.completed
 saved_search=Helpers.saved_search;routine_body=Helpers.routine_body;save=Helpers.save;ready=Helpers.ready
 refresh=Helpers.refresh;path=Helpers.path;configured=Helpers.configured;guidance=Helpers.guidance;start=Helpers.start

 async def fixture(self):
  await self.start()
  with database() as c:
   original=c.execute('SELECT * FROM manual_trips').fetchone();self.owner=original['user_id']
   row=trips.owned(c,self.owner,original['id']);self.snapshot=copy.deepcopy(row['snapshot']);self.rid=row['routine_id']
   trips.cancel(c,row['id'])
  self.route=normalize({'status':'OK','routes':[transfer_route()]},'balanced')[0][0]
  self.snapshot['candidate']=self.route
  self.binding=SimpleNamespace(routine_id=self.rid,version=self.snapshot['routine_version'],place_refs=self.snapshot['place_refs'])

 def event(self,c,kind,leg,at,tid):
  return c.execute('''INSERT INTO manual_trip_events(id,trip_id,client_event_id,body_hash,type,leg_id,source,occurred_at,received_at)
   VALUES(%s,%s,%s,'synthetic',%s,%s,'manual',%s,%s) RETURNING *''',(uuid4(),tid,uuid4(),kind,leg,at,at)).fetchone()

 def new_trip(self):
  now=datetime.now(timezone.utc);tid=uuid4();legs=self.route['ordered_legs']
  with database() as c:
   c.execute("UPDATE manual_trips SET status='cancelled' WHERE user_id=%s AND status='active'",(self.owner,))
   trips.insert(c,self.owner,uuid4(),tid,self.rid,self.snapshot,'assisted')
   for kind,leg,seconds in [('departed',legs[0],55),('boarded',legs[1],50),('alighted',legs[1],45)]:
    self.event(c,kind,leg['leg_id'],now-timedelta(seconds=seconds),tid)
  self.tid=tid;self.base=f'/trips/{tid}/walking-segments'
  return now

 async def timer(self,label='2번 출구 → 같은 방향',kind='transfer',offset=30):
  now=self.new_trip();body={'client_request_id':str(uuid4()),'kind':kind,'leg_id':self.route['ordered_legs'][3]['leg_id'],
   'label':label,'occurred_at':(now-timedelta(seconds=offset)).isoformat(),'start_boundary_confirmed':True}
  r=await self.call(self.base,body);self.assertEqual(r[0],201,r[2]);return r[2]['data'],body

 async def confirm(self,item,*,condition='normal',apply=True,same=True):
  with database() as c:self.event(c,'approach_arrived',self.route['ordered_legs'][2]['leg_id'],datetime.now(timezone.utc)-timedelta(seconds=5),self.tid)
  body={'client_request_id':str(uuid4()),'expected_version':item['version'],'same_scope':same,'condition':condition,'apply_to_guidance':apply}
  r=await self.call(self.base+'/'+item['measurement_id']+'/confirm',body);self.assertEqual(r[0],200,r[2]);return r[2]['data'],body

 def forecasts(self):return segments.for_guidance(self.owner,self.binding,self.route)

 async def edit(self,item,excluded):
  body={'client_request_id':str(uuid4()),'expected_version':item['version'],'excluded':excluded}
  return await request('/api/v1'+self.base+'/'+item['measurement_id'],'PATCH',headers=[(b'origin',b'http://127.0.0.1:5173'),(b'cookie',self.cookie.encode()),(b'x-csrf-token',self.csrf.encode()),(b'content-type',b'application/json')],body=json.dumps(body).encode())

 async def test_five_distinct_trips_opt_in_scopes_prediction_and_recompute(self):
  await self.fixture()
  for i in range(5):
   item,_=await self.timer(offset=20+i);item,_=await self.confirm(item,apply=i==4)
   self.assertEqual(item['sample_count'],i+1)
   if i<4:self.assertIsNone(item['estimate_seconds']);self.assertEqual(self.forecasts(),[])
  value=self.forecasts()[0];self.assertEqual(value['estimate_seconds'],18)
  with database() as c:self.assertEqual(c.execute('SELECT walking_duration_factor FROM user_profiles WHERE user_id=%s',(self.owner,)).fetchone()['walking_duration_factor'],1)
  item,_=await self.timer();self.assertEqual(item['predicted_seconds'],18);prediction=item['predicted_arrival_at']
  self.assertEqual((await self.edit(item,True))[0],409)
  item,_=await self.confirm(item)
  with database() as c:trips.cancel(c,self.tid)
  r=await self.edit(item,True);self.assertEqual(r[0],200,r[2]);excluded=r[2]['data'];self.assertEqual(excluded['sample_count'],5)
  with database() as c:c.execute('UPDATE manual_trip_events SET excluded=true WHERE id=(SELECT ready_event_id FROM walking_segment_measurements WHERE id<>%s LIMIT 1)',(item['measurement_id'],))
  self.assertEqual(self.forecasts(),[])
  replay=(await self.call(self.base))[2]['data']['items'][0];self.assertEqual(replay['predicted_arrival_at'],prediction)
  raw=transfer_route();raw['steps'][3]['properties']['stops'][0]['name']='다른 역'
  changed=normalize({'status':'OK','routes':[raw]},'balanced')[0][0]
  self.assertEqual(segments.for_guidance(self.owner,self.binding,changed),[])
  self.assertEqual(segments.for_guidance(self.owner,SimpleNamespace(routine_id=self.rid,version=self.binding.version+1,place_refs=self.binding.place_refs),self.route),[])

 async def test_idempotency_auth_order_and_excluded_conditions(self):
  await self.fixture();item,body=await self.timer()
  results=await asyncio.gather(self.call(self.base,body),self.call(self.base,body));self.assertEqual([r[0] for r in results],[200,200])
  self.assertEqual((await self.call(self.base,{**body,'label':'다른 범위'}))[0],409)
  self.assertEqual((await self.call(self.base,body,csrf=False))[0],403)
  self.assertEqual((await request('/api/v1'+self.base))[0],401)
  missing={'client_request_id':str(uuid4()),'expected_version':1,'same_scope':True,'condition':'normal','apply_to_guidance':True}
  self.assertEqual((await self.call(self.base+'/'+item['measurement_id']+'/confirm',missing))[0],422)
  item,confirmation=await self.confirm(item,condition='running');self.assertEqual(item['reasons'],['RUNNING']);self.assertEqual(item['sample_count'],0)
  self.assertEqual((await self.call(self.base+'/'+item['measurement_id']+'/confirm',confirmation))[2]['data'],item)
  self.assertEqual(self.forecasts(),[])
  self.assertEqual((await self.call(self.base,{**body,'client_request_id':str(uuid4())}))[0],409)
  with database() as c:trips.cancel(c,self.tid)
  r=await self.edit(item,True);self.assertEqual(r[0],200)
  restored=await self.edit(r[2]['data'],False);self.assertEqual(restored[2]['data']['reasons'],['RUNNING'])
  await self.prepare();credentials=self.credentials('other@example.invalid')
  await self.call('/auth/register',credentials);logged=await self.call('/auth/login',{'email':credentials['email'],'password':credentials['password']})
  self.cookie=logged[1][b'set-cookie'].decode().split(';')[0];self.csrf=logged[2]['data']['csrf_token']
  self.assertEqual((await self.call(self.base))[0],404)
  self.assertEqual((await self.call(self.base+'/'+item['measurement_id']+'/confirm',confirmation))[0],404)

 async def test_station_kind_labels_reset_and_retention_never_mix(self):
  await self.fixture();raw=transfer_route();raw['steps'][3]['properties']['type']='SUBWAY';raw['properties']['type']='BUS_AND_SUBWAY'
  self.route=normalize({'status':'OK','routes':[raw]},'balanced')[0][0];self.snapshot['candidate']=self.route
  for _ in range(5):
   item,_=await self.timer(kind='station_internal');item,_=await self.confirm(item)
  value=self.forecasts();self.assertEqual([v['kind'] for v in value],['station_internal'])
  item,_=await self.timer(label='다른 입구',kind='station_internal');item,_=await self.confirm(item)
  self.assertEqual(item['sample_count'],1);self.assertEqual(self.forecasts(),[])
  p=(await self.call('/me/personalization'))[2]['data']
  reset=await self.call('/me/personalization/reset',{'client_request_id':str(uuid4()),'expected_version':p['profile_version']})
  self.assertEqual(reset[0],200,reset[2])
  self.assertEqual(self.forecasts(),[])
  restore=await self.call('/me/personalization/restore',{'client_request_id':str(uuid4()),'expected_version':reset[2]['data']['profile_version']})
  self.assertEqual(restore[0],200);self.assertEqual(self.forecasts(),[])
  detail=(await self.call(self.base))[2]['data']['items'][0];self.assertIn('BEFORE_RESET',detail['reasons'])
  with database() as c:
   c.execute("UPDATE walking_segment_measurements SET expires_at=clock_timestamp()-interval '1 second' WHERE user_id=%s",(self.owner,))
   repo.clean(c,self.owner)
   self.assertEqual(c.execute('SELECT count(*) AS n FROM walking_segment_selections').fetchone()['n'],0)
   self.assertEqual(c.execute("SELECT count(*) AS n FROM trip_record_mutations WHERE kind='segment'").fetchone()['n'],0)

 async def test_latest_twenty_distinct_samples_and_event_edit_and_deletion(self):
  await self.fixture()
  for i in range(23):
   item,_=await self.timer(offset=15+i);item,_=await self.confirm(item)
  self.assertEqual(item['sample_count'],20);self.assertEqual(item['estimate_seconds'],23)
  before=self.forecasts()[0]['basis_key']
  with database() as c:
   c.execute("UPDATE manual_trip_events SET occurred_at=occurred_at+interval '2 seconds' WHERE id=(SELECT ready_event_id FROM walking_segment_measurements ORDER BY start_received_at DESC LIMIT 1)")
  self.assertNotEqual(self.forecasts()[0]['basis_key'],before)
  with database() as c:
   from app.trips.record_repository import remove
   remove(c,self.owner,trips.owned(c,self.owner,self.tid));self.assertEqual(len(repo.rows(c,self.owner)),22)
  self.assertEqual(self.forecasts()[0]['sample_count'],20)

 async def test_concurrent_confirm_rollback_and_delayed_input(self):
  await self.fixture();item,_=await self.timer()
  with database() as c:self.event(c,'approach_arrived',self.route['ordered_legs'][2]['leg_id'],datetime.now(timezone.utc)-timedelta(seconds=5),self.tid)
  body={'client_request_id':str(uuid4()),'expected_version':1,'same_scope':True,'condition':'normal','apply_to_guidance':True}
  url=self.base+'/'+item['measurement_id']+'/confirm'
  with patch.object(repo,'select',side_effect=RuntimeError('synthetic rollback')):
   failed=await self.call(url,body);self.assertEqual(failed[0],500)
  self.assertEqual((await self.call(self.base))[2]['data']['items'][0]['status'],'recording')
  both=await asyncio.gather(self.call(url,body),self.call(url,body))
  self.assertEqual([r[0] for r in both],[200,200]);self.assertEqual(both[0][2]['data'],both[1][2]['data'])
  item,_=await self.timer()
  with database() as c:
   c.execute("UPDATE walking_segment_measurements SET start_received_at=started_at+interval '61 seconds' WHERE id=%s",(item['measurement_id'],))
  item,_=await self.confirm(item);self.assertIn('INPUT_DELAY',item['reasons']);self.assertEqual(item['sample_count'],1)
  job=await self.call('/trip-exports',{'format':'json'});self.assertEqual(job[0],202)
  file=await self.call(job[2]['data']['result_ref'].removeprefix('/api/v1'))
  self.assertEqual(file[0],200,file[2]);exported=[m for t in file[2]['data']['records'] for m in t['walking_segments']]
  self.assertEqual(len(exported),2);self.assertIn('INPUT_DELAY',next(m for m in exported if m['measurement_id']==item['measurement_id'])['reasons'])

 async def test_fresh_routine_guidance_applies_history_and_rejects_deleted_basis(self):
  from psycopg.types.json import Jsonb
  from app.arrivals import service as arrivals,provider
  from test_first_arrivals import mapping
  from app.guidance import connections
  await self.fixture()
  with database() as c:c.execute('UPDATE journey_plans SET candidate=%s WHERE id=(SELECT journey_plan_id FROM routines WHERE id=%s)',(Jsonb(self.route),self.rid))
  for i in range(4):
   item,_=await self.timer(offset=25+i);item,_=await self.confirm(item)
  with database() as c:trips.cancel(c,self.tid)
  accepted,_=await self.refresh(key='history-ready',version=self.binding.version,data={'status':'OK','routes':[transfer_route()]})
  self.assertEqual(accepted[0],202,accepted[2])
  fresh=(await self.call('/journey-searches/'+accepted[2]['data']['search_id']))[2]['data']['candidates'][0]
  first=fresh['ordered_legs'][1]
  def following(owner,sid,cid,leg,snapshot,deadline):
   from test_connections import ConnectionUnitTests
   return ConnectionUnitTests.evidence(self,datetime.now(timezone.utc),leg,1800)
  with patch.object(arrivals.public_mapping,'resolve',return_value=mapping(UUID(first['leg_id']))),patch.object(provider,'fetch',return_value=[('123',780)]),patch.object(connections,'following_arrivals',side_effect=following):
   response=await self.call(self.path(accepted,self.binding.version))
   self.assertEqual(response[0],200,response[2]);old=response[2]['data']['departure'];self.assertEqual(old['personal_segment_walks'],[])
   item,_=await self.timer(offset=29);item,_=await self.confirm(item)
   with database() as c:trips.cancel(c,self.tid)
   stale=await self.call('/trips',{'guidance_id':old['guidance_id'],'measurement_mode':'assisted'});self.assertEqual(stale[0],409,stale[2])
   response=await self.call(self.path(accepted,self.binding.version))
  self.assertEqual(response[0],200,response[2]);d=response[2]['data']['departure']
  self.assertEqual(d['personal_segment_walks'][0]['sample_count'],5);self.assertEqual(d['transfers'][0]['transfer_walk_seconds'],23)
  self.assertIsNotNone(d['guidance_id']);self.assertEqual(d['buffer_seconds'],300)
  exclusion=await self.edit(item,True);self.assertEqual(exclusion[0],200)
  stale=await self.call('/trips',{'guidance_id':d['guidance_id'],'measurement_mode':'assisted'})
  self.assertEqual(stale[0],409,stale[2])
  self.assertEqual((await self.edit(exclusion[2]['data'],False))[0],200)
  with patch.object(arrivals.public_mapping,'resolve',return_value=mapping(UUID(first['leg_id']))),patch.object(provider,'fetch',return_value=[('123',780)]),patch.object(connections,'following_arrivals',side_effect=following):
   new=(await self.call(self.path(accepted,self.binding.version)))[2]['data']['departure']
   created=await self.call('/trips',{'guidance_id':new['guidance_id'],'measurement_mode':'assisted'});self.assertEqual(created[0],201,created[2])
   departed=await self.call('/trips/'+created[2]['data']['trip_id']+'/events',{'client_event_id':str(uuid4()),'type':'departed','source':'manual','occurred_at':datetime.now(timezone.utc).isoformat(),'leg_id':fresh['ordered_legs'][0]['leg_id']})
   self.assertEqual(departed[0],201,departed[2])
   reported=await self.call(self.path(accepted,self.binding.version));self.assertEqual(reported[0],200,reported[2])
   self.assertFalse(reported[2]['data']['departure']['valid_for_guidance'])

class SegmentConnectionTests(unittest.TestCase):
 fixture=ConnectionUnitTests.fixture;evidence=ConnectionUnitTests.evidence
 def test_transfer_seconds_replace_whole_walk_without_factor_or_buffer_duplication(self):
  at,route,d,p=self.fixture();p['factor']=1.5
  leg=route['ordered_legs'][3]['leg_id']
  d.personal_segment_walks=[PersonalSegmentWalk(kind='transfer',leg_id=leg,label='같은 환승',source='manual_history',profile_version=1,
   basis_key='a'*64,sample_count=5,estimate_seconds=30,valid_until=at+timedelta(days=1))]
  evaluate(route,d,p,at,lambda l:self.evidence(at,l,1800))
  self.assertEqual(d.transfers[0].transfer_walk_seconds,30);self.assertEqual(d.transfers[0].transfer_buffer_seconds,120)
  self.assertIn('MANUAL_HISTORY_WALK',d.transfers[0].reasons)
  self.assertEqual(target.evaluate(route,d,time(23),p,at).status,'estimated_meets')
  d.personal_segment_walks[0].kind='station_internal'
  evaluate(route,d,p,at,lambda l:self.evidence(at,l,1800));self.assertEqual(d.transfers[0].transfer_walk_seconds,150)

del Helpers,ConnectionUnitTests
