"""SQL for journey searches, retry keys and worker bookkeeping."""
from psycopg.types.json import Jsonb


def find_place_version_for_share(connection, place_id, user_id):
    return connection.execute('SELECT location_version FROM saved_places WHERE id=%s AND user_id=%s FOR SHARE',
                              (place_id, user_id)).fetchone()


def find_owned_place_for_share(connection, place_id, user_id):
    return connection.execute('SELECT * FROM saved_places WHERE id=%s AND user_id=%s FOR SHARE',
                              (place_id, user_id)).fetchone()


def admission_lock(connection):
    connection.execute("SELECT pg_advisory_xact_lock(hashtext('journey-admission'))")


def find_search_key(connection, user_id, key):
    return connection.execute('SELECT * FROM journey_search_keys WHERE user_id=%s AND key=%s',(user_id,key)).fetchone()


def insert_search_key(connection, values):
    connection.execute('INSERT INTO journey_search_keys VALUES(%s,%s,%s,%s,%s)',values)


def active_counts(connection, user_id):
    return connection.execute("SELECT count(*) AS total,count(*) FILTER (WHERE user_id=%s) AS owned FROM journey_searches WHERE status IN ('queued','running')",(user_id,)).fetchone()


def find_user_profile_preference(connection, user_id):
    return connection.execute('SELECT route_preference FROM user_profiles WHERE user_id=%s',(user_id,)).fetchone()


def insert_search(connection, values):
    connection.execute('''INSERT INTO journey_searches(id,job_id,user_id,status,place_refs,expires_at,worker_deadline,job_expires_at)
        VALUES(%s,%s,%s,'queued',%s,%s,%s,%s)''',values)


def find_search(connection, search_id, user_id):
    return connection.execute('SELECT * FROM journey_searches WHERE id=%s AND user_id=%s',(search_id,user_id)).fetchone()


def find_search_for_update(connection, search_id):
    return connection.execute('SELECT * FROM journey_searches WHERE id=%s FOR UPDATE',(search_id,)).fetchone()


def find_search_by_column(connection, column, identifier, user_id):
    return connection.execute(f'SELECT * FROM journey_searches WHERE {column}=%s AND user_id=%s',(identifier,user_id)).fetchone()


def claim_queued(connection, search_id):
    return connection.execute("UPDATE journey_searches SET status='running' WHERE id=%s AND status='queued' AND worker_deadline>now() RETURNING *",(search_id,)).fetchone()


def find_user_status(connection, user_id):
    return connection.execute('SELECT status FROM users WHERE id=%s',(user_id,)).fetchone()


def finish_search(connection, values):
    connection.execute('''UPDATE journey_searches SET status=%s,candidates=%s,unavailable_reasons=%s,error=%s,
        finished_at=now(),job_expires_at=now()+interval '24 hours' WHERE id=%s''',values)


def fail_interrupted_workers(connection, error):
    connection.execute("""UPDATE journey_searches SET status='failed',error=%s,finished_at=now(),job_expires_at=now()+interval '24 hours'
        WHERE status IN ('queued','running') AND worker_deadline <= now()""", (error,))


def expire_stored_candidates(connection):
    connection.execute("UPDATE journey_searches SET candidates='[]',unavailable_reasons='[]' WHERE expires_at <= now() AND (candidates <> '[]' OR unavailable_reasons <> '[]')")


def delete_expired_keys(connection):
    connection.execute('DELETE FROM journey_search_keys WHERE expires_at <= now()')


def delete_expired_searches(connection):
    connection.execute('DELETE FROM journey_searches WHERE job_expires_at <= now()')
