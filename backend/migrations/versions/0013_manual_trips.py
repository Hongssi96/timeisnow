"""Immutable selected guidance and manual departure sessions."""
from alembic import op
revision='0013_manual_trips'
down_revision='0012_departure_profile'
branch_labels=None
depends_on=None

def upgrade():
    op.execute('''
    CREATE TABLE guidance_snapshots (
      id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      routine_id uuid REFERENCES routines(id) ON DELETE SET NULL,
      snapshot jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
      expires_at timestamptz NOT NULL);
    CREATE TABLE manual_trips (
      id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      guidance_id uuid NOT NULL UNIQUE REFERENCES guidance_snapshots(id) ON DELETE CASCADE,
      measurement_mode text NOT NULL CHECK(measurement_mode IN ('assisted','baseline')),
      status text NOT NULL DEFAULT 'active' CHECK(status IN ('active','cancelled')),
      version integer NOT NULL DEFAULT 1 CHECK(version>0),
      created_at timestamptz NOT NULL DEFAULT now(), expires_at timestamptz NOT NULL);
    CREATE UNIQUE INDEX manual_trips_active_idx ON manual_trips(user_id) WHERE status='active';
    CREATE INDEX manual_trips_owner_idx ON manual_trips(user_id,created_at DESC,id DESC);
    CREATE TABLE manual_trip_creation_keys (
      user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      key varchar(128) NOT NULL, body_hash char(64) NOT NULL,
      trip_id uuid REFERENCES manual_trips(id) ON DELETE SET NULL,
      expires_at timestamptz NOT NULL, PRIMARY KEY(user_id,key));
    CREATE TABLE manual_trip_events (
      id uuid PRIMARY KEY, trip_id uuid NOT NULL REFERENCES manual_trips(id) ON DELETE CASCADE,
      client_event_id uuid NOT NULL, body_hash char(64) NOT NULL,
      type text NOT NULL CHECK(type='departed'), leg_id uuid NOT NULL,
      source text NOT NULL CHECK(source='manual'), occurred_at timestamptz NOT NULL,
      received_at timestamptz NOT NULL DEFAULT now(),
      excluded boolean NOT NULL DEFAULT false, version integer NOT NULL DEFAULT 1 CHECK(version>0),
      UNIQUE(trip_id,client_event_id), UNIQUE(trip_id,type));
    ''')

def downgrade():
    op.execute('DROP TABLE manual_trip_events')
    op.execute('DROP TABLE manual_trip_creation_keys')
    op.execute('DROP TABLE manual_trips')
    op.execute('DROP TABLE guidance_snapshots')
