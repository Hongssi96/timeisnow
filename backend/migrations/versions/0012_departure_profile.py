"""Persist the personal walking factor used by first departure approximations."""
from alembic import op
revision='0012_departure_profile'
down_revision='0011_walking_recalculation'
branch_labels=None
depends_on=None

def upgrade():
    op.execute("ALTER TABLE user_profiles ADD COLUMN walking_duration_factor double precision NOT NULL DEFAULT 1.0 CHECK(walking_duration_factor BETWEEN 0.5 AND 2.0)")

def downgrade():
    op.execute('ALTER TABLE user_profiles DROP COLUMN walking_duration_factor')
