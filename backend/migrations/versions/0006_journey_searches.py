"""Bounded journey results and job metadata; no raw input coordinates."""
from alembic import op

revision = '0006_journey_searches'
down_revision = '0005_place_management'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
    CREATE TABLE journey_searches (
      id uuid PRIMARY KEY, job_id uuid NOT NULL UNIQUE,
      user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      status text NOT NULL CHECK(status IN ('queued','running','succeeded','failed')),
      place_refs jsonb NOT NULL, candidates jsonb NOT NULL DEFAULT '[]',
      unavailable_reasons jsonb NOT NULL DEFAULT '[]', error jsonb,
      created_at timestamptz NOT NULL DEFAULT now(), expires_at timestamptz NOT NULL,
      worker_deadline timestamptz NOT NULL, finished_at timestamptz,
      job_expires_at timestamptz NOT NULL);
    CREATE INDEX journey_owner_idx ON journey_searches(user_id,id);
    CREATE INDEX journey_expiry_idx ON journey_searches(job_expires_at);
    CREATE TABLE journey_search_keys (
      user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      key varchar(128) NOT NULL, body_hash char(64) NOT NULL,
      search_id uuid REFERENCES journey_searches(id) ON DELETE SET NULL,
      expires_at timestamptz NOT NULL, PRIMARY KEY(user_id,key));
    CREATE INDEX journey_keys_expiry_idx ON journey_search_keys(expires_at);
    ''')


def downgrade():
    op.execute('DROP TABLE journey_search_keys')
    op.execute('DROP TABLE journey_searches')
