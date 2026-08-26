"""Enable pgvector for future document embeddings.

Revision ID: 20260826_enable_pgvector
Revises:
"""
from alembic import op

revision = "20260826_enable_pgvector"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")