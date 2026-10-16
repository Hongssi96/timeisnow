"""Correction audit, retry receipts and safe profile rebuilds."""
from alembic import op
revision='0019_record_relearning'
down_revision='0018_walking_learning'
branch_labels=None
depends_on=None

def upgrade():
    op.execute("ALTER TABLE walking_learning_updates DROP CONSTRAINT walking_learning_updates_kind_check")
    op.execute("ALTER TABLE walking_learning_updates ADD CONSTRAINT walking_learning_updates_kind_check CHECK(kind IN ('observation','reset','restore','rebuild'))")
    op.execute('ALTER TABLE walking_learning_updates ADD COLUMN restorable boolean NOT NULL DEFAULT true')
    op.execute('ALTER TABLE walking_learning_observations ADD COLUMN version integer NOT NULL DEFAULT 1 CHECK(version>0)')
    op.execute('ALTER TABLE walking_learning_observations ADD COLUMN confirmation jsonb')
    op.execute("UPDATE walking_learning_observations SET confirmation=jsonb_build_object('same_scope',true,'condition','normal') WHERE status='valid'")
    op.execute("""CREATE TABLE trip_event_corrections (
      id uuid PRIMARY KEY,event_id uuid NOT NULL REFERENCES manual_trip_events(id) ON DELETE CASCADE,
      previous_value jsonb NOT NULL,new_value jsonb NOT NULL,reason text NOT NULL,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp())""")
    op.execute('CREATE INDEX trip_event_corrections_event ON trip_event_corrections(event_id,created_at DESC)')
    op.execute("""CREATE TABLE trip_record_mutations (
      user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,request_id uuid NOT NULL,
      trip_id uuid NOT NULL,guidance_id uuid,kind text NOT NULL,
      body_hash text NOT NULL,response jsonb NOT NULL,
      expires_at timestamptz NOT NULL DEFAULT clock_timestamp()+interval '24 hours',
      PRIMARY KEY(user_id,request_id))""")
    op.execute('CREATE INDEX trip_record_mutations_guidance ON trip_record_mutations(user_id,guidance_id)')

def downgrade():
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM trip_event_corrections)
      OR EXISTS(SELECT 1 FROM trip_record_mutations) OR EXISTS(SELECT 1 FROM walking_learning_updates WHERE kind='rebuild')
      THEN RAISE EXCEPTION 'Record correction history must be preserved'; END IF; END $$""")
    op.execute('DROP TABLE trip_record_mutations')
    op.execute('DROP TABLE trip_event_corrections')
    op.execute('ALTER TABLE walking_learning_observations DROP COLUMN confirmation,DROP COLUMN version')
    op.execute('ALTER TABLE walking_learning_updates DROP COLUMN restorable')
    op.execute('ALTER TABLE walking_learning_updates DROP CONSTRAINT walking_learning_updates_kind_check')
    op.execute("ALTER TABLE walking_learning_updates ADD CONSTRAINT walking_learning_updates_kind_check CHECK(kind IN ('observation','reset','restore'))")
