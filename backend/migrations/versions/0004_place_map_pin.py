"""User-confirmed map coordinates and entrance notes, preserving saved places."""
from alembic import op

revision = '0004_place_map_pin'
down_revision = '0003_saved_places'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
    ALTER TABLE saved_places ADD COLUMN entrance_note varchar(100)
      CHECK(entrance_note IS NULL OR length(btrim(entrance_note)) BETWEEN 1 AND 100);
    ALTER TABLE saved_places ADD COLUMN location_source text NOT NULL DEFAULT 'search'
      CHECK(location_source IN ('search','map_pin'));
    ALTER TABLE saved_places ADD COLUMN location_address text;
    CREATE TABLE place_location_confirmations (
      id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      latitude double precision NOT NULL CHECK(latitude BETWEEN -90 AND 90),
      longitude double precision NOT NULL CHECK(longitude BETWEEN -180 AND 180),
      location_address text NOT NULL, expires_at timestamptz NOT NULL);
    CREATE INDEX place_location_confirmations_expiry_idx ON place_location_confirmations(expires_at);
    ''')


def downgrade():
    op.execute('DROP TABLE place_location_confirmations')
    for column in ('location_address', 'location_source', 'entrance_note'):
        op.execute(f'ALTER TABLE saved_places DROP COLUMN {column}')
