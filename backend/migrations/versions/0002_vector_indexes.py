"""Vector cosine indexes for semantic retrieval."""
from alembic import op
revision = '0002_vector_indexes'
down_revision = 'dccb608c195f'
branch_labels = None
depends_on = None

def upgrade():
    if op.get_bind().dialect.name == 'postgresql':
        op.create_index('ix_memory_embeddings_cosine', 'memory_embeddings', ['embedding'], postgresql_using='hnsw', postgresql_ops={'embedding':'vector_cosine_ops'})
        op.create_index('ix_document_chunks_cosine', 'document_chunks', ['embedding'], postgresql_using='hnsw', postgresql_ops={'embedding':'vector_cosine_ops'})

def downgrade():
    if op.get_bind().dialect.name == 'postgresql':
        op.drop_index('ix_document_chunks_cosine', table_name='document_chunks')
        op.drop_index('ix_memory_embeddings_cosine', table_name='memory_embeddings')
