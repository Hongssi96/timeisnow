"""Join independently published meeting-personal-flow and trip-export heads.

Keep both existing revision IDs so installations on either branch can upgrade.
Alembic applies the missing parent before joining; this revision changes no DDL.
"""
revision = '0021_meeting_flow_merge'
down_revision = ('0020_trip_exports', '0018_meeting_personal_flows')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
