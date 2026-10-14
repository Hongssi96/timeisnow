"""Meeting core: appointments, members, revisions, invites, idempotency keys and delete jobs."""
from alembic import op

revision = '0013_meeting_core'
down_revision = '0012_departure_profile'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
    CREATE TABLE meetings (
      id uuid PRIMARY KEY,
      user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      title varchar(100) NOT NULL CHECK(length(btrim(title)) BETWEEN 1 AND 100),
      status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','confirmed','completed','cancelled')),
      max_members smallint NOT NULL DEFAULT 2 CHECK (max_members = 2),
      closed_at timestamptz,
      version integer NOT NULL DEFAULT 1 CHECK (version > 0),
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE meeting_members (
      id uuid PRIMARY KEY,
      meeting_id uuid NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
      user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      role text NOT NULL CHECK (role IN ('organizer','participant')),
      participation_status text NOT NULL DEFAULT 'active' CHECK (participation_status IN ('active','left')),
      version integer NOT NULL DEFAULT 1 CHECK (version > 0),
      joined_at timestamptz NOT NULL DEFAULT now(), left_at timestamptz,
      UNIQUE (meeting_id, user_id));
    CREATE INDEX meeting_members_user_idx ON meeting_members(user_id, participation_status);
    CREATE TABLE meeting_revisions (
      id uuid PRIMARY KEY,
      meeting_id uuid NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
      revision_no integer NOT NULL CHECK (revision_no >= 1),
      target_arrival_at timestamptz NOT NULL,
      timezone text NOT NULL CHECK (timezone = 'Asia/Seoul'),
      destination_snapshot jsonb NOT NULL,
      confirmed_by_member_id uuid NOT NULL REFERENCES meeting_members(id) ON DELETE CASCADE,
      confirmed_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE (meeting_id, revision_no));
    CREATE TABLE meeting_invites (
      id uuid PRIMARY KEY,
      meeting_id uuid NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
      inviter_member_id uuid NOT NULL REFERENCES meeting_members(id) ON DELETE CASCADE,
      token_hash char(64) NOT NULL UNIQUE,
      expires_at timestamptz NOT NULL,
      accepted_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
      accepted_at timestamptz, revoked_at timestamptz,
      created_at timestamptz NOT NULL DEFAULT now());
    CREATE INDEX meeting_invites_meeting_idx ON meeting_invites(meeting_id, created_at DESC);
    CREATE TABLE meeting_idempotency_keys (
      user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      scope varchar(32) NOT NULL CHECK (scope IN ('meeting-create','invite-issue','invite-accept')),
      key varchar(128) NOT NULL, body_hash char(64) NOT NULL,
      meeting_id uuid REFERENCES meetings(id) ON DELETE SET NULL,
      expires_at timestamptz NOT NULL, PRIMARY KEY (user_id, scope, key));
    CREATE INDEX meeting_keys_expiry_idx ON meeting_idempotency_keys(expires_at);
    CREATE TABLE jobs (
      id uuid PRIMARY KEY,
      user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      type text NOT NULL CHECK (type IN ('meeting_delete')),
      status text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','succeeded','failed')),
      result_ref jsonb, error jsonb,
      created_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
      expires_at timestamptz NOT NULL);
    CREATE INDEX jobs_expiry_idx ON jobs(expires_at);
    ''')


def downgrade():
    op.execute('DROP TABLE jobs')
    op.execute('DROP TABLE meeting_idempotency_keys')
    op.execute('DROP TABLE meeting_invites')
    op.execute('DROP TABLE meeting_revisions')
    op.execute('DROP TABLE meeting_members')
    op.execute('DROP TABLE meetings')
