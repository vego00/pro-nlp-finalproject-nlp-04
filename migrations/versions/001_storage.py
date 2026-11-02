"""Initial document and session persistence."""
from alembic import op
from sqlalchemy import Column, MetaData, Table, String, Text, Integer, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
metadata = MetaData()
users = Table('users', metadata, Column('id', String, primary_key=True), Column('key', String, unique=True, nullable=False))
documents = Table('documents', metadata,
    Column('id', String, primary_key=True), Column('owner_id', ForeignKey('users.id'), nullable=False),
    Column('title', Text, nullable=False), Column('draft', Text, nullable=False), Column('draft_document', JSONB),
    Column('draft_revision', Integer, nullable=False, default=0),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('updated_at', DateTime(timezone=True), server_default=func.now(), nullable=False, index=True))
sessions = Table('sessions', metadata,
    Column('id', String, primary_key=True), Column('document_id', ForeignKey('documents.id'), unique=True, nullable=False),
    Column('state', JSONB, nullable=False), Column('state_schema_version', Integer, nullable=False, default=1),
    Column('markdown', Text, nullable=False), Column('status', String, nullable=False), Column('error', Text),
    Column('run_token', String))

revision = '001_storage'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    metadata.create_all(op.get_bind())

def downgrade():
    raise RuntimeError('데이터 보존을 위해 자동 삭제를 지원하지 않습니다.')
