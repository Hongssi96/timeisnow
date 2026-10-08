"""SQL for saved places, searches, confirmations, creation keys and routine linkage."""


def advisory_lock(connection, key):
    connection.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (key,))


def delete_expired_confirmations(connection):
    connection.execute('DELETE FROM place_location_confirmations WHERE expires_at <= now()')


def insert_confirmation(connection, confirmation_id, user_id, latitude, longitude, address, expires):
    connection.execute('INSERT INTO place_location_confirmations VALUES(%s,%s,%s,%s,%s,%s)',
                       (confirmation_id, user_id, latitude, longitude, address, expires))


def find_confirmation(connection, user_id, confirmation_id):
    return connection.execute('''SELECT * FROM place_location_confirmations
        WHERE id=%s AND user_id=%s AND expires_at > now()''', (confirmation_id, user_id)).fetchone()


def delete_expired_searches(connection):
    connection.execute('DELETE FROM place_searches WHERE expires_at <= now()')


def insert_search(connection, search_id, user_id, candidates, expires):
    connection.execute('INSERT INTO place_searches VALUES(%s,%s,%s,%s)',
                       (search_id, user_id, candidates, expires))


def find_search(connection, search_id, user_id):
    return connection.execute('SELECT candidates FROM place_searches WHERE id=%s AND user_id=%s AND expires_at > now()',
                              (search_id, user_id)).fetchone()


def delete_expired_creation_keys(connection):
    connection.execute('DELETE FROM place_creation_keys WHERE expires_at <= now()')


def find_creation_key(connection, user_id, key):
    return connection.execute('SELECT * FROM place_creation_keys WHERE user_id=%s AND key=%s', (user_id, key)).fetchone()


def insert_creation_key(connection, user_id, key, fingerprint, place_id):
    connection.execute("INSERT INTO place_creation_keys VALUES(%s,%s,%s,%s,now()+interval '24 hours')",
                       (user_id, key, fingerprint, place_id))


def find_place(connection, place_id, user_id):
    return connection.execute('SELECT * FROM saved_places WHERE id=%s AND user_id=%s', (place_id, user_id)).fetchone()


def find_place_for_update(connection, place_id, user_id):
    return connection.execute('SELECT * FROM saved_places WHERE id=%s AND user_id=%s FOR UPDATE',
                              (place_id, user_id)).fetchone()


def find_place_id(connection, place_id, user_id):
    return connection.execute('SELECT id FROM saved_places WHERE id=%s AND user_id=%s', (place_id, user_id)).fetchone()


def insert_place(connection, values):
    return connection.execute('''INSERT INTO saved_places(id,user_id,label,name,address,latitude,longitude,entrance_note,location_source,location_address)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *''', values).fetchone()


def update_place(connection, values):
    return connection.execute('''UPDATE saved_places SET latitude=%s,longitude=%s,location_source=%s,
        location_address=%s,entrance_note=%s,label=%s,version=version+1,
        location_version=location_version+%s,updated_at=now()
        WHERE id=%s AND user_id=%s RETURNING *''', values).fetchone()


def delete_place(connection, place_id, user_id):
    connection.execute('DELETE FROM saved_places WHERE id=%s AND user_id=%s', (place_id, user_id))


def list_places(connection, user_id, cursor_id, limit):
    return connection.execute('''SELECT * FROM saved_places WHERE user_id=%s
        AND (%s::uuid IS NULL OR id < %s::uuid) ORDER BY id DESC LIMIT %s''',
        (user_id, cursor_id, cursor_id, limit + 1)).fetchall()


def mark_routines_needs_attention(connection, user_id, place_id):
    connection.execute('''UPDATE routines SET status='needs_attention',
        version=version+1,updated_at=now()
        WHERE user_id=%s AND (origin_place_id=%s OR destination_place_id=%s)''',
        (user_id, place_id, place_id))


def detach_routines_from_place(connection, user_id, place_id):
    connection.execute('''UPDATE routines SET
        origin_place_id=CASE WHEN origin_place_id=%s THEN NULL ELSE origin_place_id END,
        destination_place_id=CASE WHEN destination_place_id=%s THEN NULL ELSE destination_place_id END,
        status='needs_attention', version=version+1, updated_at=now()
        WHERE user_id=%s AND (origin_place_id=%s OR destination_place_id=%s)''',
        (place_id, place_id, user_id, place_id, place_id))
