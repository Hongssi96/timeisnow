"""Extend terminal self reports without discarding old observations."""
from alembic import op
revision='0017_trip_outcomes'
down_revision='0016_transfer_events'
branch_labels=None
depends_on=None

def upgrade():
    op.execute('ALTER TABLE manual_trip_events DROP CONSTRAINT manual_trip_events_type_check')
    op.execute("ALTER TABLE manual_trip_events ADD CONSTRAINT manual_trip_events_type_check CHECK(type IN ('departed','approach_arrived','boarded','alighted','missed','arrived'))")
    op.execute('ALTER TABLE manual_trips DROP CONSTRAINT manual_trips_status_check')
    op.execute("ALTER TABLE manual_trips ADD CONSTRAINT manual_trips_status_check CHECK(status IN ('active','cancelled','missed','completed'))")

def downgrade():
    op.execute('ALTER TABLE manual_trip_events DROP CONSTRAINT manual_trip_events_type_check')
    op.execute("ALTER TABLE manual_trip_events ADD CONSTRAINT manual_trip_events_type_check CHECK(type IN ('departed','approach_arrived','boarded','alighted'))")
    op.execute('ALTER TABLE manual_trips DROP CONSTRAINT manual_trips_status_check')
    op.execute("ALTER TABLE manual_trips ADD CONSTRAINT manual_trips_status_check CHECK(status IN ('active','cancelled'))")
