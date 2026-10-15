"""Extend first-boarding self reports while preserving existing departures."""
from alembic import op

revision='0015_first_boarding_events'
down_revision='0014_integrated_features'
branch_labels=None
depends_on=None

def upgrade():
    op.execute('ALTER TABLE manual_trip_events DROP CONSTRAINT manual_trip_events_type_check')
    op.execute("ALTER TABLE manual_trip_events ADD CONSTRAINT manual_trip_events_type_check CHECK(type IN ('departed','approach_arrived','boarded'))")

def downgrade():
    # Refuse to discard new observations on downgrade. Remove them explicitly first.
    op.execute('ALTER TABLE manual_trip_events DROP CONSTRAINT manual_trip_events_type_check')
    op.execute("ALTER TABLE manual_trip_events ADD CONSTRAINT manual_trip_events_type_check CHECK(type='departed')")
