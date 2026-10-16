"""Real isolated DB/auth retention, rebuild, rollback and worker integration."""
import asyncio,io,json,unittest
from contextlib import redirect_stdout
from uuid import uuid4
from unittest.mock import patch
import test_personalization as personal
from app.common.database import database
from app.personalization import derived
from app.retention import service as retention
from app.ai import provider as ai
from app.guidance import walk_provider

class RetentionTests(unittest.IsolatedAsyncioTestCase):
 async def learned(self,n=5):
  await self.fixture();self.ids=[]
  for _ in range(n):
   tid=self.observation();self.ids.append(tid);self.assertEqual((await self.learn(tid))[0],201)
  self.before=(await self.call('/me/personalization'))[2]['data']
 def expire(self,tid,snapshot=False):
  with database() as c:
   if snapshot:c.execute("UPDATE guidance_snapshots SET expires_at=clock_timestamp()-interval '1 second' WHERE id=(SELECT guidance_id FROM manual_trips WHERE id=%s)",(tid,))
   else:c.execute("UPDATE walking_learning_observations SET expires_at=clock_timestamp()-interval '1 second' WHERE trip_id=%s",(tid,))
 def stats(self):
  with database() as c:
   return {t:c.execute('SELECT count(*) AS n FROM '+t+' WHERE user_id=%s',(self.owner,)).fetchone()['n'] for t in ('walking_learning_updates','walking_estimate_revisions','walking_learning_observations')}
 async def test_expired_valid_sample_rebuilds_before_me_and_refreshes_once(self):
  await self.learned();self.expire(self.ids[-1]);before=self.stats()
  with patch.object(ai,'fetch_estimate') as model,patch.object(walk_provider,'fetch') as maps:
   me=await self.call('/me');self.assertEqual(me[0],200)
   self.assertEqual(me[2]['data']['profile']['walking_duration_factor'],1)
   one=(await self.call('/me/personalization'))[2]['data'];two=(await self.call('/me/personalization'))[2]['data']
   departure=(await self.call(self.path(self.accepted)))[2]['data']['departure']
   self.assertEqual(departure['approach_seconds'],436)
   self.assertEqual(departure['personal_walk']['profile_version'],one['profile_version'])
  self.assertEqual(one,two);self.assertEqual(one['profile_version'],self.before['profile_version']+1)
  self.assertEqual(one['sample_counts']['valid'],4);self.assertFalse(one['can_restore']);model.assert_not_called();maps.assert_not_called()
  after=self.stats();self.assertEqual(after['walking_learning_updates'],before['walking_learning_updates']+1)
  self.assertEqual(after['walking_estimate_revisions'],before['walking_estimate_revisions']+1)
  with database() as c:
   latest=c.execute('SELECT estimated_seconds FROM walking_estimate_revisions WHERE user_id=%s ORDER BY calculated_at DESC LIMIT 1',(self.owner,)).fetchone()
  self.assertEqual(latest['estimated_seconds'],436)
 async def test_six_to_five_rebuild_and_missing_historical_reference(self):
  await self.learned(6);self.expire(self.ids[-1]);one=(await self.call('/me/personalization'))[2]['data']
  self.assertEqual(one['sample_counts']['valid'],5);self.assertAlmostEqual(one['factors'][0]['value'],1.04)
  with database() as c:
   c.execute('DELETE FROM walking_learning_observations WHERE trip_id=%s',(self.ids[0],))
  two=(await self.call('/me/personalization'))[2]['data'];self.assertEqual(two['factors'][0]['value'],1)
  with database() as c:
   refs=c.execute('SELECT sample_ids FROM walking_learning_updates WHERE user_id=%s',(self.owner,)).fetchall()
   valid={str(r['id']) for r in c.execute('SELECT id FROM walking_learning_observations WHERE user_id=%s',(self.owner,))}
  self.assertTrue(all(set(r['sample_ids'])<=valid for r in refs))
 async def test_snapshot_expiry_removes_event_audit_and_raw_retry_copies(self):
  await self.learned();tid=self.ids[-1]
  from app.trips import record_repository as records
  from psycopg.types.json import Jsonb
  with database() as c:
   event=c.execute('SELECT * FROM manual_trip_events WHERE trip_id=%s LIMIT 1',(tid,)).fetchone()
   records.edit(c,event,event['occurred_at'],True,'learning_exclusion')
   c.execute("INSERT INTO trip_record_mutations(user_id,request_id,trip_id,kind,body_hash,response) VALUES(%s,%s,%s,'event',%s,%s)",(self.owner,uuid4(),tid,'0'*64,Jsonb({'private':'expired-event-copy'})))
   c.execute('INSERT INTO manual_trip_creation_keys VALUES(%s,%s,%s,%s,clock_timestamp()+interval \'1 hour\')',(self.owner,'expired-key','0'*64,tid))
  self.expire(tid,True);result=await self.call('/trips/'+tid);self.assertEqual(result[0],404)
  with database() as c:
   for table in ('manual_trips','walking_learning_observations','trip_record_mutations','manual_trip_creation_keys'):
    field='id' if table=='manual_trips' else 'trip_id'
    self.assertEqual(c.execute('SELECT count(*) AS n FROM '+table+' WHERE '+field+'=%s',(tid,)).fetchone()['n'],0)
   self.assertEqual(c.execute('SELECT count(*) AS n FROM trip_event_corrections').fetchone()['n'],0)
  job=(await self.call('/trip-exports',{'format':'json'}))[2]['data']
  result=await self.call(job['result_ref'].removeprefix('/api/v1'))
  self.assertNotIn(tid,[r['trip_id'] for r in result[2]['data']['records']])
 async def test_expired_excluded_and_metadata_do_not_change_factor(self):
  await self.learned();bad=self.observation(delayed=True);await self.learn(bad);self.expire(bad)
  before=self.stats();one=(await self.call('/me/personalization'))[2]['data']
  self.assertEqual(one['profile_version'],self.before['profile_version']);self.assertEqual(one['factors'],self.before['factors'])
  self.assertEqual(self.stats()['walking_estimate_revisions'],before['walking_estimate_revisions'])
 async def test_expired_previous_generation_cannot_resurrect_or_restore(self):
  await self.learned();body={'expected_version':self.before['profile_version'],'client_request_id':str(uuid4())}
  reset=await self.call('/me/personalization/reset',body);self.assertEqual(reset[0],200)
  with database() as c:generation=c.execute('SELECT generation FROM walking_learning_state WHERE user_id=%s',(self.owner,)).fetchone()['generation']
  self.expire(self.ids[-1]);one=(await self.call('/me/personalization'))[2]['data']
  self.assertEqual(one['factors'][0]['value'],1);self.assertFalse(one['can_restore']);self.assertEqual(one['sample_counts']['valid'],0)
  with database() as c:self.assertEqual(c.execute('SELECT generation FROM walking_learning_state WHERE user_id=%s',(self.owner,)).fetchone()['generation'],generation)
  body.update(expected_version=one['profile_version'],client_request_id=str(uuid4()))
  self.assertEqual((await self.call('/me/personalization/restore',body))[2]['error']['code'],'RESTORE_UNAVAILABLE')
 async def test_unauthorized_requests_do_not_sweep_and_failure_rolls_back(self):
  await self.learned();self.expire(self.ids[-1]);before=self.stats();cookie=self.cookie;self.cookie=None
  self.assertEqual((await self.call('/me'))[0],401);self.assertEqual(self.stats(),before);self.cookie=cookie
  self.assertEqual((await self.call('/trip-exports',{'format':'json'},csrf=False))[0],403);self.assertEqual(self.stats(),before)
  with patch.object(derived,'recalculate',side_effect=RuntimeError('synthetic failure')):
   self.assertEqual((await self.call('/me/personalization'))[0],500)
  self.assertEqual(self.stats(),before)
  self.assertEqual((await self.call('/me/personalization'))[2]['data']['factors'][0]['value'],1)
 async def test_parallel_admin_and_requests_rebuild_once(self):
  await self.learned();self.expire(self.ids[-1]);before=self.stats()
  results=await asyncio.gather(asyncio.to_thread(retention.run_all),self.call('/me/personalization'),self.call('/me'))
  self.assertEqual(results[0]['failed'],0);self.assertEqual(results[1][0],200);self.assertEqual(results[2][0],200)
  self.assertEqual(self.stats()['walking_learning_updates'],before['walking_learning_updates']+1)
 async def test_expired_base_removed_and_never_recalculated(self):
  await self.learned()
  with database() as c:
   c.execute("UPDATE walking_paths SET calculated_at=clock_timestamp()-interval '2 days',retained_until=clock_timestamp()-interval '1 second' WHERE user_id=%s",(self.owner,))
  result=(await self.call('/me/personalization'))[2]['data'];self.assertEqual(result['factors'][0]['value'],1)
  self.assertEqual(result['sample_counts']['valid'],0)
  with database() as c:
   self.assertEqual(c.execute('SELECT count(*) AS n FROM walking_paths WHERE user_id=%s',(self.owner,)).fetchone()['n'],0)
   self.assertEqual(c.execute('SELECT count(*) AS n FROM walking_estimate_revisions WHERE user_id=%s',(self.owner,)).fetchone()['n'],0)
 async def test_worker_failure_isolated_and_only_aggregate_output(self):
  await self.learned();self.expire(self.ids[-1]);other=uuid4();before=self.stats()
  with database() as c:
   c.execute("INSERT INTO users(id,display_name) VALUES(%s,'other fixture')",(other,));c.execute('INSERT INTO user_profiles(user_id) VALUES(%s)',(other,))
   c.execute("INSERT INTO trip_exports(id,user_id,range_from,range_to,expires_at) VALUES(%s,%s,clock_timestamp()-interval '1 day',clock_timestamp(),clock_timestamp()-interval '1 second')",(uuid4(),other))
  original=retention.sweep
  def fail_owner(c,owner):
   result=original(c,owner)
   if owner==self.owner:raise RuntimeError('private must not log')
   return result
  with patch.object(retention,'sweep',side_effect=fail_owner):result=retention.run_all()
  self.assertEqual(result,{'checked':2,'changed':1,'rebuilt':0,'failed':1});self.assertEqual(self.stats(),before)
  with database() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM trip_exports WHERE user_id=%s',(other,)).fetchone()['n'],0)
  with patch.object(retention,'run_all',return_value=result),redirect_stdout(io.StringIO()) as output:
   async with retention.lifespan(None):await asyncio.sleep(.03)
  self.assertIn('retention.sweep.completed',output.getvalue());self.assertNotIn(str(self.owner),output.getvalue());self.assertNotIn('private',output.getvalue())
 async def test_orphan_raw_mutation_cleaned_but_delete_receipt_replay_retained(self):
  await self.fixture()
  from psycopg.types.json import Jsonb
  with database() as c:
   for kind in ('event','delete'):
    c.execute('INSERT INTO trip_record_mutations(user_id,request_id,trip_id,kind,body_hash,response) VALUES(%s,%s,%s,%s,%s,%s)',
      (self.owner,uuid4(),uuid4(),kind,'0'*64,Jsonb({'kind':kind})))
   version=c.execute('SELECT version FROM user_profiles WHERE user_id=%s',(self.owner,)).fetchone()['version']
  self.assertEqual((await self.call('/me'))[0],200)
  with database() as c:
   self.assertEqual([r['kind'] for r in c.execute('SELECT kind FROM trip_record_mutations WHERE user_id=%s',(self.owner,))],['delete'])
   self.assertEqual(c.execute('SELECT version FROM user_profiles WHERE user_id=%s',(self.owner,)).fetchone()['version'],version)

for name,value in personal.PersonalizationTests.__dict__.items():
 if not name.startswith('test_') and not name.startswith('__'):setattr(RetentionTests,name,value)
