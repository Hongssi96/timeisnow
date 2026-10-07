"""Separate location basis from edits; preserve deleted creation retry keys."""
from alembic import op

revision = '0005_place_management'
down_revision = '0004_place_map_pin'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
    ALTER TABLE saved_places ADD COLUMN location_version integer NOT NULL DEFAULT 1 CHECK(location_version > 0);
    UPDATE saved_places SET location_version=version;
    ALTER TABLE place_creation_keys DROP CONSTRAINT place_creation_keys_place_id_fkey;
    ALTER TABLE place_creation_keys ALTER COLUMN place_id DROP NOT NULL;
    ALTER TABLE place_creation_keys ADD CONSTRAINT place_creation_keys_place_id_fkey
      FOREIGN KEY(place_id) REFERENCES saved_places(id) ON DELETE SET NULL;
    ''')


def downgrade():
    # Removed places cannot be recovered by a schema downgrade. Drop their key markers only.
    op.execute('''
    DELETE FROM place_creation_keys WHERE place_id IS NULL;
    ALTER TABLE place_creation_keys DROP CONSTRAINT place_creation_keys_place_id_fkey;
    ALTER TABLE place_creation_keys ALTER COLUMN place_id SET NOT NULL;
    ALTER TABLE place_creation_keys ADD CONSTRAINT place_creation_keys_place_id_fkey
      FOREIGN KEY(place_id) REFERENCES saved_places(id) ON DELETE CASCADE;
    ALTER TABLE saved_places DROP COLUMN location_version;
    ''')
