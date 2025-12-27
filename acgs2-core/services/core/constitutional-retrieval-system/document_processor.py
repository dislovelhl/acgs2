"""
Document Processor for Constitutional Retrieval System

Handles processing, chunking, and vectorization of constitutional documents
and historical precedents using Hugging Face Transformers.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import re
from pathlib import Path
from datetime import datetime, timezone

try:
    from transformers import AutoTokenizer, AutoModel
    from sentence_transformers import SentenceTransformer
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Processes constitutional documents and precedents for vectorization."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize document processor.

        Args:
            model_name: Hugging Face model for embeddings
        """
        self.model_name = model_name
        self.embedding_model = None
        self.tokenizer = None
        self.vector_dim = 384  # Default for all-MiniLM-L6-v2

        if HUGGINGFACE_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(model_name)
                self.vector_dim = self.embedding_model.get_sentence_embedding_dimension()
                logger.info(f"Initialized embedding model: {model_name} (dim: {self.vector_dim})")
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}")
        else:
            logger.warning("Hugging Face transformers not available")

    def process_constitutional_document(self, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a constitutional document into chunks with metadata.

        Args:
            content: Raw document text
            metadata: Document metadata (title, date, type, etc.)

        Returns:
            List of document chunks with metadata
        """
        # Clean and normalize text
        cleaned_content = self._clean_text(content)

        # Split into semantic chunks
        chunks = self._semantic_chunking(cleaned_content)

        # Create chunk objects
        chunk_objects = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_id": f"{metadata.get('doc_id', 'unknown')}_chunk_{i}",
                "chunk_index": i,
                "total_chunks": len(chunks),
                "content_length": len(chunk),
                "processed_at": datetime.now(timezone.utc).isoformat()
            })

            chunk_objects.append({
                "content": chunk,
                "metadata": chunk_metadata
            })

        logger.info(f"Processed document into {len(chunks)} chunks")
        return chunk_objects

    def process_precedent_document(self, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a historical precedent document.

        Args:
            content: Raw precedent text
            metadata: Precedent metadata (case_id, court, date, outcome, etc.)

        Returns:
            List of precedent chunks with metadata
        """
        # Similar to constitutional documents but with precedent-specific processing
        cleaned_content = self._clean_text(content)

        # Extract key sections (facts, reasoning, decision)
        sections = self._extract_precedent_sections(cleaned_content)

        chunk_objects = []
        for section_name, section_content in sections.items():
            if not section_content.strip():
                continue

            chunks = self._semantic_chunking(section_content)

            for i, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "section": section_name,
                    "chunk_id": f"{metadata.get('case_id', 'unknown')}_{section_name}_chunk_{i}",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "content_length": len(chunk),
                    "processed_at": datetime.now(timezone.utc).isoformat()
                })

                chunk_objects.append({
                    "content": chunk,
                    "metadata": chunk_metadata
                })

        logger.info(f"Processed precedent into {len(chunk_objects)} chunks")
        return chunk_objects

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate vector embeddings for text chunks.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        if not self.embedding_model:
            logger.warning("Embedding model not available, returning zero vectors")
            return [[0.0] * self.vector_dim for _ in texts]

        try:
            embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return [[0.0] * self.vector_dim for _ in texts]

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        # Remove page numbers, headers, footers (basic patterns)
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        text = re.sub(r'Page \d+ of \d+', '', text)

        # Normalize quotes
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r'['']', "'", text)

        return text.strip()

    def _semantic_chunking(self, text: str, max_chunk_size: int = 512) -> List[str]:
        """
        Split text into semantic chunks.

        Args:
            text: Input text
            max_chunk_size: Maximum characters per chunk

        Returns:
            List of text chunks
        """
        if len(text) <= max_chunk_size:
            return [text]

        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', text)

        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk + sentence) <= max_chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _extract_precedent_sections(self, text: str) -> Dict[str, str]:
        """
        Extract key sections from precedent documents.

        Args:
            text: Full precedent text

        Returns:
            Dictionary of section name to content
        """
        sections = {
            "facts": "",
            "reasoning": "",
            "decision": "",
            "full_text": text
        }

        # Simple pattern matching for common precedent structures
        # This would need to be enhanced for real legal documents
        text_lower = text.lower()

        # Look for section headers
        fact_patterns = [r'facts?:', r'background:', r'history:']
        reasoning_patterns = [r'reasoning:', r'analysis:', r'consideration:']
        decision_patterns = [r'decision:', r'judgment:', r'ruling:', r'held:']

        # Extract facts section
        for pattern in fact_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                start = match.end()
                # Find next section or end
                next_patterns = reasoning_patterns + decision_patterns
                end = len(text)
                for next_pattern in next_patterns:
                    next_match = re.search(next_pattern, text_lower[start:], re.IGNORECASE)
                    if next_match:
                        end = start + next_match.start()
                        break
                sections["facts"] = text[start:end].strip()
                break

        # Extract reasoning section
        for pattern in reasoning_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                start = match.end()
                end = len(text)
                for next_pattern in decision_patterns:
                    next_match = re.search(next_pattern, text_lower[start:], re.IGNORECASE)
                    if next_match:
                        end = start + next_match.start()
                        break
                sections["reasoning"] = text[start:end].strip()
                break

        # Extract decision section
        for pattern in decision_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                start = match.end()
                sections["decision"] = text[start:].strip()
                break

        return sections

    def load_documents_from_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """
        Load and process all documents from a directory.

        Args:
            directory_path: Path to directory containing documents

        Returns:
            List of processed document chunks
        """
        directory = Path(directory_path)
        if not directory.exists():
            logger.error(f"Directory not found: {directory_path}")
            return []

        all_chunks = []

        # Process different file types
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                try:
                    if file_path.suffix.lower() in ['.txt', '.md']:
                        content = file_path.read_text(encoding='utf-8')
                        metadata = self._extract_file_metadata(file_path)
                        chunks = self.process_constitutional_document(content, metadata)
                        all_chunks.extend(chunks)
                    elif file_path.suffix.lower() == '.json':
                        # Handle JSON structured data
                        import json
                        data = json.loads(file_path.read_text(encoding='utf-8'))
                        if isinstance(data, dict) and 'content' in data:
                            metadata = data.get('metadata', {})
                            metadata['source_file'] = str(file_path)
                            chunks = self.process_constitutional_document(data['content'], metadata)
                            all_chunks.extend(chunks)
                except Exception as e:
                    logger.error(f"Failed to process file {file_path}: {e}")

        logger.info(f"Loaded {len(all_chunks)} chunks from {directory_path}")
        return all_chunks

    def _extract_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from file path and name."""
        metadata = {
            "source_file": str(file_path),
            "filename": file_path.name,
            "file_type": file_path.suffix,
            "doc_id": file_path.stem,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }

        # Try to extract date from filename
        date_match = re.search(r'\d{4}[-_]\d{2}[-_]\d{2}', file_path.name)
        if date_match:
            metadata["date"] = date_match.group().replace('_', '-')

        # Classify document type
        name_lower = file_path.name.lower()
        if 'constitution' in name_lower:
            metadata["doc_type"] = "constitution"
        elif 'precedent' in name_lower or 'case' in name_lower:
            metadata["doc_type"] = "precedent"
        else:
            metadata["doc_type"] = "document"

        return metadata