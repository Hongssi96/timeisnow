"""SQL for private timers and explicit per-route selections."""
from psycopg.types.json import Jsonb

def rows(c,owner,*,trip=None,context=None):
    return c.execute('''SELECT m.*,a.occurred_at AS anchor_at,a.excluded AS anchor_excluded,
      r.occurred_at AS ready_at,r.received_at AS ready_received_at,r.excluded AS ready_excluded
      FROM walking_segment_measurements m
      LEFT JOIN manual_trip_events a ON a.id=m.anchor_event_id
      LEFT JOIN manual_trip_events r ON r.id=m.ready_event_id
      JOIN manual_trips t ON t.id=m.trip_id JOIN guidance_snapshots g ON g.id=t.guidance_id
      WHERE m.user_id=%s AND m.expires_at>clock_timestamp() AND t.expires_at>clock_timestamp() AND g.expires_at>clock_timestamp()
      AND (%s::uuid IS NULL OR m.trip_id=%s) AND (%s::text IS NULL OR m.context_key=%s)
      ORDER BY m.start_received_at DESC,m.id DESC''',(owner,trip,trip,context,context)).fetchall()

def start_request(c,owner,rid):
    return c.execute('SELECT * FROM walking_segment_measurements WHERE user_id=%s AND start_request_id=%s AND expires_at>clock_timestamp()',(owner,rid)).fetchone()

def same(c,owner,tid,kind,leg):
    return c.execute('SELECT 1 FROM walking_segment_measurements WHERE user_id=%s AND trip_id=%s AND kind=%s AND leg_id=%s',(owner,tid,kind,leg)).fetchone()

def insert(c,values):
    c.execute('''INSERT INTO walking_segment_measurements(id,user_id,trip_id,kind,leg_id,context_key,label,generation,
      start_request_id,start_hash,anchor_event_id,started_at,predicted_seconds,predicted_arrival_at,expires_at)
      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',values)

def finish(c,identifier,event,body):
    c.execute('''UPDATE walking_segment_measurements SET ready_event_id=%s,finished_at=%s,finish_received_at=clock_timestamp(),
      same_scope=%s,condition=%s,apply_to_guidance=%s,version=version+1 WHERE id=%s''',
      (event['id'],event['occurred_at'],body.same_scope,body.condition,body.apply_to_guidance,identifier))

def exclude(c,identifier,value):
    c.execute('UPDATE walking_segment_measurements SET excluded=%s,version=version+1 WHERE id=%s',(value,identifier))

def selected(c,owner,key):
    row=c.execute('SELECT label FROM walking_segment_selections WHERE user_id=%s AND context_key=%s',(owner,key)).fetchone()
    return row['label'] if row else None

def select(c,owner,key,label):
    c.execute('''INSERT INTO walking_segment_selections VALUES(%s,%s,%s)
      ON CONFLICT(user_id,context_key) DO UPDATE SET label=excluded.label''',(owner,key,label))

def generation(c,owner):
    row=c.execute('SELECT generation FROM walking_learning_state WHERE user_id=%s',(owner,)).fetchone()
    return row['generation'] if row else 1

def clean(c,owner):
    c.execute('DELETE FROM walking_segment_measurements WHERE user_id=%s AND expires_at<=clock_timestamp()',(owner,))
    c.execute('''DELETE FROM trip_record_mutations r WHERE r.user_id=%s AND r.kind='segment' AND NOT EXISTS(
      SELECT 1 FROM walking_segment_measurements m WHERE m.user_id=r.user_id AND m.id::text=r.response->>'measurement_id')''',(owner,))
    c.execute('''DELETE FROM walking_segment_selections s WHERE user_id=%s AND NOT EXISTS(
      SELECT 1 FROM walking_segment_measurements m WHERE m.user_id=s.user_id AND m.context_key=s.context_key AND m.expires_at>clock_timestamp())''',(owner,))
