"""Join independently published manual-trip and meeting migration heads.

Keep both existing revision IDs so installations on either branch can upgrade.
Alembic applies the missing parent before joining; this revision changes no DDL.
"""
revision = '0014_integrated_features'
down_revision = ('0013_manual_trips', '0013_meeting_core')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
