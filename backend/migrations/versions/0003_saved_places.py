"""Owned saved places, short-lived search candidates and creation retries."""
from alembic import op

revision = '0003_saved_places'
down_revision = '0002_member_auth'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
    CREATE TABLE saved_places (
      id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      label varchar(30) NOT NULL CHECK(length(btrim(label)) BETWEEN 1 AND 30),
      name text NOT NULL, address text NOT NULL,
      latitude double precision NOT NULL CHECK(latitude BETWEEN -90 AND 90),
      longitude double precision NOT NULL CHECK(longitude BETWEEN -180 AND 180),
      entrance_ref text, version integer NOT NULL DEFAULT 1 CHECK(version > 0),
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
    CREATE INDEX saved_places_owner_idx ON saved_places(user_id,id DESC);
    CREATE TABLE place_searches (
      id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      candidates jsonb NOT NULL, expires_at timestamptz NOT NULL);
    CREATE INDEX place_searches_expiry_idx ON place_searches(expires_at);
    CREATE TABLE place_creation_keys (
      user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      key varchar(128) NOT NULL, body_hash char(64) NOT NULL,
      place_id uuid NOT NULL REFERENCES saved_places(id) ON DELETE CASCADE,
      expires_at timestamptz NOT NULL, PRIMARY KEY(user_id,key));
    CREATE INDEX place_keys_expiry_idx ON place_creation_keys(expires_at);
    ''')


def downgrade():
    for table in ('place_creation_keys', 'place_searches', 'saved_places'):
        op.execute(f'DROP TABLE {table}')
