"""SQL for learning; caller holds manual-trip then routine-write owner locks."""
from psycopg.types.json import Jsonb
from app.trips.repository import lock_owner
from app.walking.history_repository import lock

def locked(c,owner):
    lock_owner(c,owner);lock(c,owner)
    c.execute('DELETE FROM walking_learning_observations WHERE user_id=%s AND expires_at<=clock_timestamp()',(owner,))
    c.execute('INSERT INTO walking_learning_state(user_id) VALUES(%s) ON CONFLICT DO NOTHING',(owner,))
    return c.execute('SELECT p.*,s.generation,s.started_at FROM user_profiles p JOIN walking_learning_state s USING(user_id) WHERE user_id=%s FOR UPDATE OF p,s',(owner,)).fetchone()

def current_places(c,owner,refs):
    return all(c.execute('SELECT 1 FROM saved_places WHERE user_id=%s AND id=%s AND location_version=%s FOR SHARE',(owner,r['place_id'],r['location_version'])).fetchone() for r in refs)

def evidence(c,owner,revision):
    return c.execute("""SELECT r.*,p.cache_key,p.place_refs,p.scope,p.evidence
      FROM walking_estimate_revisions r JOIN walking_estimates e ON (e.id,e.user_id)=(r.estimate_id,r.user_id)
      JOIN walking_paths p ON (p.id,p.user_id)=(e.walking_path_id,e.user_id)
      WHERE r.user_id=%s AND r.id=%s AND r.retained_until>clock_timestamp() AND p.retained_until>clock_timestamp()""",(owner,revision)).fetchone()

def previous(c,owner,trip):
    return c.execute('SELECT * FROM walking_learning_observations WHERE user_id=%s AND trip_id=%s',(owner,trip)).fetchone()

def samples(c,owner,generation,path=None):
    return c.execute("""SELECT o.* FROM walking_learning_observations o
      WHERE user_id=%s AND generation=%s AND status='valid' AND expires_at>clock_timestamp()
      AND (%s::text IS NULL OR path_key=%s)
      AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements(o.place_refs) ref
        WHERE NOT EXISTS(SELECT 1 FROM saved_places p WHERE p.user_id=o.user_id
          AND p.id=(ref->>'place_id')::uuid AND p.location_version=(ref->>'location_version')::integer))
      ORDER BY created_at DESC,id DESC LIMIT 20""",(owner,generation,path,path)).fetchall()

def counts(c,owner,generation):
    return c.execute("""SELECT count(*) FILTER(WHERE status='excluded') AS excluded,
      count(*) FILTER(WHERE status='valid' AND NOT EXISTS(
        SELECT 1 FROM jsonb_array_elements(o.place_refs) ref WHERE NOT EXISTS(
          SELECT 1 FROM saved_places p WHERE p.user_id=o.user_id AND p.id=(ref->>'place_id')::uuid
          AND p.location_version=(ref->>'location_version')::integer))) AS valid
      FROM walking_learning_observations o
      WHERE user_id=%s AND generation=%s AND expires_at>clock_timestamp()""",(owner,generation)).fetchone()

def save_samples(c,owner,version,rows,scope):
    c.execute('UPDATE walking_learning_updates SET sample_ids=%s,pool_scope=%s WHERE user_id=%s AND profile_version=%s',
      (Jsonb([str(r['id']) for r in rows]),scope,owner,version))

def last_change(c,owner):
    return c.execute('SELECT * FROM walking_learning_updates WHERE user_id=%s ORDER BY profile_version DESC LIMIT 1',(owner,)).fetchone()

def request(c,owner,rid):
    return c.execute('SELECT * FROM walking_learning_updates WHERE user_id=%s AND request_id=%s',(owner,rid)).fetchone()

def change(c,owner,factor,kind,rid=None,digest=None):
    row=c.execute('UPDATE user_profiles SET walking_duration_factor=%s,version=version+1 WHERE user_id=%s RETURNING version',(factor,owner)).fetchone()
    return row['version']

def save_change(c,values):
    c.execute('INSERT INTO walking_learning_updates(id,user_id,profile_version,previous_factor,factor,kind,request_id,body_hash) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',values)

def save_response(c,owner,rid,value):
    c.execute('UPDATE walking_learning_updates SET response=%s WHERE user_id=%s AND request_id=%s',(Jsonb(value),owner,rid))

def reset_generation(c,owner):
    c.execute('UPDATE walking_learning_state SET generation=generation+1,started_at=clock_timestamp() WHERE user_id=%s',(owner,))

def save_observation(c,values):
    c.execute('''INSERT INTO walking_learning_observations(id,user_id,trip_id,body_hash,generation,path_key,place_refs,
      base_seconds,observed_seconds,predicted_seconds,ratio,status,reasons,response,expires_at)
      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',values)

def observation_response(c,oid,value):
    c.execute('UPDATE walking_learning_observations SET response=%s WHERE id=%s',(Jsonb(value),oid))
