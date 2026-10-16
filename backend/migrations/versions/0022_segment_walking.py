"""Owned manual segment durations, separate from provider-based walking factors."""
from alembic import op
revision='0022_segment_walking'
down_revision='0021_meeting_flow_merge'
branch_labels=None
depends_on=None

def upgrade():
    op.execute('''CREATE TABLE walking_segment_measurements (
      id uuid PRIMARY KEY,user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      trip_id uuid NOT NULL REFERENCES manual_trips(id) ON DELETE CASCADE,
      kind text NOT NULL CHECK(kind IN ('station_internal','transfer')),leg_id uuid NOT NULL,
      context_key text NOT NULL,label varchar(60) NOT NULL,generation integer NOT NULL,
      start_request_id uuid NOT NULL,start_hash text NOT NULL,
      anchor_event_id uuid REFERENCES manual_trip_events(id) ON DELETE SET NULL,
      ready_event_id uuid REFERENCES manual_trip_events(id) ON DELETE SET NULL,
      started_at timestamptz NOT NULL,start_received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      finished_at timestamptz,finish_received_at timestamptz,
      same_scope boolean,condition text,apply_to_guidance boolean NOT NULL DEFAULT false,
      excluded boolean NOT NULL DEFAULT false,version integer NOT NULL DEFAULT 1 CHECK(version>0),
      predicted_seconds integer,predicted_arrival_at timestamptz,
      expires_at timestamptz NOT NULL,
      UNIQUE(trip_id,kind,leg_id),UNIQUE(user_id,start_request_id))''')
    op.execute('CREATE INDEX walking_segment_pool ON walking_segment_measurements(user_id,context_key,generation,start_received_at DESC)')
    op.execute('''CREATE TABLE walking_segment_selections (
      user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      context_key text NOT NULL,label varchar(60) NOT NULL,PRIMARY KEY(user_id,context_key))''')

def downgrade():
    op.execute("DO $$ BEGIN IF EXISTS(SELECT 1 FROM walking_segment_measurements) THEN RAISE EXCEPTION 'Manual segment history must be preserved'; END IF; END $$")
    op.execute('DROP TABLE walking_segment_selections,walking_segment_measurements')
