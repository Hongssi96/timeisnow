"""Named routines over selected journey candidate snapshots; deleted place refs detach."""
from alembic import op

revision = '0007_routines'
down_revision = '0006_journey_searches'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
    CREATE TABLE journey_plans (
      id uuid PRIMARY KEY,
      user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      search_id uuid NOT NULL, candidate_id uuid NOT NULL,
      candidate jsonb NOT NULL,
      total_seconds integer NOT NULL CHECK(total_seconds >= 0),
      transfer_count smallint NOT NULL CHECK(transfer_count BETWEEN 0 AND 2),
      model_version text NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now());
    CREATE UNIQUE INDEX journey_plans_candidate_idx ON journey_plans(user_id, search_id, candidate_id);
    CREATE TABLE routines (
      id uuid PRIMARY KEY,
      user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      name varchar(30) NOT NULL CHECK(length(btrim(name)) BETWEEN 1 AND 30),
      origin_place_id uuid REFERENCES saved_places(id) ON DELETE SET NULL,
      destination_place_id uuid REFERENCES saved_places(id) ON DELETE SET NULL,
      journey_plan_id uuid NOT NULL REFERENCES journey_plans(id) ON DELETE CASCADE,
      status text NOT NULL DEFAULT 'active' CHECK(status IN ('active','needs_attention')),
      version integer NOT NULL DEFAULT 1 CHECK(version > 0),
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
    CREATE INDEX routines_owner_idx ON routines(user_id, id DESC);
    CREATE TABLE routine_creation_keys (
      user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      key varchar(128) NOT NULL, body_hash char(64) NOT NULL,
      routine_id uuid REFERENCES routines(id) ON DELETE SET NULL,
      expires_at timestamptz NOT NULL, PRIMARY KEY(user_id, key));
    CREATE INDEX routine_keys_expiry_idx ON routine_creation_keys(expires_at);
    ''')


def downgrade():
    op.execute('DROP TABLE routine_creation_keys')
    op.execute('DROP TABLE routines')
    op.execute('DROP TABLE journey_plans')
