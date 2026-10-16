"""Exports use real isolated PostgreSQL/auth and synthetic transport, no live providers."""
import json,unittest,asyncio
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from unittest.mock import patch
import test_manual_trips as manual
from test_api_contract import request
from app.common.database import database
from app.trips import export_repository,record_repository

class TripExportTests(unittest.IsolatedAsyncioTestCase):
 async def make_export(self,**body):
  r=await self.call('/trip-exports',{'format':'json',**body})
  self.assertEqual(r[0],202,r[2]);return r[2]['data']
 async def file(self,job):return await self.call(job['result_ref'].removeprefix('/api/v1'))
 async def test_owned_file_job_and_private_projection(self):
  await self.start();await self.call('/trips/'+self.trip['trip_id']+'/events',await self.event_body())
  job=await self.make_export();r=await self.file(job)
  self.assertEqual(r[0],200);self.assertEqual(r[1][b'cache-control'],b'no-store')
  self.assertIn(b'attachment',r[1][b'content-disposition'])
  item=r[2]['data']['records'][0];self.assertEqual(item['trip_id'],self.trip['trip_id']);self.assertEqual(len(item['events']),1)
  self.assertEqual((await self.call('/jobs/'+job['job_id']))[2]['data'],job)
  self.assertEqual((await self.call('/trip-exports/'+job['job_id']))[0],200)
  raw=json.dumps(r[2]);self.assertNotIn('transit_bindings',raw);self.assertNotIn('latitude',raw);self.assertNotIn('body_hash',raw)
  with database() as c:
   columns=c.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='trip_exports'").fetchall()
  self.assertEqual({x['column_name'] for x in columns},{'id','user_id','range_from','range_to','created_at','expires_at','download_expires_at'})
 async def test_auth_csrf_and_foreign_owner_cannot_read_job_or_file(self):
  await self.start();job=await self.make_export()
  self.assertEqual((await self.call('/trip-exports',{'format':'json'},csrf=False))[0],403)
  self.cookie=None;self.assertEqual((await self.file(job))[0],401)
  await self.prepare();await self.call('/auth/register',self.credentials('other@example.invalid'))
  logged=await self.call('/auth/login',{'email':'other@example.invalid','password':self.credentials()['password']})
  self.assertEqual(logged[0],200)
  self.cookie=logged[1][b'set-cookie'].decode().split(';')[0]
  for path in ('/jobs/'+job['job_id'],'/trip-exports/'+job['job_id'],job['result_ref'].removeprefix('/api/v1')):
   self.assertEqual((await self.call(path))[0],404)
 async def test_invalid_window_format_and_full_limit_fail_without_partial_job(self):
  await self.start();now=datetime.now(timezone.utc)
  for b in ({'format':'csv'},{'from':None},{'from':123},{'from':'2026-10-01'},
   {'from':now.isoformat(),'to':(now-timedelta(seconds=1)).isoformat()},
   {'from':(now-timedelta(days=91)).isoformat(),'to':now.isoformat()},{'user_id':str(uuid4())}):
   self.assertEqual((await self.call('/trip-exports',{'format':'json',**b}))[0],422,b)
  with patch.object(export_repository,'rows',return_value=[{}]*501):
   r=await self.call('/trip-exports',{'format':'json'});self.assertEqual(r[2]['error']['code'],'EXPORT_LIMIT_EXCEEDED')
  with database() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM trip_exports').fetchone()['n'],0)
 async def test_empty_window_and_creation_cutoff(self):
  await self.start();now=datetime.now(timezone.utc)
  empty=await self.make_export(**{'from':(now-timedelta(days=2)).isoformat(),'to':(now-timedelta(days=1)).isoformat()})
  self.assertEqual((await self.file(empty))[2]['data']['records'],[])
  job=await self.make_export(**{'from':(now-timedelta(days=1)).isoformat(),'to':(now+timedelta(days=1)).isoformat()})
  with database() as c:c.execute("UPDATE manual_trips SET created_at=clock_timestamp()+interval '1 second'")
  self.assertEqual((await self.file(job))[2]['data']['records'],[])
 async def test_link_ten_minutes_job_twenty_four_hours_and_cleanup(self):
  await self.start();job=await self.make_export()
  with database() as c:c.execute("UPDATE trip_exports SET download_expires_at=clock_timestamp()-interval '1 second'")
  self.assertEqual((await self.file(job))[0],404)
  self.assertIsNone((await self.call('/jobs/'+job['job_id']))[2]['data']['result_ref'])
  with database() as c:c.execute("UPDATE trip_exports SET expires_at=clock_timestamp()-interval '1 second'")
  self.assertEqual((await self.call('/trip-exports/'+job['job_id']))[0],404)
  with database() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM trip_exports').fetchone()['n'],0)
 async def test_current_correction_deletion_and_expiry_reflected_without_stored_copy(self):
  await self.start();await self.call('/trips/'+self.trip['trip_id']+'/events',await self.event_body());job=await self.make_export()
  with database() as c:
   owner=c.execute('SELECT user_id FROM manual_trips WHERE id=%s',(self.trip['trip_id'],)).fetchone()['user_id']
   event=c.execute('SELECT * FROM manual_trip_events WHERE trip_id=%s',(self.trip['trip_id'],)).fetchone()
   record_repository.edit(c,event,event['occurred_at'],True,'learning_exclusion')
  item=(await self.file(job))[2]['data']['records'][0]
  self.assertTrue(item['events'][0]['excluded']);self.assertEqual(item['corrections'][0]['current']['version'],2)
  with database() as c:c.execute("UPDATE manual_trips SET expires_at=clock_timestamp()-interval '1 second'")
  self.assertEqual((await self.file(job))[2]['data']['records'],[])
  with database() as c:c.execute('DELETE FROM guidance_snapshots WHERE id=%s',(self.trip['guidance_id'],))
  self.assertEqual((await self.file(job))[2]['data']['records'],[])
  with database() as c:
   c.execute('DELETE FROM users WHERE id=%s',(owner,))
   self.assertEqual(c.execute('SELECT count(*) AS n FROM trip_exports').fetchone()['n'],0)
 async def test_rate_limit(self):
  await self.start()
  from app.auth import repository as auth_repo
  with patch.object(auth_repo,'clock_now',return_value=datetime.now(timezone.utc)):
   for _ in range(10):await self.make_export()
   self.assertEqual((await self.call('/trip-exports',{'format':'json'}))[0],429)
 async def test_download_waits_for_atomic_deletion(self):
  await self.start();job=await self.make_export()
  from app.trips.repository import lock_owner
  with database() as c:
   owner=c.execute('SELECT user_id FROM manual_trips WHERE id=%s',(self.trip['trip_id'],)).fetchone()['user_id']
   lock_owner(c,owner)
   task=asyncio.create_task(self.file(job));await asyncio.sleep(.15);self.assertFalse(task.done())
   c.execute('DELETE FROM guidance_snapshots WHERE id=%s',(self.trip['guidance_id'],))
  self.assertEqual((await task)[2]['data']['records'],[])
 async def test_actual_five_hundred_limit_and_stable_order(self):
  await self.start()
  with database() as c:
   c.execute('''INSERT INTO guidance_snapshots(id,user_id,routine_id,snapshot,expires_at)
     SELECT gen_random_uuid(),user_id,routine_id,snapshot,expires_at FROM guidance_snapshots CROSS JOIN generate_series(1,499)''')
   c.execute('''INSERT INTO manual_trips(id,user_id,guidance_id,measurement_mode,status,expires_at)
     SELECT gen_random_uuid(),g.user_id,g.id,'assisted','cancelled',g.expires_at FROM guidance_snapshots g
     WHERE NOT EXISTS(SELECT 1 FROM manual_trips t WHERE t.guidance_id=g.id)''')
  job=await self.make_export();records=(await self.file(job))[2]['data']['records']
  self.assertEqual(len(records),500)
  self.assertEqual([(x['created_at'],x['trip_id']) for x in records],sorted((x['created_at'],x['trip_id']) for x in records))
  with database() as c:
   c.execute('''INSERT INTO guidance_snapshots(id,user_id,routine_id,snapshot,expires_at)
     SELECT gen_random_uuid(),user_id,routine_id,snapshot,expires_at FROM guidance_snapshots LIMIT 1''')
   c.execute('''INSERT INTO manual_trips(id,user_id,guidance_id,measurement_mode,status,expires_at)
     SELECT gen_random_uuid(),g.user_id,g.id,'assisted','cancelled',g.expires_at FROM guidance_snapshots g
     WHERE NOT EXISTS(SELECT 1 FROM manual_trips t WHERE t.guidance_id=g.id)''')
  self.assertEqual((await self.call('/trip-exports',{'format':'json'}))[2]['error']['code'],'EXPORT_LIMIT_EXCEEDED')

for name,value in manual.ManualTripTests.__dict__.items():
 if not name.startswith('test_') and not name.startswith('__'):setattr(TripExportTests,name,value)
