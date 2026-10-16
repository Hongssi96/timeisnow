"""Export metadata only; no duplicated private records or files."""
from alembic import op
revision='0020_trip_exports'
down_revision='0019_record_relearning'
branch_labels=None
depends_on=None

def upgrade():
    op.execute('''CREATE TABLE trip_exports (
      id uuid PRIMARY KEY,user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      range_from timestamptz NOT NULL,range_to timestamptz NOT NULL,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      expires_at timestamptz NOT NULL DEFAULT clock_timestamp()+interval '24 hours',
      download_expires_at timestamptz NOT NULL DEFAULT clock_timestamp()+interval '10 minutes',
      CHECK(range_from<range_to))''')
    op.execute('CREATE INDEX trip_exports_owner ON trip_exports(user_id,expires_at)')

def downgrade():
    op.execute('DROP TABLE trip_exports')
