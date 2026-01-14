"""
Text Chunking Service - Smart chunking for RAG and vector embeddings
Following 2024 best practices for optimal retrieval performance
"""

import logging
import re
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata"""
    text: str
    chunk_index: int
    start_char: int
    end_char: int
    token_count: int
    metadata: Dict = None


class TextChunker:
    """
    Service for chunking text documents for RAG systems
    
    Best practices:
    - 256-512 tokens per chunk (optimal for most use cases)
    - 10-20% overlap between chunks
    - Recursive splitting (paragraphs → sentences → words)
    - Preserve semantic boundaries
    """
    
    def __init__(
        self,
        chunk_size: int = 512,  # tokens
        chunk_overlap: int = 100,  # tokens
        chars_per_token: float = 4.0  # average chars per token
    ):
        """
        Initialize chunker with configurable parameters
        
        Args:
            chunk_size: Target chunk size in tokens (default: 512)
            chunk_overlap: Overlap between chunks in tokens (default: 100)
            chars_per_token: Average characters per token (default: 4.0)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chars_per_token = chars_per_token
        
        # Convert to characters for splitting
        self.chunk_size_chars = int(chunk_size * chars_per_token)
        self.overlap_chars = int(chunk_overlap * chars_per_token)
        
        logger.info(
            f"TextChunker initialized: {chunk_size} tokens "
            f"({self.chunk_size_chars} chars) with {chunk_overlap} token overlap"
        )
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from text"""
        return int(len(text) / self.chars_per_token)
    
    def chunk_by_paragraphs(self, text: str) -> List[TextChunk]:
        """
        Chunk text by paragraphs with overlap
        Best for: General documents, articles, documentation
        """
        # Split by paragraphs (double newline)
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = ""
        current_start = 0
        chunk_index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Check if adding this paragraph exceeds chunk size
            potential_chunk = current_chunk + "\n\n" + para if current_chunk else para
            
            if len(potential_chunk) > self.chunk_size_chars and current_chunk:
                # Save current chunk
                chunks.append(TextChunk(
                    text=current_chunk.strip(),
                    chunk_index=chunk_index,
                    start_char=current_start,
                    end_char=current_start + len(current_chunk),
                    token_count=self.estimate_tokens(current_chunk)
                ))
                
                # Start new chunk with overlap
                # Take last N chars from current chunk for overlap
                overlap_text = current_chunk[-self.overlap_chars:] if len(current_chunk) > self.overlap_chars else current_chunk
                current_chunk = overlap_text + "\n\n" + para
                current_start = current_start + len(current_chunk) - len(overlap_text)
                chunk_index += 1
            else:
                current_chunk = potential_chunk
        
        # Add final chunk
        if current_chunk:
            chunks.append(TextChunk(
                text=current_chunk.strip(),
                chunk_index=chunk_index,
                start_char=current_start,
                end_char=current_start + len(current_chunk),
                token_count=self.estimate_tokens(current_chunk)
            ))
        
        return chunks
    
    def chunk_by_sentences(self, text: str) -> List[TextChunk]:
        """
        Chunk text by sentences with overlap
        Best for: FAQ, Q&A, precise fact retrieval
        """
        # Split by sentences (simple regex)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        current_start = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(potential_chunk) > self.chunk_size_chars and current_chunk:
                # Save current chunk
                chunks.append(TextChunk(
                    text=current_chunk.strip(),
                    chunk_index=chunk_index,
                    start_char=current_start,
                    end_char=current_start + len(current_chunk),
                    token_count=self.estimate_tokens(current_chunk)
                ))
                
                # Start new chunk with overlap (last few sentences)
                sentences_in_chunk = current_chunk.split('. ')
                overlap_sentences = sentences_in_chunk[-2:] if len(sentences_in_chunk) > 2 else sentences_in_chunk
                overlap_text = '. '.join(overlap_sentences)
                
                current_chunk = overlap_text + " " + sentence
                current_start = current_start + len(current_chunk) - len(overlap_text)
                chunk_index += 1
            else:
                current_chunk = potential_chunk
        
        # Add final chunk
        if current_chunk:
            chunks.append(TextChunk(
                text=current_chunk.strip(),
                chunk_index=chunk_index,
                start_char=current_start,
                end_char=current_start + len(current_chunk),
                token_count=self.estimate_tokens(current_chunk)
            ))
        
        return chunks
    
    def chunk_recursive(self, text: str) -> List[TextChunk]:
        """
        Recursive chunking - tries to split at natural boundaries
        Priority: Paragraphs → Sentences → Words → Characters
        Best for: Most general use cases (RECOMMENDED)
        """
        separators = [
            "\n\n",  # Paragraphs
            "\n",    # Lines
            ". ",    # Sentences
            "! ",    # Exclamations
            "? ",    # Questions
            "; ",    # Semicolons
            ", ",    # Commas
            " ",     # Words
            ""       # Characters
        ]
        
        return self._recursive_split(text, separators, 0, 0, 0)
    
    def _recursive_split(
        self,
        text: str,
        separators: List[str],
        sep_index: int,
        start_char: int,
        chunk_index: int
    ) -> List[TextChunk]:
        """Helper for recursive splitting"""
        
        if not text or len(text) <= self.chunk_size_chars:
            if text.strip():
                return [TextChunk(
                    text=text.strip(),
                    chunk_index=chunk_index,
                    start_char=start_char,
                    end_char=start_char + len(text),
                    token_count=self.estimate_tokens(text)
                )]
            return []
        
        # Try current separator
        if sep_index >= len(separators):
            # No more separators, force split
            chunks = []
            for i in range(0, len(text), self.chunk_size_chars - self.overlap_chars):
                chunk_text = text[i:i + self.chunk_size_chars]
                if chunk_text.strip():
                    chunks.append(TextChunk(
                        text=chunk_text.strip(),
                        chunk_index=len(chunks),
                        start_char=start_char + i,
                        end_char=start_char + i + len(chunk_text),
                        token_count=self.estimate_tokens(chunk_text)
                    ))
            return chunks
        
        separator = separators[sep_index]
        splits = text.split(separator) if separator else [text]
        
        chunks = []
        current_chunk = ""
        current_pos = start_char
        
        for split in splits:
            potential = current_chunk + separator + split if current_chunk else split
            
            if len(potential) > self.chunk_size_chars and current_chunk:
                # Current chunk is full, save it
                chunks.append(TextChunk(
                    text=current_chunk.strip(),
                    chunk_index=len(chunks),
                    start_char=current_pos,
                    end_char=current_pos + len(current_chunk),
                    token_count=self.estimate_tokens(current_chunk)
                ))
                
                # Add overlap
                overlap_size = min(self.overlap_chars, len(current_chunk))
                overlap_text = current_chunk[-overlap_size:]
                current_chunk = overlap_text + separator + split
                current_pos = current_pos + len(current_chunk) - overlap_size
            else:
                current_chunk = potential
        
        # Handle remaining text
        if current_chunk.strip():
            if len(current_chunk) > self.chunk_size_chars:
                # Still too large, try next separator
                sub_chunks = self._recursive_split(
                    current_chunk,
                    separators,
                    sep_index + 1,
                    current_pos,
                    len(chunks)
                )
                chunks.extend(sub_chunks)
            else:
                chunks.append(TextChunk(
                    text=current_chunk.strip(),
                    chunk_index=len(chunks),
                    start_char=current_pos,
                    end_char=current_pos + len(current_chunk),
                    token_count=self.estimate_tokens(current_chunk)
                ))
        
        return chunks
    
    def chunk_text(
        self,
        text: str,
        strategy: str = "recursive",
        metadata: Optional[Dict] = None
    ) -> List[TextChunk]:
        """
        Main chunking method - choose strategy
        
        Args:
            text: Text to chunk
            strategy: Chunking strategy ('recursive', 'paragraphs', 'sentences')
            metadata: Optional metadata to attach to chunks
            
        Returns:
            List of TextChunk objects
        """
        if not text or not text.strip():
            return []
        
        # Choose strategy
        if strategy == "paragraphs":
            chunks = self.chunk_by_paragraphs(text)
        elif strategy == "sentences":
            chunks = self.chunk_by_sentences(text)
        else:  # recursive (default)
            chunks = self.chunk_recursive(text)
        
        # Add metadata to chunks
        if metadata:
            for chunk in chunks:
                chunk.metadata = metadata
        
        logger.info(
            f"Chunked text into {len(chunks)} chunks using '{strategy}' strategy. "
            f"Avg tokens per chunk: {sum(c.token_count for c in chunks) / len(chunks):.0f}"
        )
        
        return chunks


# Singleton instance with default settings
text_chunker = TextChunker(
    chunk_size=512,      # 512 tokens (~2000 chars) - optimal for most use cases
    chunk_overlap=100,   # 100 tokens (~400 chars) - 20% overlap
    chars_per_token=4.0  # Average for English text
)
