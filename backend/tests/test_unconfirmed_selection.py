"""Strict half boundary, refreshed searches, and stored manual departure gates."""
import unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from uuid import uuid4,UUID
from app.guidance import selection,service,routine
from app.arrivals import service as arrivals,cache,provider
from test_first_arrivals import mapping
from test_manual_trips import ManualTripTests
from app.common.database import database

class SelectionTests(unittest.TestCase):
 def setUp(self):
  self.at=datetime(2026,10,14,8,tzinfo=timezone.utc)
  self.profile={'factor':1.,'buffer':300,'transfer_buffer':120,'version':1}
  self.binding=routine.Binding(uuid4(),uuid4(),1,uuid4(),'same route',self.at+timedelta(seconds=300),())
  self.session=selection.Session(self.at+timedelta(seconds=120))
  self.obs=patch.object(selection,'observation',return_value=(None,False));self.obs.start()
 def tearDown(self):self.obs.stop()
 def run_at(self,seconds,etas=(600,1200),search_id=None,profile=None,walking=300):
  at=self.at+timedelta(seconds=seconds);sid=search_id or UUID(int=1);cid=UUID(int=2)
  m=mapping().model_copy(update={'verified_at':self.at-timedelta(seconds=1),'valid_until':self.at+timedelta(seconds=2000)})
  received=self.at+timedelta(seconds=int(seconds))
  values=[(str(i+1),eta-int(seconds)) for i,eta in enumerate(etas)]
  e=arrivals.normalize(m,values,received,at,sid,cid,self.at+timedelta(seconds=2000))
  root=cache.Entry({},self.at+timedelta(seconds=2000),'fingerprint');root.mapping=m;root.evidence=e
  root.vehicle_keys=arrivals.vehicle_keys(m,values,sid,cid)
  lease=selection.Lease(self.session,self.binding);p=profile or self.profile
  with patch.object(cache,'lookup',return_value=root):choice=lease.choose(e,walking,p,at,'fingerprint')
  d=service.calculate(e,walking,walking,p,at,choice=choice);lease.commit(d)
  return d,root
 def test_exact_half_boundary_does_not_switch_but_fractional_excess_does(self):
  first,_=self.run_at(0);equal,_=self.run_at(150);next_one,_=self.run_at(150.001)
  self.assertEqual(first.arrival_candidate_id,equal.arrival_candidate_id)
  self.assertNotEqual(equal.arrival_candidate_id,next_one.arrival_candidate_id)
  self.assertEqual(next_one.recommended_departure_at,self.at+timedelta(seconds=600))
  self.assertIn('DEPARTURE_UNCONFIRMED_NEXT_VEHICLE',next_one.reasons)
 def test_pending_rule_survives_new_search_candidate_ids_without_public_vehicle_keys(self):
  first,root=self.run_at(0);new,newroot=self.run_at(151,search_id=uuid4())
  self.assertNotEqual(first.arrival_candidate_id,new.arrival_candidate_id)
  self.assertIn('DEPARTURE_UNCONFIRMED_NEXT_VEHICLE',new.reasons)
  self.assertEqual(set(root.vehicle_keys.values()),set(newroot.vehicle_keys.values()))
  self.assertNotIn('vehicle_keys',new.model_dump_json());self.assertNotIn('private.first.vehicle',new.model_dump_json())
 def test_missing_or_buffer_short_next_vehicle_never_fabricates_times(self):
  for etas in ((600,),(600,700)):
   self.session=selection.Session(self.at+timedelta(seconds=120));self.run_at(0,etas)
   d,_=self.run_at(151,etas);self.assertFalse(d.valid_for_guidance);self.assertIsNone(d.selected_departure_at)
   self.assertEqual(d.reasons,['DEPARTURE_UNCONFIRMED_NO_NEXT'])
 def test_excluded_first_vehicle_does_not_reappear_before_next_half_deadline(self):
  self.run_at(0);chosen,_=self.run_at(151);repeat,_=self.run_at(152)
  self.assertEqual(chosen.arrival_candidate_id,repeat.arrival_candidate_id);self.assertEqual(len(self.session.value['skipped']),1)
 def test_changed_profile_or_walk_resets_old_half_anchor(self):
  self.run_at(0);d,_=self.run_at(151,profile={**self.profile,'version':2})
  self.assertNotIn('DEPARTURE_UNCONFIRMED_NEXT_VEHICLE',d.reasons)
  self.assertEqual(len(self.session.value['skipped']),0)
 def test_receipt_eta_update_changes_the_next_displayed_anchor(self):
  self.run_at(0);d,_=self.run_at(100,etas=(700,1300))
  self.assertEqual(self.session.value['anchor']['s'],d.recommended_departure_at)
  same,_=self.run_at(250,etas=(700,1300));self.assertNotIn('DEPARTURE_UNCONFIRMED_NEXT_VEHICLE',same.reasons)
 def test_missing_identity_is_blocked_instead_of_using_eta_as_vehicle_identity(self):
  at=self.at;m=mapping().model_copy(update={'verified_at':at-timedelta(seconds=1),'valid_until':at+timedelta(seconds=300)})
  e=arrivals.normalize(m,[('1',600)],at,at,uuid4(),uuid4(),at+timedelta(seconds=300));lease=selection.Lease(self.session,self.binding)
  with patch.object(cache,'lookup',return_value=None):choice=lease.choose(e,300,self.profile,at,'f')
  self.assertEqual(choice['reason'],'SELECTION_IDENTITY_UNCONFIRMED')
 def test_trip_change_between_query_and_commit_keeps_original_anchor(self):
  self.run_at(0);old=self.session.value.copy();lease=selection.Lease(self.session,self.binding)
  with patch.object(selection,'observation',return_value=(('new event',),True)):
   with self.assertRaises(Exception) as caught:lease.commit(None)
  self.assertEqual(caught.exception.code,'VERSION_CONFLICT');self.assertEqual(self.session.value,old)
 def test_concurrent_lease_is_429_and_releases_after_close(self):
  selection._states.clear()
  with patch.object(arrivals,'now',return_value=self.at):
   lease=selection.begin(self.binding)
   try:
    with self.assertRaises(Exception) as caught:selection.begin(self.binding)
    self.assertEqual(caught.exception.status,429)
   finally:lease.close()
   another=selection.begin(self.binding);another.close()
 def test_selected_eta_expiry_starts_a_new_anchor_without_reviving_observations(self):
  selection._states.clear()
  with patch.object(arrivals,'now',return_value=self.at):
   lease=selection.begin(self.binding);old=lease.entry;old.expires_at=self.at+timedelta(seconds=1);lease.close()
  with patch.object(arrivals,'now',return_value=self.at+timedelta(seconds=2)):
   fresh=selection.begin(self.binding)
   self.assertIsNot(fresh.entry,old);self.assertIsNone(fresh.pending['anchor']);fresh.close()
 def test_history_limit_never_grows_past_sixteen_or_releases_old_exclusions(self):
  self.run_at(0);self.session.value['skipped']=set(str(i) for i in range(16))
  d,_=self.run_at(151);self.assertEqual(d.reasons,['SELECTION_HISTORY_LIMIT']);self.assertEqual(len(self.session.value['skipped']),16)
 def test_anchor_expiring_during_upstream_wait_is_reset_before_selection(self):
  self.run_at(0);d,_=self.run_at(601,etas=(1500,))
  self.assertTrue(d.valid_for_guidance);self.assertNotIn('DEPARTURE_UNCONFIRMED_NO_NEXT',d.reasons)
  self.assertEqual(len(self.session.value['skipped']),0)

class SelectionApiTests(unittest.IsolatedAsyncioTestCase):
 setUp=ManualTripTests.setUp;tearDown=ManualTripTests.tearDown;call=ManualTripTests.call
 prepare=ManualTripTests.prepare;credentials=ManualTripTests.credentials;signup_login=ManualTripTests.signup_login
 saved=ManualTripTests.saved;create=ManualTripTests.create;search=ManualTripTests.search;completed=ManualTripTests.completed
 saved_search=ManualTripTests.saved_search;routine_body=ManualTripTests.routine_body;save=ManualTripTests.save;ready=ManualTripTests.ready
 refresh=ManualTripTests.refresh;path=ManualTripTests.path;configured=ManualTripTests.configured
 guidance=ManualTripTests.guidance;start=ManualTripTests.start;event_body=ManualTripTests.event_body;patch_trip=ManualTripTests.patch_trip
 async def test_persisted_departed_suppresses_rule_and_all_provider_calls_even_after_memory_reset(self):
  await self.start();body=await self.event_body();await self.call('/trips/'+self.trip['trip_id']+'/events',body)
  selection._states.clear()
  with patch.object(provider,'fetch') as fetch:response=await self.call(self.lastpath)
  fetch.assert_not_called();self.assertEqual(response[0],200);d=response[2]['data']['departure']
  self.assertEqual(d['departure_state'],'reported_departed');self.assertFalse(d['valid_for_guidance']);self.assertIsNone(d['selected_departure_at']);self.assertIsNone(d['guidance_id'])
 async def test_session_without_departed_does_not_suppress_half_switch_and_goal_recalculation(self):
  accepted,m=await self.configured();self.lastpath=self.path(accepted,2);at=arrivals.now()
  with patch.object(arrivals,'now',return_value=at),patch.object(arrivals.public_mapping,'resolve',return_value=m),patch.object(provider,'fetch',return_value=[('1',690),('2',1200)]):
   initial=await self.call(self.lastpath)
  self.body={'guidance_id':initial[2]['data']['departure']['guidance_id'],'measurement_mode':'assisted'}
  self.assertEqual((await self.call('/trips',self.body))[0],201)
  with patch.object(arrivals,'now',return_value=at+timedelta(seconds=240)),patch.object(provider,'fetch',return_value=[('1',450),('2',960)]):equal=await self.call(self.lastpath)
  with patch.object(arrivals,'now',return_value=at+timedelta(seconds=241)),patch.object(provider,'fetch') as fetch:changed=await self.call(self.lastpath)
  fetch.assert_not_called();self.assertEqual((equal[0],changed[0]),(200,200))
  old=initial[2]['data']['departure'];d=changed[2]['data']['departure']
  self.assertEqual(equal[2]['data']['departure']['arrival_candidate_id'],old['arrival_candidate_id'])
  self.assertNotEqual(d['arrival_candidate_id'],old['arrival_candidate_id']);self.assertIn('DEPARTURE_UNCONFIRMED_NEXT_VEHICLE',d['reasons'])
  self.assertEqual(d['arrival_evidence']['received_at'],equal[2]['data']['departure']['arrival_evidence']['received_at'])
  self.assertGreater(d['estimated_final_alighting_at'],old['estimated_final_alighting_at'])
 async def test_cancelled_departure_is_not_a_current_suppression_signal(self):
  await self.start();await self.call('/trips/'+self.trip['trip_id']+'/events',await self.event_body());await self.patch_trip(self.trip['trip_id'],1)
  response=await self.call(self.lastpath);self.assertEqual(response[0],200);self.assertEqual(response[2]['data']['departure']['departure_state'],'unconfirmed')
 async def test_departure_recorded_during_provider_query_rejects_numbers_and_anchor_commit(self):
  accepted,m=await self.configured();path=self.path(accepted,2)
  with patch.object(arrivals.public_mapping,'resolve',return_value=m),patch.object(provider,'fetch',return_value=[('1',690)]):initial=await self.call(path)
  gid=initial[2]['data']['departure']['guidance_id'];created=await self.call('/trips',{'guidance_id':gid,'measurement_mode':'assisted'});self.trip=created[2]['data']
  original=selection._states[(str(routine._bindings[accepted[2]['data']['search_id']].user_id),self.rid)].value['anchor'].copy()
  at=arrivals.now()+timedelta(seconds=61)
  def recorded(_):
   with database() as c:
    snap=c.execute('SELECT snapshot FROM guidance_snapshots WHERE id=%s',(gid,)).fetchone()['snapshot']
    c.execute("INSERT INTO manual_trip_events(id,trip_id,client_event_id,body_hash,type,leg_id,source,occurred_at) VALUES(%s,%s,%s,%s,'departed',%s,'manual',clock_timestamp())",(uuid4(),self.trip['trip_id'],uuid4(),'a'*64,snap['candidate']['ordered_legs'][0]['leg_id']))
   return [('1',629)]
  with patch.object(arrivals,'now',return_value=at),patch.object(provider,'fetch',side_effect=recorded):response=await self.call(path)
  self.assertEqual(response[0],409);self.assertEqual(selection._states[(str(routine._bindings[accepted[2]['data']['search_id']].user_id),self.rid)].value['anchor'],original)

del ManualTripTests
