"""SQL for routines, journey plans, retry keys and owned search/place reads."""


def advisory_lock(connection, key):
    connection.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (key,))


def delete_expired_creation_keys(connection):
    connection.execute('DELETE FROM routine_creation_keys WHERE expires_at <= now()')


def find_creation_key(connection, user_id, key):
    return connection.execute('SELECT * FROM routine_creation_keys WHERE user_id=%s AND key=%s',
                              (user_id, key)).fetchone()


def insert_creation_key(connection, values):
    connection.execute("INSERT INTO routine_creation_keys VALUES(%s,%s,%s,%s,now()+interval '24 hours')", values)


def find_routine(connection, routine_id, user_id):
    return connection.execute('SELECT * FROM routines WHERE id=%s AND user_id=%s',
                              (routine_id, user_id)).fetchone()


def find_routine_for_update(connection, routine_id, user_id):
    return connection.execute('SELECT * FROM routines WHERE id=%s AND user_id=%s FOR UPDATE',
                              (routine_id, user_id)).fetchone()


def insert_routine(connection, values):
    return connection.execute('''INSERT INTO routines(id,user_id,name,origin_place_id,destination_place_id,journey_plan_id,
        weekdays,target_arrival_local_time)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *''', values).fetchone()


def update_routine(connection, values):
    return connection.execute('''UPDATE routines SET name=%s, weekdays=%s, target_arrival_local_time=%s,
        origin_place_id=%s, destination_place_id=%s, journey_plan_id=%s, status=%s,
        version=version+1, updated_at=now() WHERE id=%s RETURNING *''', values).fetchone()


def delete_routine(connection, routine_id, user_id):
    connection.execute('DELETE FROM routines WHERE id=%s AND user_id=%s', (routine_id, user_id))


def find_routine_created_at(connection, routine_id, user_id):
    return connection.execute('SELECT created_at FROM routines WHERE id=%s AND user_id=%s',
                              (routine_id, user_id)).fetchone()


def list_routines(connection, user_id, cursor_id, cursor_time, limit):
    return connection.execute("""SELECT * FROM routines WHERE user_id=%s
        AND (%s::uuid IS NULL OR (created_at,id) < (%s::timestamptz,%s::uuid))
        ORDER BY created_at DESC,id DESC LIMIT %s""",
        (user_id, cursor_id, cursor_time, cursor_id, limit + 1)).fetchall()


def find_journey_search(connection, search_id, user_id):
    return connection.execute('SELECT * FROM journey_searches WHERE id=%s AND user_id=%s',
                              (search_id, user_id)).fetchone()


def find_owned_place_for_share(connection, place_id, user_id):
    return connection.execute('SELECT * FROM saved_places WHERE id=%s AND user_id=%s FOR SHARE',
                              (place_id, user_id)).fetchone()


def find_owned_place(connection, place_id, user_id):
    return connection.execute('SELECT * FROM saved_places WHERE id=%s AND user_id=%s',
                              (place_id, user_id)).fetchone()


def insert_plan(connection, values):
    connection.execute('''INSERT INTO journey_plans(id,user_id,search_id,candidate_id,candidate,total_seconds,transfer_count,model_version)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (user_id,search_id,candidate_id) DO NOTHING''', values)


def find_plan_for_update(connection, user_id, search_id, candidate_id):
    return connection.execute('SELECT * FROM journey_plans WHERE user_id=%s AND search_id=%s AND candidate_id=%s FOR UPDATE',
                              (user_id, search_id, candidate_id)).fetchone()


def find_plan(connection, plan_id):
    return connection.execute('SELECT * FROM journey_plans WHERE id=%s', (plan_id,)).fetchone()


def lock_plan(connection, plan_id):
    connection.execute('SELECT id FROM journey_plans WHERE id=%s FOR UPDATE', (plan_id,))


def delete_plan_if_unused(connection, plan_id):
    connection.execute('DELETE FROM journey_plans WHERE id=%s AND NOT EXISTS '
                       '(SELECT 1 FROM routines WHERE journey_plan_id=%s)', (plan_id, plan_id))
