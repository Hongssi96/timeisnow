"""SQL for meetings, members, revisions, invites, idempotency keys and delete jobs."""


def advisory_lock(connection, key):
    connection.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (key,))


def db_now(connection):
    return connection.execute('SELECT now() AS now').fetchone()['now']


def delete_expired_keys(connection):
    connection.execute('DELETE FROM meeting_idempotency_keys WHERE expires_at <= now()')


def delete_expired_jobs(connection):
    connection.execute("DELETE FROM jobs WHERE type='meeting_delete' AND expires_at <= now()")


def find_idempotency_key(connection, user_id, scope, key):
    return connection.execute('SELECT * FROM meeting_idempotency_keys WHERE user_id=%s AND scope=%s AND key=%s',
                              (user_id, scope, key)).fetchone()


def insert_idempotency_key(connection, values):
    connection.execute("INSERT INTO meeting_idempotency_keys VALUES(%s,%s,%s,%s,%s,now()+interval '24 hours')", values)


def insert_meeting(connection, values):
    return connection.execute('INSERT INTO meetings(id,user_id,title) VALUES(%s,%s,%s) RETURNING *', values).fetchone()


def insert_member(connection, values):
    return connection.execute("INSERT INTO meeting_members(id,meeting_id,user_id,role) VALUES(%s,%s,%s,%s) RETURNING *",
                              values).fetchone()


def find_meeting(connection, meeting_id):
    return connection.execute('SELECT * FROM meetings WHERE id=%s', (meeting_id,)).fetchone()


def find_meeting_for_update(connection, meeting_id):
    return connection.execute('SELECT * FROM meetings WHERE id=%s FOR UPDATE', (meeting_id,)).fetchone()


def find_member(connection, meeting_id, user_id):
    return connection.execute('SELECT * FROM meeting_members WHERE meeting_id=%s AND user_id=%s',
                              (meeting_id, user_id)).fetchone()


def find_member_with_name(connection, member_id):
    return connection.execute("""SELECT mm.*, u.display_name FROM meeting_members mm JOIN users u ON u.id=mm.user_id
        WHERE mm.id=%s""", (member_id,)).fetchone()


def count_active_members(connection, meeting_id):
    return connection.execute("SELECT count(*) AS count FROM meeting_members WHERE meeting_id=%s AND participation_status='active'",
                              (meeting_id,)).fetchone()['count']


def list_active_members(connection, meeting_ids):
    return connection.execute("""SELECT mm.*, u.display_name FROM meeting_members mm JOIN users u ON u.id=mm.user_id
        WHERE mm.meeting_id = ANY(%s::uuid[]) AND mm.participation_status='active' ORDER BY mm.joined_at, mm.id""",
                              (meeting_ids,)).fetchall()


def find_meeting_created_at(connection, meeting_id, user_id):
    return connection.execute("""SELECT m.created_at FROM meetings m JOIN meeting_members mm ON mm.meeting_id=m.id
        WHERE m.id=%s AND mm.user_id=%s AND mm.participation_status='active'""", (meeting_id, user_id)).fetchone()


def list_meetings(connection, user_id, status, cursor_id, cursor_time, limit):
    return connection.execute("""SELECT m.* FROM meetings m JOIN meeting_members mm ON mm.meeting_id=m.id
        WHERE mm.user_id=%s AND mm.participation_status='active'
        AND (%s::text IS NULL OR m.status=%s)
        AND (%s::uuid IS NULL OR (m.created_at,m.id) < (%s::timestamptz,%s::uuid))
        ORDER BY m.created_at DESC, m.id DESC LIMIT %s""",
        (user_id, status, status, cursor_id, cursor_time, cursor_id, limit + 1)).fetchall()


def latest_revision(connection, meeting_id):
    return connection.execute('SELECT * FROM meeting_revisions WHERE meeting_id=%s ORDER BY revision_no DESC LIMIT 1',
                              (meeting_id,)).fetchone()


def latest_revisions(connection, meeting_ids):
    return connection.execute("""SELECT DISTINCT ON (meeting_id) * FROM meeting_revisions WHERE meeting_id = ANY(%s::uuid[])
        ORDER BY meeting_id, revision_no DESC""", (meeting_ids,)).fetchall()


def next_revision_no(connection, meeting_id):
    return connection.execute('SELECT COALESCE(MAX(revision_no),0)+1 AS next FROM meeting_revisions WHERE meeting_id=%s',
                              (meeting_id,)).fetchone()['next']


def insert_revision(connection, values):
    return connection.execute("""INSERT INTO meeting_revisions(id,meeting_id,revision_no,target_arrival_at,timezone,
        destination_snapshot,confirmed_by_member_id) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING *""", values).fetchone()


def update_meeting_title(connection, meeting_id, title):
    return connection.execute("UPDATE meetings SET title=%s, version=version+1, updated_at=now() WHERE id=%s RETURNING *",
                              (title, meeting_id)).fetchone()


def confirm_meeting(connection, meeting_id):
    return connection.execute("UPDATE meetings SET status='confirmed', version=version+1, updated_at=now() WHERE id=%s RETURNING *",
                              (meeting_id,)).fetchone()


def close_meeting(connection, meeting_id, status):
    return connection.execute("""UPDATE meetings SET status=%s, closed_at=now(), version=version+1, updated_at=now()
        WHERE id=%s RETURNING *""", (status, meeting_id)).fetchone()


def bump_meeting_version(connection, meeting_id):
    return connection.execute('UPDATE meetings SET version=version+1, updated_at=now() WHERE id=%s RETURNING *',
                              (meeting_id,)).fetchone()


def delete_meeting(connection, meeting_id):
    connection.execute('DELETE FROM meetings WHERE id=%s', (meeting_id,))


def revoke_active_invites(connection, meeting_id):
    connection.execute("""UPDATE meeting_invites SET revoked_at=now() WHERE meeting_id=%s
        AND revoked_at IS NULL AND accepted_at IS NULL AND expires_at > now()""", (meeting_id,))


def find_active_invite(connection, meeting_id):
    return connection.execute("""SELECT * FROM meeting_invites WHERE meeting_id=%s
        AND revoked_at IS NULL AND accepted_at IS NULL AND expires_at > now()""", (meeting_id,)).fetchone()


def insert_invite(connection, values):
    return connection.execute("INSERT INTO meeting_invites(id,meeting_id,inviter_member_id,token_hash,expires_at) "
                              "VALUES(%s,%s,%s,%s, now() + interval '24 hours') RETURNING *", values).fetchone()


def find_invite(connection, meeting_id, invite_id):
    return connection.execute('SELECT * FROM meeting_invites WHERE meeting_id=%s AND id=%s', (meeting_id, invite_id)).fetchone()


def find_invite_by_token(connection, token_hash):
    return connection.execute('SELECT * FROM meeting_invites WHERE token_hash=%s', (token_hash,)).fetchone()


def consume_invite(connection, invite_id, user_id):
    return connection.execute('UPDATE meeting_invites SET accepted_by_user_id=%s, accepted_at=now() WHERE id=%s RETURNING *',
                              (user_id, invite_id)).fetchone()


def revoke_invite(connection, invite_id):
    return connection.execute('UPDATE meeting_invites SET revoked_at=now() WHERE id=%s RETURNING *', (invite_id,)).fetchone()


def reactivate_member(connection, member_id):
    return connection.execute("""UPDATE meeting_members SET participation_status='active', left_at=NULL, version=version+1
        WHERE id=%s RETURNING *""", (member_id,)).fetchone()


def leave_member(connection, member_id):
    return connection.execute("""UPDATE meeting_members SET participation_status='left', left_at=now(), version=version+1
        WHERE id=%s RETURNING *""", (member_id,)).fetchone()


def insert_job(connection, values):
    return connection.execute("INSERT INTO jobs(id,user_id,type,expires_at) VALUES(%s,%s,'meeting_delete',now()+interval '24 hours') "
                              "RETURNING *", values).fetchone()


def finish_job(connection, job_id):
    return connection.execute("UPDATE jobs SET status='succeeded', finished_at=now() WHERE id=%s RETURNING *", (job_id,)).fetchone()


def find_job(connection, job_id, user_id):
    return connection.execute("SELECT * FROM jobs WHERE id=%s AND user_id=%s AND type='meeting_delete'",
                              (job_id, user_id)).fetchone()
