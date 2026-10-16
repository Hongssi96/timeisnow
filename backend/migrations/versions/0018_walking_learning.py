"""Owned manual walking observations and immutable factor changes."""
from alembic import op
revision='0018_walking_learning'
down_revision='0017_trip_outcomes'
branch_labels=None
depends_on=None

def upgrade():
    op.execute("""CREATE TABLE walking_learning_state (
      user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
      generation integer NOT NULL DEFAULT 1,
      started_at timestamptz NOT NULL DEFAULT 'epoch')""")
    op.execute("""CREATE TABLE walking_learning_updates (
      id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      profile_version integer NOT NULL, previous_factor double precision NOT NULL,
      factor double precision NOT NULL CHECK(factor BETWEEN 0.5 AND 2),
      kind text NOT NULL CHECK(kind IN ('observation','reset','restore')),
      request_id uuid, body_hash text, response jsonb,
      policy_version text NOT NULL DEFAULT 'manual-walking.v1',
      sample_ids jsonb NOT NULL DEFAULT '[]', pool_scope text,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      UNIQUE(user_id,profile_version), UNIQUE(user_id,request_id))""")
    op.execute("""CREATE TABLE walking_learning_observations (
      id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      trip_id uuid NOT NULL UNIQUE REFERENCES manual_trips(id) ON DELETE CASCADE,
      body_hash text NOT NULL, generation integer NOT NULL,
      path_key text, place_refs jsonb NOT NULL, base_seconds numeric,
      observed_seconds numeric, predicted_seconds numeric, ratio numeric,
      status text NOT NULL CHECK(status IN ('valid','excluded')),
      reasons jsonb NOT NULL, response jsonb NOT NULL,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(), expires_at timestamptz NOT NULL)""")
    op.execute('CREATE INDEX walking_learning_pool ON walking_learning_observations(user_id,generation,status,created_at DESC)')

def downgrade():
    op.execute('DROP TABLE walking_learning_observations')
    op.execute('DROP TABLE walking_learning_updates')
    op.execute('DROP TABLE walking_learning_state')
