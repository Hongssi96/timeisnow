"""Meeting data access: an abstract port plus the PostgreSQL adapter.

MeetingService는 MeetingRepository(ABC)에만 의존한다. SQL은
PostgresMeetingRepository가 맡고, 테스트는 이 포트를 상속한 메모리
구현체를 주입해 DB 없이 도메인 규칙을 검증할 수 있다.
"""
from abc import ABC, abstractmethod

from psycopg.types.json import Jsonb


class MeetingRepository(ABC):
    """Every call receives the transaction connection as its first argument."""

    @abstractmethod
    def advisory_lock(self, connection, key):
        """Take a transaction-scoped advisory lock."""

    @abstractmethod
    def db_now(self, connection):
        """Database time, the authority for schedule checks."""

    @abstractmethod
    def delete_expired_keys(self, connection):
        """Idempotency keys older than their expiry stop being visible."""

    @abstractmethod
    def delete_expired_jobs(self, connection):
        """Finished or expired meeting jobs are housekept here."""

    @abstractmethod
    def find_idempotency_key(self, connection, user_id, scope, key):
        """The stored replay record for one key, or None."""

    @abstractmethod
    def insert_idempotency_key(self, connection, values):
        """Record (user_id, scope, key, body_hash, meeting_id) for replays."""

    @abstractmethod
    def insert_meeting(self, connection, values):
        """Create the aggregate row; version starts at 1."""

    @abstractmethod
    def insert_member(self, connection, values):
        """Join one user to a meeting with a role."""

    @abstractmethod
    def find_meeting(self, connection, meeting_id):
        """The meeting row, or None when it never existed or was deleted."""

    @abstractmethod
    def find_meeting_for_update(self, connection, meeting_id):
        """The meeting row locked against concurrent writers, or None."""

    @abstractmethod
    def find_member(self, connection, meeting_id, user_id):
        """Membership row including left ones, or None."""

    @abstractmethod
    def find_member_with_name(self, connection, member_id):
        """Membership plus the display name for responses."""

    @abstractmethod
    def count_active_members(self, connection, meeting_id):
        """Active participants; the capacity check for invites."""

    @abstractmethod
    def list_active_members(self, connection, meeting_ids):
        """Active members of the given meetings, joined in order."""

    @abstractmethod
    def find_meeting_created_at(self, connection, meeting_id, user_id):
        """Cursor anchor: created_at of a meeting this user can see."""

    @abstractmethod
    def list_meetings(self, connection, user_id, status, cursor_id, cursor_time, limit):
        """One user's meetings, newest first, up to limit+1 for paging."""

    @abstractmethod
    def latest_revision(self, connection, meeting_id):
        """Highest revision_no row, or None for drafts."""

    @abstractmethod
    def latest_revisions(self, connection, meeting_ids):
        """Latest revision per meeting, one row each."""

    @abstractmethod
    def next_revision_no(self, connection, meeting_id):
        """Sequential confirmation number for this meeting."""

    @abstractmethod
    def insert_revision(self, connection, values):
        """Store one confirmed snapshot; destination is a plain dict here."""

    @abstractmethod
    def update_meeting_title(self, connection, meeting_id, title):
        """Title change bumps the aggregate version."""

    @abstractmethod
    def confirm_meeting(self, connection, meeting_id):
        """draft → confirmed; bumps the aggregate version."""

    @abstractmethod
    def close_meeting(self, connection, meeting_id, status):
        """Move to completed or cancelled; bumps the aggregate version."""

    @abstractmethod
    def bump_meeting_version(self, connection, meeting_id):
        """Membership and invite changes bump the aggregate version too."""

    @abstractmethod
    def delete_meeting(self, connection, meeting_id):
        """Cascade removes members, revisions and invites with it."""

    @abstractmethod
    def revoke_active_invites(self, connection, meeting_id):
        """Re-issue invalidates the previous unused invite."""

    @abstractmethod
    def insert_invite(self, connection, values):
        """Store the hashed token; the raw token never reaches SQL."""

    @abstractmethod
    def find_invite(self, connection, meeting_id, invite_id):
        """Invite of this meeting by id, or None."""

    @abstractmethod
    def find_invite_by_token(self, connection, token_hash):
        """Invite lookup by sha256 hash, or None."""

    @abstractmethod
    def consume_invite(self, connection, invite_id, user_id):
        """Mark accepted so it can never be reused."""

    @abstractmethod
    def revoke_invite(self, connection, invite_id):
        """Organizer-side invalidation."""

    @abstractmethod
    def reactivate_member(self, connection, member_id):
        """A member who left may return through a new invite."""

    @abstractmethod
    def leave_member(self, connection, member_id):
        """Soft-leave keeps history; version protects the caller's view."""

    @abstractmethod
    def insert_job(self, connection, values):
        """Delete requests become jobs even when done synchronously."""

    @abstractmethod
    def finish_job(self, connection, job_id):
        """Record the outcome for the shared /jobs view."""

    @abstractmethod
    def find_job(self, connection, job_id, user_id):
        """Only the owner sees their job; others get None."""


class PostgresMeetingRepository(MeetingRepository):
    def advisory_lock(self, connection, key):
        connection.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (key,))

    def db_now(self, connection):
        return connection.execute('SELECT now() AS now').fetchone()['now']

    def delete_expired_keys(self, connection):
        connection.execute('DELETE FROM meeting_idempotency_keys WHERE expires_at <= now()')

    def delete_expired_jobs(self, connection):
        connection.execute("DELETE FROM jobs WHERE type='meeting_delete' AND expires_at <= now()")

    def find_idempotency_key(self, connection, user_id, scope, key):
        return connection.execute('SELECT * FROM meeting_idempotency_keys WHERE user_id=%s AND scope=%s AND key=%s',
                                  (user_id, scope, key)).fetchone()

    def insert_idempotency_key(self, connection, values):
        connection.execute("INSERT INTO meeting_idempotency_keys VALUES(%s,%s,%s,%s,%s,now()+interval '24 hours')", values)

    def insert_meeting(self, connection, values):
        return connection.execute('INSERT INTO meetings(id,user_id,title) VALUES(%s,%s,%s) RETURNING *', values).fetchone()

    def insert_member(self, connection, values):
        return connection.execute("INSERT INTO meeting_members(id,meeting_id,user_id,role) VALUES(%s,%s,%s,%s) RETURNING *",
                                  values).fetchone()

    def find_meeting(self, connection, meeting_id):
        return connection.execute('SELECT * FROM meetings WHERE id=%s', (meeting_id,)).fetchone()

    def find_meeting_for_update(self, connection, meeting_id):
        return connection.execute('SELECT * FROM meetings WHERE id=%s FOR UPDATE', (meeting_id,)).fetchone()

    def find_member(self, connection, meeting_id, user_id):
        return connection.execute('SELECT * FROM meeting_members WHERE meeting_id=%s AND user_id=%s',
                                  (meeting_id, user_id)).fetchone()

    def find_member_with_name(self, connection, member_id):
        return connection.execute("""SELECT mm.*, u.display_name FROM meeting_members mm JOIN users u ON u.id=mm.user_id
            WHERE mm.id=%s""", (member_id,)).fetchone()

    def count_active_members(self, connection, meeting_id):
        return connection.execute("SELECT count(*) AS count FROM meeting_members WHERE meeting_id=%s AND participation_status='active'",
                                  (meeting_id,)).fetchone()['count']

    def list_active_members(self, connection, meeting_ids):
        return connection.execute("""SELECT mm.*, u.display_name FROM meeting_members mm JOIN users u ON u.id=mm.user_id
            WHERE mm.meeting_id = ANY(%s::uuid[]) AND mm.participation_status='active' ORDER BY mm.joined_at, mm.id""",
                                  (meeting_ids,)).fetchall()

    def find_meeting_created_at(self, connection, meeting_id, user_id):
        return connection.execute("""SELECT m.created_at FROM meetings m JOIN meeting_members mm ON mm.meeting_id=m.id
            WHERE m.id=%s AND mm.user_id=%s AND mm.participation_status='active'""", (meeting_id, user_id)).fetchone()

    def list_meetings(self, connection, user_id, status, cursor_id, cursor_time, limit):
        return connection.execute("""SELECT m.* FROM meetings m JOIN meeting_members mm ON mm.meeting_id=m.id
            WHERE mm.user_id=%s AND mm.participation_status='active'
            AND (%s::text IS NULL OR m.status=%s)
            AND (%s::uuid IS NULL OR (m.created_at,m.id) < (%s::timestamptz,%s::uuid))
            ORDER BY m.created_at DESC, m.id DESC LIMIT %s""",
            (user_id, status, status, cursor_id, cursor_time, cursor_id, limit + 1)).fetchall()

    def latest_revision(self, connection, meeting_id):
        return connection.execute('SELECT * FROM meeting_revisions WHERE meeting_id=%s ORDER BY revision_no DESC LIMIT 1',
                                  (meeting_id,)).fetchone()

    def latest_revisions(self, connection, meeting_ids):
        return connection.execute("""SELECT DISTINCT ON (meeting_id) * FROM meeting_revisions WHERE meeting_id = ANY(%s::uuid[])
            ORDER BY meeting_id, revision_no DESC""", (meeting_ids,)).fetchall()

    def next_revision_no(self, connection, meeting_id):
        return connection.execute('SELECT COALESCE(MAX(revision_no),0)+1 AS next FROM meeting_revisions WHERE meeting_id=%s',
                                  (meeting_id,)).fetchone()['next']

    def insert_revision(self, connection, values):
        # The adapter owns psycopg-specific types; the service passes a plain dict.
        wrapped = values[:5] + (Jsonb(values[5]),) + values[6:]
        return connection.execute("""INSERT INTO meeting_revisions(id,meeting_id,revision_no,target_arrival_at,timezone,
            destination_snapshot,confirmed_by_member_id) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING *""", wrapped).fetchone()

    def update_meeting_title(self, connection, meeting_id, title):
        return connection.execute("UPDATE meetings SET title=%s, version=version+1, updated_at=now() WHERE id=%s RETURNING *",
                                  (title, meeting_id)).fetchone()

    def confirm_meeting(self, connection, meeting_id):
        return connection.execute("UPDATE meetings SET status='confirmed', version=version+1, updated_at=now() WHERE id=%s RETURNING *",
                                  (meeting_id,)).fetchone()

    def close_meeting(self, connection, meeting_id, status):
        return connection.execute("""UPDATE meetings SET status=%s, closed_at=now(), version=version+1, updated_at=now()
            WHERE id=%s RETURNING *""", (status, meeting_id)).fetchone()

    def bump_meeting_version(self, connection, meeting_id):
        return connection.execute('UPDATE meetings SET version=version+1, updated_at=now() WHERE id=%s RETURNING *',
                                  (meeting_id,)).fetchone()

    def delete_meeting(self, connection, meeting_id):
        connection.execute('DELETE FROM meetings WHERE id=%s', (meeting_id,))

    def revoke_active_invites(self, connection, meeting_id):
        connection.execute("""UPDATE meeting_invites SET revoked_at=now() WHERE meeting_id=%s
            AND revoked_at IS NULL AND accepted_at IS NULL AND expires_at > now()""", (meeting_id,))

    def insert_invite(self, connection, values):
        return connection.execute("INSERT INTO meeting_invites(id,meeting_id,inviter_member_id,token_hash,expires_at) "
                                  "VALUES(%s,%s,%s,%s, now() + interval '24 hours') RETURNING *", values).fetchone()

    def find_invite(self, connection, meeting_id, invite_id):
        return connection.execute('SELECT * FROM meeting_invites WHERE meeting_id=%s AND id=%s', (meeting_id, invite_id)).fetchone()

    def find_invite_by_token(self, connection, token_hash):
        return connection.execute('SELECT * FROM meeting_invites WHERE token_hash=%s', (token_hash,)).fetchone()

    def consume_invite(self, connection, invite_id, user_id):
        return connection.execute('UPDATE meeting_invites SET accepted_by_user_id=%s, accepted_at=now() WHERE id=%s RETURNING *',
                                  (user_id, invite_id)).fetchone()

    def revoke_invite(self, connection, invite_id):
        return connection.execute('UPDATE meeting_invites SET revoked_at=now() WHERE id=%s RETURNING *', (invite_id,)).fetchone()

    def reactivate_member(self, connection, member_id):
        return connection.execute("""UPDATE meeting_members SET participation_status='active', left_at=NULL, version=version+1
            WHERE id=%s RETURNING *""", (member_id,)).fetchone()

    def leave_member(self, connection, member_id):
        return connection.execute("""UPDATE meeting_members SET participation_status='left', left_at=now(), version=version+1
            WHERE id=%s RETURNING *""", (member_id,)).fetchone()

    def insert_job(self, connection, values):
        return connection.execute("INSERT INTO jobs(id,user_id,type,expires_at) VALUES(%s,%s,'meeting_delete',now()+interval '24 hours') "
                                  "RETURNING *", values).fetchone()

    def finish_job(self, connection, job_id):
        return connection.execute("UPDATE jobs SET status='succeeded', finished_at=now() WHERE id=%s RETURNING *", (job_id,)).fetchone()

    def find_job(self, connection, job_id, user_id):
        return connection.execute("SELECT * FROM jobs WHERE id=%s AND user_id=%s AND type='meeting_delete'",
                                  (job_id, user_id)).fetchone()
