"""add pgvector extension

Revision ID: 001
Revises: 
Create Date: 2024-03-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Enable the pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create an index on the embedding column for faster similarity search
    op.execute('''
        CREATE INDEX IF NOT EXISTS presentation_embeddings_embedding_idx 
        ON presentation_embeddings 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    ''')

def downgrade():
    # Drop the index
    op.execute('DROP INDEX IF EXISTS presentation_embeddings_embedding_idx')
    
    # Drop the extension
    op.execute('DROP EXTENSION IF EXISTS vector') 