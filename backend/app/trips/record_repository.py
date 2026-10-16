"""Owned event edits and 24-hour minimal retry receipts."""
from uuid import uuid4
from psycopg.types.json import Jsonb

def receipt(c,owner,rid):
    c.execute('DELETE FROM trip_record_mutations WHERE user_id=%s AND expires_at<=clock_timestamp()',(owner,))
    return c.execute('SELECT * FROM trip_record_mutations WHERE user_id=%s AND request_id=%s',(owner,rid)).fetchone()

def save_receipt(c,owner,rid,trip,kind,digest,value,guidance=None):
    c.execute('INSERT INTO trip_record_mutations(user_id,request_id,trip_id,guidance_id,kind,body_hash,response) VALUES(%s,%s,%s,%s,%s,%s,%s)',
      (owner,rid,trip,guidance,kind,digest,Jsonb(value)))

def was_deleted(c,owner,guidance):
    return c.execute("SELECT 1 FROM trip_record_mutations WHERE user_id=%s AND guidance_id=%s AND kind='delete' AND expires_at>clock_timestamp()",(owner,guidance)).fetchone() is not None

def edit(c,event,occurred,excluded,reason):
    from app.trips.service import event_data
    row=c.execute('UPDATE manual_trip_events SET occurred_at=%s,excluded=%s,version=version+1 WHERE id=%s RETURNING *',(occurred,excluded,event['id'])).fetchone()
    c.execute('INSERT INTO trip_event_corrections(id,event_id,previous_value,new_value,reason) VALUES(%s,%s,%s,%s,%s)',
      (uuid4(),event['id'],Jsonb(event_data(event)),Jsonb(event_data(row)),reason))
    return row

def bump(c,tid):return c.execute('UPDATE manual_trips SET version=version+1 WHERE id=%s RETURNING version',(tid,)).fetchone()['version']

def corrections(c,tid):
    return c.execute('''SELECT h.id,h.reason,h.previous_value,h.new_value,h.created_at FROM trip_event_corrections h
      JOIN manual_trip_events e ON e.id=h.event_id WHERE e.trip_id=%s ORDER BY h.created_at DESC,h.id DESC LIMIT 50''',(tid,)).fetchall()

def remove(c,owner,trip):
    # Raw correction responses must disappear together with the deleted events.
    c.execute('DELETE FROM trip_record_mutations WHERE user_id=%s AND trip_id=%s',(owner,trip['id']))
    c.execute('DELETE FROM manual_trip_creation_keys WHERE user_id=%s AND trip_id=%s',(owner,trip['id']))
    c.execute('''UPDATE walking_learning_updates SET sample_ids=COALESCE((SELECT jsonb_agg(s) FROM jsonb_array_elements(sample_ids) s
      WHERE s#>>'{}' NOT IN(SELECT id::text FROM walking_learning_observations WHERE user_id=%s AND trip_id=%s)),'[]')
      WHERE user_id=%s''',(owner,trip['id'],owner))
    c.execute('DELETE FROM guidance_snapshots WHERE id=%s AND user_id=%s',(trip['guidance_id'],owner))
