"""SQL boundary for owned immutable guidance and manual sessions."""
from psycopg.types.json import Jsonb

def lock_owner(c,owner):
    c.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('manual-trip:'+str(owner),))

def clean(c,owner):
    c.execute('DELETE FROM manual_trip_creation_keys WHERE user_id=%s AND expires_at<=clock_timestamp()',(owner,))
    c.execute('DELETE FROM guidance_snapshots WHERE user_id=%s AND expires_at<=clock_timestamp()',(owner,))

def retry_key(c,owner,key):
    return c.execute('SELECT * FROM manual_trip_creation_keys WHERE user_id=%s AND key=%s',(owner,key)).fetchone()

def save_key(c,owner,key,digest,trip_id):
    c.execute("INSERT INTO manual_trip_creation_keys VALUES(%s,%s,%s,%s,clock_timestamp()+interval '24 hours')",(owner,key,digest,trip_id))

def same_guidance(c,owner,gid):
    return c.execute('SELECT t.*,g.routine_id,g.meeting_journey_id,g.snapshot FROM manual_trips t JOIN guidance_snapshots g ON g.id=t.guidance_id WHERE t.user_id=%s AND t.guidance_id=%s AND t.expires_at>clock_timestamp()',(owner,gid)).fetchone()

def active(c,owner):
    return c.execute("SELECT id FROM manual_trips WHERE user_id=%s AND status='active' AND expires_at>clock_timestamp()",(owner,)).fetchone()

def selection_observation(c,owner,routine_id):
    return c.execute('''SELECT t.id,t.version,g.snapshot,e.id AS event_id,e.version AS event_version,
      e.source,e.type,e.excluded FROM manual_trips t JOIN guidance_snapshots g ON g.id=t.guidance_id
      LEFT JOIN manual_trip_events e ON e.trip_id=t.id AND e.type='departed'
      WHERE t.user_id=%s AND g.routine_id=%s AND t.status='active'
      AND t.expires_at>clock_timestamp() AND g.expires_at>clock_timestamp()''',(owner,routine_id)).fetchone()

def source(c,owner,binding,search_id):
    row=c.execute('''SELECT r.version AS routine_version,r.status AS routine_status,r.journey_plan_id,
      r.origin_place_id,r.destination_place_id,p.candidate AS plan_candidate,s.candidates,s.place_refs,
      s.status AS search_status,s.expires_at AS search_expires,
      pr.version AS profile_version,pr.walking_duration_factor,pr.first_boarding_buffer_seconds,pr.transfer_buffer_seconds
      FROM routines r JOIN journey_plans p ON p.id=r.journey_plan_id AND p.user_id=r.user_id
      JOIN journey_searches s ON s.id=%s AND s.user_id=r.user_id
      JOIN user_profiles pr ON pr.user_id=r.user_id
      WHERE r.id=%s AND r.user_id=%s FOR SHARE OF r,p,s,pr''',(search_id,binding.routine_id,owner)).fetchone()
    places=[]
    if row:
        for key in ('origin_place_id','destination_place_id'):
            places.append(c.execute('SELECT id,location_version FROM saved_places WHERE id=%s AND user_id=%s FOR SHARE',(row[key],owner)).fetchone())
    return row,places

def meeting_source(c,owner,binding,search_id):
    """The meeting journey, its meeting and the stored search evidence, shared-locked."""
    return c.execute('''SELECT m.version AS meeting_version,m.status AS meeting_status,j.meeting_revision_id,
      j.candidate_id,j.candidate_signature,j.trip_id,s.candidates,s.place_refs,
      s.status AS search_status,s.expires_at AS search_expires,
      pr.version AS profile_version,pr.walking_duration_factor,pr.first_boarding_buffer_seconds,pr.transfer_buffer_seconds
      FROM meeting_journeys j JOIN meeting_members mm ON mm.id=j.member_id AND mm.user_id=%s
      JOIN meetings m ON m.id=mm.meeting_id
      JOIN journey_searches s ON s.id=j.journey_search_id AND s.id=%s AND s.user_id=%s
      JOIN user_profiles pr ON pr.user_id=%s
      WHERE j.id=%s FOR SHARE OF m,j,s,pr''',(owner,search_id,owner,owner,binding.meeting_journey_id)).fetchone()

def find_meeting_trip(c,owner,tid,jid):
    return c.execute('''SELECT t.id FROM manual_trips t JOIN guidance_snapshots g ON g.id=t.guidance_id
      WHERE t.user_id=%s AND t.id=%s AND g.meeting_journey_id=%s''',(owner,tid,jid)).fetchone()

def insert(c,owner,gid,tid,rid,snapshot,mode,meeting_journey_id=None):
    c.execute("INSERT INTO guidance_snapshots(id,user_id,routine_id,meeting_journey_id,snapshot,created_at,expires_at) VALUES(%s,%s,%s,%s,%s,clock_timestamp(),clock_timestamp()+interval '90 days')",(gid,owner,rid,meeting_journey_id,Jsonb(snapshot)))
    c.execute("INSERT INTO manual_trips(id,user_id,guidance_id,measurement_mode,expires_at) SELECT %s,%s,id,%s,expires_at FROM guidance_snapshots WHERE id=%s",(tid,owner,mode,gid))
    if meeting_journey_id is not None:
        c.execute('UPDATE meeting_journeys SET trip_id=%s, updated_at=now() WHERE id=%s',(tid,meeting_journey_id))
    return same_guidance(c,owner,gid)

def owned(c,owner,tid,lock=False):
    return c.execute('SELECT t.*,g.routine_id,g.meeting_journey_id,g.snapshot FROM manual_trips t JOIN guidance_snapshots g ON g.id=t.guidance_id WHERE t.user_id=%s AND t.id=%s AND t.expires_at>clock_timestamp()'+(' FOR UPDATE OF t' if lock else ''),(owner,tid)).fetchone()

def events(c,tid):
    return c.execute('SELECT * FROM manual_trip_events WHERE trip_id=%s ORDER BY received_at,id',(tid,)).fetchall()

def event(c,tid,cid):
    return c.execute('SELECT * FROM manual_trip_events WHERE trip_id=%s AND client_event_id=%s',(tid,cid)).fetchone()

def add_event(c,tid,eid,body,digest,received):
    return c.execute('''INSERT INTO manual_trip_events(id,trip_id,client_event_id,body_hash,type,leg_id,source,occurred_at,received_at)
      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *''',(eid,tid,body.client_event_id,digest,body.type,body.leg_id,body.source,body.occurred_at,received)).fetchone()

def cancel(c,tid):
    c.execute("UPDATE manual_trips SET status='cancelled',version=version+1 WHERE id=%s",(tid,))

def finish(c,tid,status):
    c.execute('UPDATE manual_trips SET status=%s,version=version+1 WHERE id=%s',(status,tid))

def listed(c,owner,rid,status,cursor,limit):
    return c.execute('''SELECT t.*,g.routine_id,g.meeting_journey_id,g.snapshot FROM manual_trips t JOIN guidance_snapshots g ON g.id=t.guidance_id
      WHERE t.user_id=%s AND t.expires_at>clock_timestamp() AND (%s::uuid IS NULL OR g.routine_id=%s)
      AND (%s::text IS NULL OR t.status=%s) AND (%s::uuid IS NULL OR (t.created_at,t.id)<(%s,%s))
      ORDER BY t.created_at DESC,t.id DESC LIMIT %s''',(owner,rid,rid,status,status,cursor['id'] if cursor else None,cursor['created_at'] if cursor else None,cursor['id'] if cursor else None,limit+1)).fetchall()


def meeting_trip_summary(c,meeting_id,member_id):
    row=c.execute("""SELECT t.*,g.meeting_journey_id,g.snapshot FROM manual_trips t
      JOIN guidance_snapshots g ON g.id=t.guidance_id
      JOIN meeting_journeys j ON j.id=g.meeting_journey_id
      JOIN meeting_members mm ON mm.id=j.member_id
      WHERE mm.meeting_id=%s AND mm.id=%s ORDER BY t.created_at DESC,t.id DESC LIMIT 1""",
      (meeting_id,member_id)).fetchone()
    if row is None:
        return None
    events=c.execute('SELECT * FROM manual_trip_events WHERE trip_id=%s ORDER BY occurred_at,id',(row['id'],)).fetchall()
    return {'trip':row,'events':events}
