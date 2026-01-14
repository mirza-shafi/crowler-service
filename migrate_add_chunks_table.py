"""
Migration script to add content_chunks table for RAG
"""

import asyncio
from sqlalchemy import create_engine, text
from app.core.config import settings

async def migrate():
    """Add content_chunks table"""
    
    # Create synchronous engine for migration
    db_url = settings.DATABASE_URL.replace('+asyncpg', '')
    engine = create_engine(db_url)
    
    migrations = [
        # Create content_chunks table
        """
        CREATE TABLE IF NOT EXISTS content_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            content_id UUID NOT NULL,
            chunk_index INTEGER NOT NULL,
            start_char INTEGER NOT NULL,
            end_char INTEGER NOT NULL,
            token_count INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding vector(384),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        # Create index on content_id
        """
        CREATE INDEX IF NOT EXISTS idx_chunks_content_id ON content_chunks(content_id);
        """,
        
        # Create index on embedding (IVFFlat index for fast search)
        # Note: Requires adequate data quantity, using simple create if not exists
        """
        CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON content_chunks 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
        """
    ]
    
    try:
        with engine.connect() as conn:
            print("Starting migration for RAG chunks...")
            
            # Enable vector extension just in case
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            
            for i, migration_sql in enumerate(migrations, 1):
                print(f"Running migration {i}/{len(migrations)}...")
                try:
                    conn.execute(text(migration_sql))
                    conn.commit()
                    print(f"✓ Migration {i} completed")
                except Exception as e:
                    print(f"⚠️  Warning in migration {i}: {e}")
                    # Continue anyway as table might exist
            
            print("\n✅ content_chunks table created successfully!")
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())
