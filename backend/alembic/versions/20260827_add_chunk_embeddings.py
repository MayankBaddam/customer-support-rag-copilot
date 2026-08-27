"""Add vector embeddings to document chunks.

Revision ID: 20260827_chunk_embeddings
Revises: 20260827_document_ingestion
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "20260827_chunk_embeddings"
down_revision = "20260827_document_ingestion"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_document_chunks_embedding_hnsw_cosine"


def upgrade() -> None:
    op.add_column("document_chunks", sa.Column("embedding", Vector(768), nullable=True))
    op.create_index(
        INDEX_NAME,
        "document_chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="document_chunks", postgresql_using="hnsw")
    op.drop_column("document_chunks", "embedding")
