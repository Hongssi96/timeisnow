"""Selected routine target: full timeline and egress, timezone, no extra network."""
import unittest
from datetime import datetime,time,timedelta,timezone
from unittest.mock import patch
from uuid import UUID,uuid4
from app.guidance import target,service
from app.guidance.connections import evaluate as connections
from app.arrivals import service as arrivals,provider
from app.journeys.provider import normalize
from app.common.database import database
from test_journeys import route
from test_connections import transfer_route
from test_first_arrivals import mapping
from test_routine_departure import RoutineDepartureTests

class TargetUnitTests(unittest.TestCase):
 def fixture(self,count=0,egress=50,at=None,factor=1):
  at=at or datetime(2026,10,14,8,tzinfo=timezone.utc);raw=transfer_route(count) if count else route()
  if egress is None:raw['steps'].pop()
  else:raw['steps'][-1]['properties']['time']=egress
  raw['properties']['totalTime']=sum(s['properties']['time'] for s in raw['steps'])
  candidate=normalize({'status':'OK','routes':[raw]},'balanced')[0][0]
  profile={'factor':factor,'buffer':300,'transfer_buffer':120,'version':1}
  def evidence(leg,seconds):
   m=mapping(UUID(leg['leg_id'])).model_copy(update={'verified_at':at-timedelta(seconds=1),'valid_until':at+timedelta(seconds=300)})
   return arrivals.normalize(m,[('123',seconds)],at,at,uuid4(),uuid4(),at+timedelta(seconds=300))
  first=next(l for l in candidate['ordered_legs'] if l['type']!='WALKING')
  d=service.calculate(evidence(first,780),100,100,profile,at)
  times=iter([1800,3000]);connections(candidate,d,profile,at,lambda leg:evidence(leg,next(times)))
  return at,candidate,d,profile
 def test_boundary_meets_and_negative_margin_is_preserved(self):
  at,r,d,p=self.fixture(egress=100);one=target.evaluate(r,d,time(17,23),p,at)
  self.assertEqual(one.status,'estimated_meets');self.assertEqual(one.margin_seconds,0)
  late=target.evaluate(r,d,time(17,22),p,at);self.assertEqual(late.status,'estimated_late');self.assertEqual(late.margin_seconds,-60)
 def test_egress_uses_original_seconds_and_personal_factor_once(self):
  at,r,d,p=self.fixture(egress=101,factor=1.1);one=target.evaluate(r,d,time(18),p,at)
  self.assertEqual(one.egress_seconds,112);self.assertEqual(one.estimated_destination_arrival_at,d.estimated_final_alighting_at+timedelta(seconds=112))
 def test_each_transfer_must_link_before_final_destination(self):
  at,r,d,p=self.fixture(2);one=target.evaluate(r,d,time(18),p,at)
  self.assertEqual(one.status,'estimated_meets');self.assertEqual(one.estimated_destination_arrival_at,at+timedelta(seconds=3550))
  d.transfers[1].next_boarding_at-=timedelta(seconds=1);bad=target.evaluate(r,d,time(18),p,at);self.assertEqual(bad.status,'unknown');self.assertIsNone(bad.margin_seconds)
 def test_missing_zero_egress_and_unconfirmed_connections_never_use_alighting_as_destination(self):
  for seconds in (None,0):
   at,r,d,p=self.fixture(egress=seconds);one=target.evaluate(r,d,time(18),p,at);self.assertEqual(one.reasons,['EGRESS_TIME_UNCONFIRMED']);self.assertIsNone(one.estimated_destination_arrival_at)
  at,r,d,p=self.fixture();d.connection_status='unknown';self.assertEqual(target.evaluate(r,d,time(18),p,at).status,'unknown')
 def test_unset_and_passed_goal_do_not_roll_to_tomorrow(self):
  at,r,d,p=self.fixture();none=target.evaluate(r,d,None,p,at);self.assertEqual(none.status,'not_configured');self.assertIsNone(none.target_arrival_at)
  passed=target.evaluate(r,d,time(16,59),p,at);self.assertEqual(passed.status,'target_passed');self.assertEqual(passed.target_arrival_at.date(),at.date());self.assertIsNone(passed.estimated_destination_arrival_at)
 def test_korean_midnight_uses_local_date_not_utc_date(self):
  at,r,d,p=self.fixture(at=datetime(2026,10,14,16,tzinfo=timezone.utc));one=target.evaluate(r,d,time(1,30),p,at)
  self.assertEqual(one.status,'estimated_meets');self.assertEqual(one.target_arrival_at.astimezone(target.KST).date().isoformat(),'2026-10-15')
 def test_expiry_unreachable_first_vehicle_and_inconsistent_total_are_unknown(self):
  at,r,d,p=self.fixture();self.assertEqual(target.evaluate(r,d,time(18),p,at+timedelta(seconds=121)).status,'stale')
  d.approach_seconds=900;self.assertEqual(target.evaluate(r,d,time(18),p,at).status,'unknown')
  at,r,d,p=self.fixture();r['timing_breakdown']['status']='inconsistent';self.assertEqual(target.evaluate(r,d,time(18),p,at).reasons,['DURATION_TOTAL_MISMATCH'])
 def test_unallocated_provider_total_is_not_added_as_extra_walk(self):
  at,r,d,p=self.fixture();r['timing_breakdown']['status']='unallocated';one=target.evaluate(r,d,time(18),p,at)
  self.assertEqual(one.estimated_destination_arrival_at,at+timedelta(seconds=1330));self.assertIn('PROVIDER_UNALLOCATED_TIME_NOT_USED',one.reasons)

class TargetApiTests(unittest.IsolatedAsyncioTestCase):
 setUp=RoutineDepartureTests.setUp;tearDown=RoutineDepartureTests.tearDown;call=RoutineDepartureTests.call
 prepare=RoutineDepartureTests.prepare;credentials=RoutineDepartureTests.credentials;signup_login=RoutineDepartureTests.signup_login
 saved=RoutineDepartureTests.saved;create=RoutineDepartureTests.create;search=RoutineDepartureTests.search;completed=RoutineDepartureTests.completed
 saved_search=RoutineDepartureTests.saved_search;routine_body=RoutineDepartureTests.routine_body;save=RoutineDepartureTests.save;ready=RoutineDepartureTests.ready
 refresh=RoutineDepartureTests.refresh;path=RoutineDepartureTests.path
 async def configured(self):
  await self.ready()
  with database() as c:c.execute("UPDATE routines SET target_arrival_local_time='23:59',version=2 WHERE id=%s",(self.rid,))
  accepted,_=await self.refresh(version=2);sid=accepted[2]['data']['search_id'];candidate=(await self.call('/journey-searches/'+sid))[2]['data']['candidates'][0]
  return accepted,mapping(UUID(candidate['ordered_legs'][1]['leg_id']))
 async def test_owned_routine_get_evaluates_without_an_additional_provider_request(self):
  accepted,m=await self.configured()
  with patch.object(arrivals.public_mapping,'resolve',return_value=m),patch.object(provider,'fetch',return_value=[('123',780)]) as fetch:
   one=await self.call(self.path(accepted,2));two=await self.call(self.path(accepted,2))
  self.assertEqual((one[0],two[0],fetch.call_count),(200,200,1));g=one[2]['data']['departure']['target_evaluation'];self.assertEqual(g['model_version'],'target.arrival.v1');self.assertIn(g['status'],['estimated_meets','estimated_late','target_passed'])
 async def test_target_changed_during_evaluation_blocks_old_goal(self):
  accepted,m=await self.configured();original=target.evaluate
  def changed(*args):
   value=original(*args)
   with database() as c:c.execute("UPDATE routines SET target_arrival_local_time='22:00',version=version+1 WHERE id=%s",(self.rid,))
   return value
  with patch.object(arrivals.public_mapping,'resolve',return_value=m),patch.object(provider,'fetch',return_value=[('123',780)]),patch.object(target,'evaluate',side_effect=changed):reply=await self.call(self.path(accepted,2))
  self.assertEqual(reply[0],409)
 async def test_profile_changed_during_goal_evaluation_blocks_old_factor(self):
  accepted,m=await self.configured();original=target.evaluate
  def changed(*args):
   value=original(*args)
   with database() as c:c.execute('UPDATE user_profiles SET version=version+1')
   return value
  with patch.object(arrivals.public_mapping,'resolve',return_value=m),patch.object(provider,'fetch',return_value=[('123',780)]),patch.object(target,'evaluate',side_effect=changed):reply=await self.call(self.path(accepted,2))
  self.assertEqual(reply[0],409)

del RoutineDepartureTests
