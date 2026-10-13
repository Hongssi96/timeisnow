"""Immutable, owner-bound walking estimates and minimal quality execution history."""
from alembic import op
revision='0009_walking_history'
down_revision='0008_routine_schedule'
branch_labels=None
depends_on=None


def upgrade():
    op.execute('''
    CREATE TABLE ai_executions (
      id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      request_id varchar(200) NOT NULL, body_hash char(64) NOT NULL,
      task_type text NOT NULL CHECK(task_type='walking_estimate'), model_version text,
      system_prompt_version text NOT NULL, prompt_version text NOT NULL, policy_version text NOT NULL,
      profile_version integer NOT NULL CHECK(profile_version>0),
      input_evidence jsonb NOT NULL, context_snapshot jsonb NOT NULL, structured_result jsonb,
      validation_status text NOT NULL CHECK(validation_status IN ('validated','needs_data','failed')),
      failure_code text, latency_ms integer CHECK(latency_ms>=0), usage jsonb,
      created_at timestamptz NOT NULL, retained_until timestamptz NOT NULL,
      UNIQUE(user_id,request_id), UNIQUE(id,user_id), CHECK(retained_until>created_at));
    CREATE TABLE walking_paths (
      id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      path_key char(64) NOT NULL, candidate_id varchar(200) NOT NULL,
      origin_ref varchar(200) NOT NULL, destination_ref varchar(200) NOT NULL,
      direction varchar(200) NOT NULL, scope varchar(200) NOT NULL,
      place_refs jsonb NOT NULL, evidence jsonb NOT NULL,
      verified_at timestamptz NOT NULL, calculated_at timestamptz NOT NULL,
      expires_at timestamptz NOT NULL, retained_until timestamptz NOT NULL,
      UNIQUE(id,user_id), CHECK(expires_at>calculated_at), CHECK(retained_until>calculated_at));
    CREATE TABLE walking_estimates (
      id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      walking_path_id uuid NOT NULL, policy_version text NOT NULL, created_at timestamptz NOT NULL,
      FOREIGN KEY(walking_path_id,user_id) REFERENCES walking_paths(id,user_id) ON DELETE CASCADE,
      UNIQUE(user_id,walking_path_id,policy_version), UNIQUE(id,user_id));
    CREATE TABLE walking_estimate_revisions (
      id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      estimate_id uuid NOT NULL, revision_no integer NOT NULL CHECK(revision_no>0),
      ai_execution_id uuid NOT NULL, profile_version integer NOT NULL CHECK(profile_version>0),
      base_seconds numeric NOT NULL CHECK(base_seconds>0 AND base_seconds<'Infinity'::numeric),
      applied_duration_factor numeric NOT NULL CHECK(applied_duration_factor BETWEEN 0.5 AND 2.0),
      estimated_seconds numeric NOT NULL CHECK(estimated_seconds>0 AND estimated_seconds=trunc(estimated_seconds) AND estimated_seconds<'Infinity'::numeric),
      method text NOT NULL CHECK(method IN ('provider_duration','distance_speed')),
      source text NOT NULL CHECK(source='ai_estimate'), calculated_at timestamptz NOT NULL,
      expires_at timestamptz NOT NULL, retained_until timestamptz NOT NULL,
      FOREIGN KEY(estimate_id,user_id) REFERENCES walking_estimates(id,user_id) ON DELETE CASCADE,
      FOREIGN KEY(ai_execution_id,user_id) REFERENCES ai_executions(id,user_id) ON DELETE CASCADE,
      UNIQUE(estimate_id,revision_no), CHECK(expires_at>calculated_at));
    CREATE INDEX walking_estimates_owner_idx ON walking_estimates(user_id,id);
    CREATE INDEX walking_revisions_latest_idx ON walking_estimate_revisions(estimate_id,revision_no DESC);
    CREATE INDEX walking_paths_retention_idx ON walking_paths(retained_until);
    CREATE INDEX ai_execution_retention_idx ON ai_executions(retained_until);
    ''')


def downgrade():
    for table in ('walking_estimate_revisions','walking_estimates','walking_paths','ai_executions'):
        op.execute('DROP TABLE '+table)
