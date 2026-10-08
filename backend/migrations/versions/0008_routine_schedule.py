"""Routine schedule: weekdays (ISO 1..7), optional target arrival and fixed timezone."""
from alembic import op

revision = '0008_routine_schedule'
down_revision = '0007_routines'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
    ALTER TABLE routines ADD COLUMN weekdays smallint[] NOT NULL DEFAULT '{1,2,3,4,5}'
      CHECK(cardinality(weekdays) BETWEEN 1 AND 7 AND weekdays <@ ARRAY[1,2,3,4,5,6,7]::smallint[]);
    ALTER TABLE routines ADD COLUMN target_arrival_local_time time;
    ALTER TABLE routines ADD COLUMN timezone text NOT NULL DEFAULT 'Asia/Seoul'
      CHECK(timezone = 'Asia/Seoul');
    ''')


def downgrade():
    op.execute('''ALTER TABLE routines DROP COLUMN timezone,
      DROP COLUMN target_arrival_local_time, DROP COLUMN weekdays''')
