"""Explicit verified physical cache identity; no inferred legacy backfill."""
from alembic import op
revision='0010_walking_cache'
down_revision='0009_walking_history'
branch_labels=None
depends_on=None


def upgrade():
    op.execute("""ALTER TABLE walking_paths ADD COLUMN cache_key char(64), ADD COLUMN cache_identity jsonb;
        ALTER TABLE walking_paths ADD CONSTRAINT walking_cache_pair CHECK ((cache_key IS NULL)=(cache_identity IS NULL));
        CREATE INDEX walking_cache_lookup ON walking_paths(user_id,cache_key,expires_at DESC) WHERE cache_key IS NOT NULL;
        ALTER TABLE ai_executions ADD COLUMN reused_estimates jsonb NOT NULL DEFAULT '[]'::jsonb;
        ALTER TABLE ai_executions ADD CONSTRAINT reused_estimates_array CHECK(jsonb_typeof(reused_estimates)='array');""")


def downgrade():
    op.execute("""ALTER TABLE ai_executions DROP CONSTRAINT reused_estimates_array, DROP COLUMN reused_estimates;
        DROP INDEX walking_cache_lookup;
        ALTER TABLE walking_paths DROP CONSTRAINT walking_cache_pair, DROP COLUMN cache_key, DROP COLUMN cache_identity;""")
