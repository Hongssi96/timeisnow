"""Per-leg manual progress; never discard observations on downgrade."""
from alembic import op
revision='0016_transfer_events'
down_revision='0015_first_boarding_events'
branch_labels=None
depends_on=None

def upgrade():
    op.execute('ALTER TABLE manual_trip_events DROP CONSTRAINT manual_trip_events_type_check')
    op.execute("ALTER TABLE manual_trip_events ADD CONSTRAINT manual_trip_events_type_check CHECK(type IN ('departed','approach_arrived','boarded','alighted'))")
    op.execute('ALTER TABLE manual_trip_events DROP CONSTRAINT manual_trip_events_trip_id_type_key')
    op.execute('ALTER TABLE manual_trip_events ADD CONSTRAINT manual_trip_events_trip_type_leg_key UNIQUE(trip_id,type,leg_id)')

def downgrade():
    op.execute('ALTER TABLE manual_trip_events DROP CONSTRAINT manual_trip_events_type_check')
    op.execute("ALTER TABLE manual_trip_events ADD CONSTRAINT manual_trip_events_type_check CHECK(type IN ('departed','approach_arrived','boarded'))")
    op.execute('ALTER TABLE manual_trip_events ADD CONSTRAINT manual_trip_events_trip_id_type_key UNIQUE(trip_id,type)')
    op.execute('ALTER TABLE manual_trip_events DROP CONSTRAINT manual_trip_events_trip_type_leg_key')
