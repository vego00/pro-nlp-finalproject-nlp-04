"""Document history, durable jobs, administrator accounts and login sessions."""
from alembic import op
revision = '002_history_auth'
down_revision = '001_storage'
branch_labels = None
depends_on = None


def upgrade():
    statements = [
        "ALTER TABLE users ADD COLUMN email text UNIQUE, ADD COLUMN password_hash text, ADD COLUMN is_admin boolean NOT NULL DEFAULT false, ADD COLUMN active boolean NOT NULL DEFAULT true, ADD COLUMN allow_google boolean NOT NULL DEFAULT false",
        "CREATE TABLE document_versions (id bigserial PRIMARY KEY, document_id varchar NOT NULL REFERENCES documents(id), revision integer NOT NULL, kind varchar NOT NULL CHECK(kind IN ('draft','generated')), markdown text NOT NULL, document jsonb, reason varchar NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(document_id,kind,revision))",
        "INSERT INTO document_versions(document_id,revision,kind,markdown,document,reason) SELECT id,draft_revision,'draft',draft,draft_document,'migration' FROM documents",
        "INSERT INTO document_versions(document_id,revision,kind,markdown,reason) SELECT document_id,0,'generated',markdown,'migration' FROM sessions WHERE markdown<>''",
        "CREATE TABLE jobs (id varchar PRIMARY KEY, owner_id varchar NOT NULL REFERENCES users(id), session_id varchar NOT NULL REFERENCES sessions(id), request_key varchar NOT NULL, input_hash varchar NOT NULL, input jsonb NOT NULL, kind varchar NOT NULL, status varchar NOT NULL, base_revision integer NOT NULL, result jsonb, error text, created_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz, UNIQUE(owner_id,request_key))",
        "CREATE INDEX jobs_session_created ON jobs(session_id,created_at DESC)",
        "CREATE TABLE agent_runs (id varchar PRIMARY KEY, job_id varchar NOT NULL REFERENCES jobs(id), started_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz, status varchar NOT NULL, error text)",
        "CREATE TABLE login_sessions (token_hash varchar PRIMARY KEY, user_id varchar NOT NULL REFERENCES users(id), csrf varchar NOT NULL, expires_at timestamptz NOT NULL)",
        "CREATE TABLE external_identities (provider varchar NOT NULL, subject varchar NOT NULL, user_id varchar NOT NULL REFERENCES users(id), PRIMARY KEY(provider,subject))",
    ]
    for statement in statements:
        op.execute(statement)


def downgrade():
    raise RuntimeError('Restore a backup instead of deleting account and history data.')
