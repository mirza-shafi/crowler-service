"""
Verify Chunking Implementation
"""
import asyncio
import uuid
from app.services.vector_db_service import vector_db_service
from app.services.text_chunker import text_chunker
from app.models.content_manager import Base, ContentChunk
from sqlalchemy import select
from app.core.config import settings

SAMPLE_TEXT = """
Introduction to Artificial Intelligence

Artificial Intelligence (AI) is the simulation of human intelligence processes by machines, especially computer systems. These processes include learning, reasoning, and self-correction. AI has become increasingly important in modern technology and business applications.

Machine Learning Fundamentals

Machine Learning is a subset of AI that provides systems the ability to automatically learn and improve from experience without being explicitly programmed. It focuses on the development of computer programs that can access data and use it to learn for themselves. The process of learning begins with observations or data, such as examples, direct experience, or instruction, in order to look for patterns in data and make better decisions in the future.

Neural Networks Architecture

Neural networks are computing systems inspired by the biological neural networks that constitute animal brains. An Artificial Neural Network (ANN) is based on a collection of connected units or nodes called artificial neurons, which loosely model the neurons in a biological brain. Each connection, like the synapses in a biological brain, can transmit a signal to other neurons. An artificial neuron receives a signal then processes it and can signal neurons connected to it.

Deep Learning Applications

Deep Learning is a subset of machine learning that uses neural networks with multiple layers. These deep neural networks attempt to simulate the behavior of the human brain, allowing it to learn from large amounts of data. While a neural network with a single layer can still make approximate predictions, additional hidden layers can help optimize the accuracy. Deep learning drives many artificial intelligence applications and services that improve automation.
""" * 5  # Multiply to make sure it's long enough to be chunked multiple times

async def verify():
    print(f"Checking chunking with {len(SAMPLE_TEXT)} chars of text...")
    
    # Initialize DB (create tables if needed, though they exist)
    await vector_db_service.initialize_database()
    
    # 1. Chunking Logic Check
    chunks = text_chunker.chunk_text(SAMPLE_TEXT)
    print(f"✅ TextChunker created {len(chunks)} chunks in memory")
    
    # 2. Store Chunks in DB
    # We fake a content ID since we aren't creating a parent record for this test, 
    # or we should create a parent to respect FK logic if enforced (currently no strict FK constraint in model definition, just logical)
    # But let's just insert chunks.
    
    content_id = uuid.uuid4()
    print(f"Simulating storage for content_id: {content_id}")
    
    stored_count = await vector_db_service.store_content_chunks(content_id, SAMPLE_TEXT)
    print(f"✅ Stored {stored_count} chunks in database")
    
    # 3. Verify in DB
    async with vector_db_service.async_session_maker() as session:
        result = await session.execute(
            select(ContentChunk).where(ContentChunk.content_id == content_id)
        )
        db_chunks = result.scalars().all()
        print(f"✅ Found {len(db_chunks)} chunks in DB")
        
        if db_chunks:
            print(f"   First chunk text: {db_chunks[0].chunk_text[:50]}...")
            print(f"   First chunk token count: {db_chunks[0].token_count}")
    
    # 4. Cleanup
    async with vector_db_service.async_session_maker() as session:
        from sqlalchemy import text
        await session.execute(text("DELETE FROM content_chunks WHERE content_id = :cid"), {"cid": content_id})
        await session.commit()
    print("✅ Cleanup complete")

if __name__ == "__main__":
    asyncio.run(verify())
