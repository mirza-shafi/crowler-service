#!/usr/bin/env python3
"""
Interactive Demo: How Chunking Works
Run this to see chunking in action!
"""

from app.services.text_chunker import text_chunker

# Sample document (simulating a PDF upload)
SAMPLE_DOCUMENT = """
Introduction to Artificial Intelligence

Artificial Intelligence (AI) is the simulation of human intelligence processes by machines, especially computer systems. These processes include learning, reasoning, and self-correction. AI has become increasingly important in modern technology and business applications.

Machine Learning Fundamentals

Machine Learning is a subset of AI that provides systems the ability to automatically learn and improve from experience without being explicitly programmed. It focuses on the development of computer programs that can access data and use it to learn for themselves. The process of learning begins with observations or data, such as examples, direct experience, or instruction, in order to look for patterns in data and make better decisions in the future.

Neural Networks Architecture

Neural networks are computing systems inspired by the biological neural networks that constitute animal brains. An Artificial Neural Network (ANN) is based on a collection of connected units or nodes called artificial neurons, which loosely model the neurons in a biological brain. Each connection, like the synapses in a biological brain, can transmit a signal to other neurons. An artificial neuron receives a signal then processes it and can signal neurons connected to it.

Deep Learning Applications

Deep Learning is a subset of machine learning that uses neural networks with multiple layers. These deep neural networks attempt to simulate the behavior of the human brain, allowing it to learn from large amounts of data. While a neural network with a single layer can still make approximate predictions, additional hidden layers can help optimize the accuracy. Deep learning drives many artificial intelligence applications and services that improve automation.

Practical Use Cases

AI and machine learning are being applied across various industries including healthcare for disease diagnosis, finance for fraud detection, retail for personalized recommendations, and autonomous vehicles for self-driving cars. The technology continues to evolve and find new applications in solving complex real-world problems.
"""

def print_separator(char="=", length=80):
    """Print a separator line"""
    print(char * length)

def print_header(text):
    """Print a formatted header"""
    print_separator()
    print(f"  {text}")
    print_separator()

def demo_chunking():
    """Demonstrate how chunking works"""
    
    print("\n")
    print_header("🎯 CHUNKING DEMO: How It Works")
    
    # Show original document
    print("\n📄 ORIGINAL DOCUMENT:")
    print_separator("-")
    print(f"Total characters: {len(SAMPLE_DOCUMENT)}")
    print(f"Total words: {len(SAMPLE_DOCUMENT.split())}")
    print(f"Estimated tokens: ~{len(SAMPLE_DOCUMENT) // 4}")
    print_separator("-")
    print(SAMPLE_DOCUMENT[:500] + "...\n[truncated for display]")
    
    # Chunk the document
    print("\n")
    print_header("✂️  CHUNKING PROCESS")
    print("\nSettings:")
    print(f"  - Chunk size: 512 tokens (~2000 characters)")
    print(f"  - Overlap: 100 tokens (~400 characters)")
    print(f"  - Strategy: recursive (paragraphs → sentences → words)")
    
    chunks = text_chunker.chunk_text(SAMPLE_DOCUMENT, strategy="recursive")
    
    print(f"\n✅ Created {len(chunks)} chunks")
    
    # Show each chunk
    print("\n")
    print_header("📦 CHUNKS CREATED")
    
    for i, chunk in enumerate(chunks):
        print(f"\n{'='*80}")
        print(f"CHUNK {i + 1} of {len(chunks)}")
        print(f"{'='*80}")
        print(f"Chunk Index: {chunk.chunk_index}")
        print(f"Character Range: {chunk.start_char} → {chunk.end_char}")
        print(f"Length: {len(chunk.text)} characters")
        print(f"Estimated Tokens: {chunk.token_count}")
        print(f"\n--- CHUNK TEXT ---")
        print(chunk.text[:300] + "..." if len(chunk.text) > 300 else chunk.text)
        print(f"\n[Full chunk is {len(chunk.text)} chars]")
        
        # Show overlap with next chunk
        if i < len(chunks) - 1:
            next_chunk = chunks[i + 1]
            overlap_start = max(chunk.start_char, next_chunk.start_char)
            overlap_end = min(chunk.end_char, next_chunk.end_char)
            overlap_size = overlap_end - overlap_start
            if overlap_size > 0:
                print(f"\n⚡ Overlap with next chunk: {overlap_size} characters")
    
    # Show search simulation
    print("\n")
    print_header("🔍 SEARCH SIMULATION")
    
    query = "What are neural networks?"
    print(f"\nUser Query: '{query}'")
    print("\nSearching through chunks...")
    
    # Simple keyword matching (in real system, this would be vector similarity)
    scores = []
    for i, chunk in enumerate(chunks):
        # Count keyword matches (simplified)
        keywords = ["neural", "network", "neuron"]
        score = sum(chunk.text.lower().count(kw) for kw in keywords)
        scores.append((i, score, chunk))
    
    # Sort by score
    scores.sort(key=lambda x: x[1], reverse=True)
    
    print("\n📊 Chunk Relevance Scores:")
    for i, score, chunk in scores:
        stars = "⭐" * min(5, score)
        print(f"  Chunk {i + 1}: {score} matches {stars}")
    
    # Show best match
    best_chunk_idx, best_score, best_chunk = scores[0]
    print(f"\n✅ BEST MATCH: Chunk {best_chunk_idx + 1}")
    print_separator("-")
    print(best_chunk.text[:400] + "...")
    print_separator("-")
    
    # Compare with non-chunking approach
    print("\n")
    print_header("🆚 COMPARISON: With vs Without Chunking")
    
    print("\n❌ WITHOUT CHUNKING (Current):")
    print(f"  - Truncate document to 5000 chars")
    print(f"  - Lost: {max(0, len(SAMPLE_DOCUMENT) - 5000)} characters")
    print(f"  - Return: Entire 5000 chars (includes irrelevant content)")
    print(f"  - User must read: 5000 characters")
    
    print("\n✅ WITH CHUNKING (Recommended):")
    print(f"  - Split into {len(chunks)} chunks")
    print(f"  - Lost: 0 characters")
    print(f"  - Return: Only relevant chunk ({len(best_chunk.text)} chars)")
    print(f"  - User must read: {len(best_chunk.text)} characters")
    
    print(f"\n💡 Improvement: User reads {((5000 - len(best_chunk.text)) / 5000 * 100):.0f}% less content!")
    
    # Summary
    print("\n")
    print_header("📈 SUMMARY")
    print(f"""
Document Statistics:
  - Original size: {len(SAMPLE_DOCUMENT)} characters
  - Number of chunks: {len(chunks)}
  - Average chunk size: {sum(len(c.text) for c in chunks) // len(chunks)} characters
  - Total overlap: {sum(len(chunks[i].text) for i in range(len(chunks)-1)) - len(SAMPLE_DOCUMENT)} characters

Search Results:
  - Query: "{query}"
  - Best matching chunk: Chunk {best_chunk_idx + 1}
  - Relevance score: {best_score} keyword matches
  - Result size: {len(best_chunk.text)} characters

Benefits:
  ✅ No information loss (vs truncation)
  ✅ Precise results (only relevant chunk)
  ✅ Better user experience (less reading)
  ✅ Maintains context (with overlap)
    """)
    
    print_separator()
    print("✅ Demo Complete!")
    print_separator()
    print("\nNext steps:")
    print("  1. Review HOW_CHUNKING_WORKS.md for detailed explanation")
    print("  2. Review CHUNKING_GUIDE.md for implementation guide")
    print("  3. Decide if you want to implement chunking in your system")
    print()

if __name__ == "__main__":
    demo_chunking()
