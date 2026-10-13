"""Immutable profile recalculation revisions with owned parent provenance."""
from alembic import op
revision='0011_walking_recalculation'
down_revision='0010_walking_cache'
branch_labels=None
depends_on=None


def upgrade():
    op.execute("""ALTER TABLE walking_estimate_revisions DROP CONSTRAINT walking_estimate_revisions_source_check;
        ALTER TABLE walking_estimate_revisions ADD CONSTRAINT walking_estimate_revisions_source_check CHECK(source IN ('ai_estimate','profile_recalculation'));
        ALTER TABLE walking_estimate_revisions ADD COLUMN parent_revision_id uuid, ADD COLUMN candidate_id varchar(200);
        ALTER TABLE walking_estimate_revisions ADD CONSTRAINT walking_revision_parent_key UNIQUE(id,user_id,estimate_id);
        ALTER TABLE walking_estimate_revisions ADD CONSTRAINT walking_revision_parent_fk FOREIGN KEY(parent_revision_id,user_id,estimate_id)
            REFERENCES walking_estimate_revisions(id,user_id,estimate_id) ON DELETE CASCADE;
        ALTER TABLE walking_estimate_revisions ADD CONSTRAINT walking_revision_provenance CHECK(
            (source='ai_estimate' AND parent_revision_id IS NULL AND candidate_id IS NULL) OR
            (source='profile_recalculation' AND parent_revision_id IS NOT NULL AND candidate_id IS NOT NULL AND parent_revision_id<>id));""")


def downgrade():
    # Discard only derived rows when explicitly downgrading; original AI snapshots remain.
    op.execute("""DELETE FROM walking_estimate_revisions WHERE source='profile_recalculation';
        ALTER TABLE walking_estimate_revisions DROP CONSTRAINT walking_revision_provenance, DROP CONSTRAINT walking_revision_parent_fk,
            DROP CONSTRAINT walking_revision_parent_key, DROP COLUMN parent_revision_id, DROP COLUMN candidate_id;
        ALTER TABLE walking_estimate_revisions DROP CONSTRAINT walking_estimate_revisions_source_check;
        ALTER TABLE walking_estimate_revisions ADD CONSTRAINT walking_estimate_revisions_source_check CHECK(source='ai_estimate');""")
