import importlib.util
from pathlib import Path
from unittest.mock import Mock

from pgvector.sqlalchemy import Vector


def load_migration():
    path = Path(__file__).parents[1] / "alembic" / "versions" / "20260827_add_chunk_embeddings.py"
    spec = importlib.util.spec_from_file_location("chunk_embedding_migration", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_embedding_migration_upgrade_defines_vector_and_hnsw_cosine_index():
    migration = load_migration()
    migration.op = Mock()

    migration.upgrade()

    column = migration.op.add_column.call_args.args[1]
    assert column.name == "embedding"
    assert isinstance(column.type, Vector)
    assert column.type.dim == 768
    assert column.nullable is True
    index_call = migration.op.create_index.call_args
    assert index_call.args[:3] == (migration.INDEX_NAME, "document_chunks", ["embedding"])
    assert index_call.kwargs["postgresql_using"] == "hnsw"
    assert index_call.kwargs["postgresql_ops"] == {"embedding": "vector_cosine_ops"}


def test_embedding_migration_downgrade_is_reversible():
    migration = load_migration()
    migration.op = Mock()

    migration.downgrade()

    migration.op.drop_index.assert_called_once_with(
        migration.INDEX_NAME, table_name="document_chunks", postgresql_using="hnsw"
    )
    migration.op.drop_column.assert_called_once_with("document_chunks", "embedding")
    assert migration.down_revision == "20260827_document_ingestion"
    assert len(migration.revision) <= 32
