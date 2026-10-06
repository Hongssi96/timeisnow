"""Email uniqueness, password credentials and server sessions. No mail workflow."""
from alembic import op

revision = "0002_member_auth"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE users (
      id uuid PRIMARY KEY, display_name varchar(30) NOT NULL,
      status text NOT NULL DEFAULT 'active' CHECK(status IN ('active','deleting')),
      created_at timestamptz NOT NULL DEFAULT now(), version integer NOT NULL DEFAULT 1);
    CREATE TABLE auth_credentials (
      user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
      email_normalized varchar(254) NOT NULL UNIQUE, password_hash text NOT NULL);
    CREATE TABLE user_profiles (
      user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
      walking_preference text NOT NULL DEFAULT 'normal',
      first_boarding_buffer_seconds integer NOT NULL DEFAULT 300 CHECK(first_boarding_buffer_seconds BETWEEN 0 AND 1800),
      transfer_buffer_seconds integer NOT NULL DEFAULT 120 CHECK(transfer_buffer_seconds BETWEEN 0 AND 1800),
      route_preference text NOT NULL DEFAULT 'balanced', timezone text NOT NULL DEFAULT 'Asia/Seoul',
      version integer NOT NULL DEFAULT 1);
    CREATE TABLE auth_sessions (
      token_hash char(64) PRIMARY KEY, user_id uuid REFERENCES users(id) ON DELETE CASCADE,
      csrf_token_hash char(64) NOT NULL, absolute_expires_at timestamptz NOT NULL,
      idle_expires_at timestamptz NOT NULL);
    CREATE TABLE auth_rate_limit_buckets (
      scope text NOT NULL, key_hash char(64) NOT NULL, window_start bigint NOT NULL,
      count integer NOT NULL DEFAULT 0 CHECK(count >= 0), expires_at timestamptz NOT NULL,
      PRIMARY KEY(scope,key_hash,window_start));
    CREATE INDEX auth_sessions_expiry_idx ON auth_sessions(idle_expires_at);
    CREATE INDEX auth_limits_expiry_idx ON auth_rate_limit_buckets(expires_at);
    """)


def downgrade():
    for table in ('auth_rate_limit_buckets', 'auth_sessions', 'user_profiles', 'auth_credentials', 'users'):
        op.execute(f'DROP TABLE {table}')
