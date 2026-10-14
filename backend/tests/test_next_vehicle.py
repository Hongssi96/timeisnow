"""Only supplied, still valid first vehicles; never fabricate missed-trip events."""
import unittest
from datetime import timedelta,time
from unittest.mock import patch
from uuid import UUID
from app.arrivals import service as arrivals,provider
from app.guidance import service,target
from app.guidance.connections import evaluate
from test_departure import DepartureCalculationTests
from test_target_arrival import TargetUnitTests,TargetApiTests

fixture=DepartureCalculationTests.fixture
timeline_fixture=TargetUnitTests.fixture

class NextVehicleTests(unittest.TestCase):
 def evidence(self,seconds):
  at,e,p=fixture(self)
  values=[e.candidates[0].model_copy(update={'candidate_id':UUID(int=i+1),'predicted_arrival_at':at+timedelta(seconds=s),'provider_prediction_seconds':s}) for i,s in enumerate(seconds)]
  return at,e.model_copy(update={'candidates':values}),p
 def test_unreachable_first_selects_supplied_second_without_extending_receipt(self):
  at,e,p=self.evidence([120,780]);d=service.calculate(e,300,300,p,at)
  self.assertTrue(d.valid_for_guidance);self.assertEqual(d.arrival_candidate_id,e.candidates[1].candidate_id)
  self.assertEqual(d.recommended_departure_at,at+timedelta(seconds=180));self.assertIn('NEXT_REACHABLE_VEHICLE',d.reasons)
  self.assertEqual(d.valid_until,e.expires_at);self.assertEqual(d.arrival_evidence.received_at,e.received_at)
  self.assertEqual(len(d.arrival_evidence.candidates),2)
 def test_reachable_first_and_below_buffer_are_preserved(self):
  at,e,p=self.evidence([480,780]);d=service.calculate(e,300,300,p,at)
  self.assertEqual(d.arrival_candidate_id,e.candidates[0].candidate_id);self.assertEqual(d.slack_seconds,180)
  self.assertIn('BUFFER_NOT_MET',d.reasons);self.assertNotIn('NEXT_REACHABLE_VEHICLE',d.reasons)
 def test_exact_access_boundary_now_basis_and_fractional_shortfall(self):
  for seconds,expected in ((300,0),(299.999,1)):
   at,e,p=self.evidence([seconds,780]);d=service.calculate(e,300,300,p,at,'now')
   self.assertEqual(d.arrival_candidate_id,e.candidates[expected].candidate_id);self.assertEqual(d.selected_departure_at,at)
   self.assertEqual(d.slack_seconds,0 if expected==0 else 480)
 def test_no_reachable_vehicle_keeps_negative_slack(self):
  at,e,p=self.evidence([120,240]);d=service.calculate(e,300,300,p,at)
  self.assertFalse(d.valid_for_guidance);self.assertEqual(d.slack_seconds,-180);self.assertEqual(d.status,'not_enough_time')
  self.assertNotIn('NEXT_REACHABLE_VEHICLE',d.reasons)
 def test_sorting_and_deterministic_equal_eta(self):
  at,e,p=self.evidence([1000,120,780,780]);d=service.calculate(e,300,300,p,at)
  self.assertEqual(d.arrival_candidate_id,e.candidates[2].candidate_id)
 def test_missing_access_expired_and_source_error_do_not_switch(self):
  at,e,p=self.evidence([120,780])
  for evidence,walk,observed in ((e,None,at),(e,300,at+timedelta(seconds=121)),(e,300,at-timedelta(seconds=1))):
   d=service.calculate(evidence,walk,walk,p,observed)
   self.assertFalse(d.valid_for_guidance);self.assertIsNone(d.selected_departure_at);self.assertNotIn('NEXT_REACHABLE_VEHICLE',d.reasons)
 def test_later_first_vehicle_recalculates_transfer_and_destination(self):
  at,route,old,p=timeline_fixture(self,count=1)
  first=old.arrival_evidence.candidates[0]
  e=old.arrival_evidence.model_copy(update={'candidates':[first.model_copy(update={'predicted_arrival_at':at+timedelta(seconds=50)}),first.model_copy(update={'candidate_id':UUID(int=7),'predicted_arrival_at':at+timedelta(seconds=1800)})]})
  d=service.calculate(e,100,100,p,at)
  def following(leg):
   value=e.model_copy(update={'candidates':[first.model_copy(update={'predicted_arrival_at':at+timedelta(seconds=3000)})]})
   return value
  evaluate(route,d,p,at,following)
  self.assertEqual(d.transfers[0].minimum_boarding_at,at+timedelta(seconds=2520))
  goal=target.evaluate(route,d,time(18),p,at)
  self.assertEqual(goal.estimated_destination_arrival_at,at+timedelta(seconds=3550));self.assertEqual(goal.margin_seconds,50)

class NextVehicleApiTests(unittest.IsolatedAsyncioTestCase):
 setUp=TargetApiTests.setUp;tearDown=TargetApiTests.tearDown;call=TargetApiTests.call
 prepare=TargetApiTests.prepare;credentials=TargetApiTests.credentials;signup_login=TargetApiTests.signup_login
 saved=TargetApiTests.saved;create=TargetApiTests.create;search=TargetApiTests.search;completed=TargetApiTests.completed
 saved_search=TargetApiTests.saved_search;routine_body=TargetApiTests.routine_body;save=TargetApiTests.save;ready=TargetApiTests.ready
 refresh=TargetApiTests.refresh;path=TargetApiTests.path;configured=TargetApiTests.configured
 async def test_routine_uses_second_vehicle_for_target_and_cached_replay(self):
  accepted,m=await self.configured()
  with patch.object(arrivals.public_mapping,'resolve',return_value=m),patch.object(provider,'fetch',return_value=[('123',30),('456',780)]) as fetch:
   one=await self.call(self.path(accepted,2));two=await self.call(self.path(accepted,2))
  self.assertEqual((one[0],two[0],fetch.call_count),(200,200,1))
  d=one[2]['data']['departure'];self.assertTrue(d['valid_for_guidance']);self.assertIn('NEXT_REACHABLE_VEHICLE',d['reasons'])
  self.assertEqual(d['vehicle_arrival_at'],d['arrival_evidence']['candidates'][1]['predicted_arrival_at'])
  self.assertIsNotNone(d['estimated_final_alighting_at']);self.assertEqual(d['arrival_evidence']['received_at'],two[2]['data']['departure']['arrival_evidence']['received_at'])

del DepartureCalculationTests,TargetUnitTests,TargetApiTests
