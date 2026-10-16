"""Meeting personal flows: member origins, per-member journeys, guidance snapshot links and invite replay cache."""
from alembic import op

revision = '0018_meeting_personal_flows'
down_revision = '0017_trip_outcomes'
branch_labels = None
depends_on = None


def upgrade():
    # pgcrypto is relocatable: pin it to a dedicated schema so every search_path sees it.
    op.execute('CREATE SCHEMA IF NOT EXISTS pgcrypto')
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA pgcrypto')
    op.execute('''
    ALTER TABLE meeting_members
      ADD COLUMN private_origin jsonb,
      ADD COLUMN origin_version integer NOT NULL DEFAULT 0 CHECK (origin_version >= 0),
      ADD COLUMN recommendation_consent boolean NOT NULL DEFAULT false,
      ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now();
    ALTER TABLE meeting_idempotency_keys DROP CONSTRAINT meeting_idempotency_keys_scope_check;
    ALTER TABLE meeting_idempotency_keys ADD CONSTRAINT meeting_idempotency_keys_scope_check
      CHECK (scope IN ('meeting-create','invite-issue','invite-accept','meeting-guidance','meeting-arrival','meeting-correction'));
    CREATE TABLE meeting_journeys (
      id uuid PRIMARY KEY,
      member_id uuid NOT NULL REFERENCES meeting_members(id) ON DELETE CASCADE,
      meeting_revision_id uuid NOT NULL REFERENCES meeting_revisions(id) ON DELETE CASCADE,
      journey_search_id uuid REFERENCES journey_searches(id) ON DELETE SET NULL,
      candidate_id uuid,
      candidate_signature text,
      origin_fingerprint char(64) NOT NULL,
      trip_id uuid REFERENCES manual_trips(id) ON DELETE SET NULL,
      status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','superseded')),
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
    CREATE UNIQUE INDEX meeting_journeys_active_idx
      ON meeting_journeys(member_id, meeting_revision_id) WHERE status = 'active';
    CREATE INDEX meeting_journeys_member_idx ON meeting_journeys(member_id, created_at DESC);
    ALTER TABLE guidance_snapshots
      ADD COLUMN meeting_journey_id uuid REFERENCES meeting_journeys(id) ON DELETE SET NULL;
    ALTER TABLE guidance_snapshots ADD CONSTRAINT guidance_snapshots_owner_check
      CHECK (routine_id IS NULL OR meeting_journey_id IS NULL);
    CREATE TABLE meeting_invite_replays (
      user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      key varchar(128) NOT NULL,
      body_hash char(64) NOT NULL,
      invite_id uuid NOT NULL REFERENCES meeting_invites(id) ON DELETE CASCADE,
      response bytea NOT NULL,
      expires_at timestamptz NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now(),
      PRIMARY KEY (user_id, key));
    CREATE INDEX meeting_replays_expiry_idx ON meeting_invite_replays(expires_at);
    CREATE TABLE meeting_share_events (
      id uuid PRIMARY KEY,
      meeting_id uuid NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
      member_id uuid NOT NULL REFERENCES meeting_members(id) ON DELETE CASCADE,
      meeting_journey_id uuid REFERENCES meeting_journeys(id) ON DELETE SET NULL,
      client_event_id uuid NOT NULL,
      kind text NOT NULL CHECK (kind IN ('arrival','correction')),
      occurred_at timestamptz NOT NULL,
      source text NOT NULL CHECK (source IN ('manual')),
      excluded boolean NOT NULL DEFAULT false,
      correction_reason text CHECK (correction_reason IN ('wrong_time','wrong_action')),
      corrects_event_id uuid REFERENCES meeting_share_events(id),
      version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
      received_at timestamptz NOT NULL DEFAULT now(),
      CONSTRAINT meeting_share_events_client_unique UNIQUE (member_id, client_event_id));
    CREATE INDEX meeting_share_events_member_idx ON meeting_share_events(member_id, received_at DESC);
    ALTER TABLE meeting_members
      ADD COLUMN sharing_enabled boolean NOT NULL DEFAULT false,
      ADD COLUMN sharing_updated_at timestamptz;
    ''')


def downgrade():
    op.execute('''
    DROP TABLE meeting_invite_replays;
    DROP TABLE meeting_share_events;
    ALTER TABLE guidance_snapshots DROP CONSTRAINT guidance_snapshots_owner_check;
    ALTER TABLE guidance_snapshots DROP COLUMN meeting_journey_id;
    DROP TABLE meeting_journeys;
    ALTER TABLE meeting_idempotency_keys DROP CONSTRAINT meeting_idempotency_keys_scope_check;
    ALTER TABLE meeting_idempotency_keys ADD CONSTRAINT meeting_idempotency_keys_scope_check
      CHECK (scope IN ('meeting-create','invite-issue','invite-accept'));
    ALTER TABLE meeting_members
      DROP COLUMN sharing_updated_at,
      DROP COLUMN sharing_enabled,
      DROP COLUMN updated_at,
      DROP COLUMN recommendation_consent,
      DROP COLUMN origin_version,
      DROP COLUMN private_origin;
    DROP EXTENSION IF EXISTS pgcrypto;
    DROP SCHEMA IF EXISTS pgcrypto;
    ''')
