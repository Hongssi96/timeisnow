"""SQL for auth sessions, rate-limit buckets and member records."""


def find_session(connection, token_hash):
    return connection.execute('''SELECT s.*, u.status FROM auth_sessions s
        LEFT JOIN users u ON u.id=s.user_id WHERE token_hash=%s FOR UPDATE OF s''',
        (token_hash,)).fetchone()


def insert_session(connection, token_hash, user_id, csrf_token_hash, expiry, idle):
    connection.execute('INSERT INTO auth_sessions VALUES(%s,%s,%s,%s,%s)',
                       (token_hash, user_id, csrf_token_hash, expiry, idle))


def update_session_csrf(connection, token_hash, csrf_token_hash):
    connection.execute('UPDATE auth_sessions SET csrf_token_hash=%s WHERE token_hash=%s',
                       (csrf_token_hash, token_hash))


def extend_session(connection, token_hash):
    connection.execute('''UPDATE auth_sessions SET idle_expires_at=LEAST(absolute_expires_at,now()+interval '24 hours')
        WHERE token_hash=%s''', (token_hash,))


def delete_session(connection, token_hash):
    connection.execute('DELETE FROM auth_sessions WHERE token_hash=%s', (token_hash,))


def delete_expired_sessions(connection):
    connection.execute('DELETE FROM auth_sessions WHERE idle_expires_at <= now() OR absolute_expires_at <= now()')


def delete_expired_buckets(connection):
    connection.execute('DELETE FROM auth_rate_limit_buckets WHERE expires_at <= now()')


def find_credential(connection, email):
    return connection.execute('''SELECT c.*,u.status FROM auth_credentials c
        JOIN users u ON u.id=c.user_id WHERE email_normalized=%s''', (email,)).fetchone()


def find_display_name(connection, user_id):
    return connection.execute('SELECT display_name FROM users WHERE id=%s', (user_id,)).fetchone()


def find_profile(connection, user_id):
    return connection.execute('SELECT * FROM user_profiles WHERE user_id=%s', (user_id,)).fetchone()


def insert_user(connection, user_id, display_name):
    connection.execute('INSERT INTO users(id,display_name) VALUES(%s,%s)', (user_id, display_name))


def insert_credential(connection, user_id, email, password_hash):
    connection.execute('INSERT INTO auth_credentials VALUES(%s,%s,%s)',
                       (user_id, email, password_hash))


def insert_profile(connection, user_id):
    connection.execute('INSERT INTO user_profiles(user_id) VALUES(%s)', (user_id,))


def update_profile(connection, user_id, values):
    return connection.execute('''UPDATE user_profiles SET walking_preference=%s,
        first_boarding_buffer_seconds=%s,transfer_buffer_seconds=%s,route_preference=%s,
        version=version+1 WHERE user_id=%s RETURNING *''',
        (values['walking_preference'],values['first_boarding_buffer_seconds'],
         values['transfer_buffer_seconds'],values['route_preference'],user_id)).fetchone()


def clock_now(connection):
    return connection.execute('SELECT clock_timestamp() AS now').fetchone()['now']


def ensure_bucket(connection, scope, key, start, expiry):
    connection.execute('''INSERT INTO auth_rate_limit_buckets VALUES(%s,%s,%s,0,%s)
        ON CONFLICT DO NOTHING''', (scope, key, start, expiry))


def bucket_count(connection, scope, key, start):
    return connection.execute('''SELECT count FROM auth_rate_limit_buckets
        WHERE scope=%s AND key_hash=%s AND window_start=%s FOR UPDATE''', (scope, key, start)).fetchone()


def increment_bucket(connection, key):
    connection.execute('''UPDATE auth_rate_limit_buckets SET count=count+1
        WHERE scope=%s AND key_hash=%s AND window_start=%s''', key)
