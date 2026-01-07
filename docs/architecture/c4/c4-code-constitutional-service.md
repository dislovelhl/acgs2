# C4 Code Level: Constitutional Retrieval Service

## Overview

- **Name**: Core Constitutional Retrieval Service
- **Description**: Constitutional AI validation engine implementing Retrieval-Augmented Generation (RAG) with vector-based semantic search, LLM-powered reasoning, and multi-agent coordination for real-time constitutional compliance checking and decision support
- **Location**: `/home/dislove/document/acgs2/src/core/services/core/constitutional-retrieval-system/`
- **Language**: Python 3.11-3.13 with async/await patterns
- **Purpose**: Provides intelligent retrieval and reasoning capabilities for constitutional compliance validation, precedent analysis, and enhanced decision-making in fuzzy governance scenarios. Supports multi-agent collaboration through shared vector knowledge base infrastructure.
- **Constitutional Hash**: `cdd01ef066bc6cf2`

## Architecture Overview

The Constitutional Retrieval Service implements a sophisticated **Retrieval-Augmented Generation (RAG)** architecture combining:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Multi-Agent    │    │   Retrieval     │    │     LLM         │
│ Coordinator     │◄──►│    Engine       │◄──►│   Reasoner      │
│                 │    │   (RAG)         │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                       ▲                       ▲
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Feedback      │    │  Document       │    │  Vector         │
│    Loop         │    │ Processor       │    │ Database        │
│                 │    │                  │    │ (Qdrant/Milvus)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## Code Elements

### Core Modules and Classes

#### 1. **VectorDatabaseManager** (Abstract Base Class)
- **File**: `vector_database.py` (lines 31-86)
- **Type**: Abstract Base Class
- **Purpose**: Unified interface for vector database operations supporting multiple backends
- **Key Methods**:
  - `connect() -> bool` - Establish database connection
  - `disconnect() -> None` - Close database connection
  - `create_collection(collection_name: str, vector_dim: int) -> bool` - Create vector collection
  - `insert_vectors(collection_name: str, vectors: List[List[float]], payloads: List[Dict], ids: Optional[List[str]]) -> bool` - Insert vectors with metadata
  - `search_vectors(collection_name: str, query_vector: List[float], limit: int, filter_dict: Optional[Dict]) -> List[Dict]` - Semantic vector search
  - `delete_vectors(collection_name: str, ids: List[str]) -> bool` - Remove vectors
  - `update_vectors(collection_name: str, ids: List[str], vectors: List[List[float]], payloads: List[Dict]) -> bool` - Update existing vectors
- **Responsibilities**:
  - Define CRUD interface for vector operations
  - Enable pluggable backend implementations (Qdrant, Milvus, Mock)
  - Provide consistent API across vector database systems

#### 2. **QdrantManager** (VectorDatabaseManager Implementation)
- **File**: `vector_database.py` (lines 88-223)
- **Type**: Concrete Class
- **Purpose**: Production-grade Qdrant vector database backend
- **Key Methods**:
  - `connect() -> bool` (lines 97-111) - Connect to Qdrant server at `host:port`
  - `create_collection(collection_name: str, vector_dim: int) -> bool` (lines 120-134) - Create collection with COSINE distance metric
  - `insert_vectors(...) -> bool` (lines 136-158) - Batch insert vectors as Qdrant points
  - `search_vectors(...) -> List[Dict]` (lines 160-186) - Vector similarity search with filtering
  - `delete_vectors(collection_name: str, ids: List[str]) -> bool` (lines 188-199) - Delete vectors by ID
  - `update_vectors(...) -> bool` (lines 201-222) - Upsert vectors (update or insert)
- **Dependencies**: `qdrant_client`, `Distance`, `VectorParams`
- **Responsibilities**:
  - Manage connections to Qdrant database
  - Execute vector operations on Qdrant backend
  - Handle error recovery and logging

#### 3. **MilvusManager** (VectorDatabaseManager Implementation)
- **File**: `vector_database.py` (lines 225-382)
- **Type**: Concrete Class
- **Purpose**: Alternative Milvus vector database backend for distributed deployments
- **Key Methods**:
  - `connect() -> bool` (lines 233-245) - Establish Milvus connection
  - `create_collection(collection_name: str, vector_dim: int) -> bool` (lines 255-279) - Create collection with IVF_FLAT index
  - `insert_vectors(...) -> bool` (lines 281-304) - Batch insert with JSON payload support
  - `search_vectors(...) -> List[Dict]` (lines 306-350) - HNSW-optimized similarity search
  - `delete_vectors(collection_name: str, ids: List[str]) -> bool` (lines 352-362) - Expression-based deletion
  - `update_vectors(...) -> bool` (lines 364-381) - Delete and re-insert pattern for updates
- **Dependencies**: `pymilvus` (Collection, Schema, FieldSchema, DataType)
- **Responsibilities**:
  - Manage distributed Milvus connections
  - Support complex filtering with Milvus expressions
  - Implement efficient vector indexing strategies

#### 4. **MockVectorManager** (VectorDatabaseManager Implementation)
- **File**: `vector_database.py` (lines 384-437)
- **Type**: Concrete Class (Testing/Development)
- **Purpose**: In-memory mock implementation for testing and development
- **Key Methods**:
  - All VectorDatabaseManager abstract methods implemented with memory-based operations
- **Responsibilities**:
  - Provide fast testing without database dependencies
  - Enable unit testing of retrieval pipelines

#### 5. **create_vector_db_manager()** (Factory Function)
- **File**: `vector_database.py` (lines 440-449)
- **Signature**: `create_vector_db_manager(db_type: str = "qdrant", **kwargs) -> VectorDatabaseManager`
- **Purpose**: Factory pattern for instantiating appropriate vector database manager
- **Logic**:
  - Maps `db_type` parameter to implementation class
  - Supports: "qdrant", "milvus", "mock"
  - Raises `ValueError` for unknown types

---

#### 6. **DocumentProcessor**
- **File**: `document_processor.py` (lines 25-327)
- **Type**: Concrete Class
- **Purpose**: Processes constitutional documents and precedents for vectorization
- **Key Methods**:
  - `__init__(model_name: str = "sentence-transformers/all-MiniLM-L6-v2")` (lines 28-48) - Initialize with Hugging Face embedding model (384-dim vectors)
  - `process_constitutional_document(content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]` (lines 50-86) - Process constitutional documents into semantic chunks with metadata
  - `process_precedent_document(content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]` (lines 88-130) - Process precedent documents with section extraction (Facts, Reasoning, Decision)
  - `generate_embeddings(texts: List[str]) -> List[List[float]]` (lines 132-151) - Generate vector embeddings using Sentence Transformers
  - `load_documents_from_directory(directory_path: str) -> List[Dict[str, Any]]` (lines 260-300) - Load and process all documents (.txt, .md, .json) from directory
- **Private Methods**:
  - `_clean_text(text: str) -> str` (lines 153-166) - Normalize whitespace, remove artifacts
  - `_semantic_chunking(text: str, max_chunk_size: int = 512) -> List[str]` (lines 168-197) - Split text into semantic chunks by sentence boundaries
  - `_extract_precedent_sections(text: str) -> Dict[str, str]` (lines 199-258) - Extract Facts, Reasoning, Decision sections from precedent text
  - `_extract_file_metadata(file_path: Path) -> Dict[str, Any]` (lines 302-326) - Extract metadata from file path and name
- **Dependencies**: `sentence_transformers` (SentenceTransformer)
- **Responsibilities**:
  - Convert raw documents to embeddings
  - Intelligent document chunking for optimal semantic representation
  - Metadata enrichment and document classification
  - Support for multiple document formats

---

#### 7. **RetrievalEngine**
- **File**: `retrieval_engine.py` (lines 21-368)
- **Type**: Concrete Class
- **Purpose**: RAG engine for retrieving and ranking constitutional documents and precedents
- **Key Methods**:
  - `__init__(vector_db: VectorDatabaseManager, doc_processor: DocumentProcessor)` (lines 24-34) - Initialize with database and processor
  - `initialize_collections() -> bool` (lines 36-46) - Create vector database collections
  - `index_documents(documents: List[Dict[str, Any]]) -> bool` (lines 48-84) - Index document chunks into vector database
  - `retrieve_similar_documents(query: str, limit: int = 5, filters: Optional[Dict]) -> List[Dict[str, Any]]` (lines 86-126) - Semantic search with relevance scoring
  - `retrieve_precedents_for_case(case_description: str, legal_domain: Optional[str], limit: int = 10) -> List[Dict[str, Any]]` (lines 128-165) - Retrieve legal precedents with domain filtering
  - `retrieve_constitutional_provisions(query: str, constitutional_rights: Optional[List[str]], limit: int = 5) -> List[Dict[str, Any]]` (lines 167-202) - Retrieve constitutional provisions with rights filtering
  - `hybrid_search(query: str, keyword_filters: Optional[List[str]], semantic_weight: float = 0.7, keyword_weight: float = 0.3, limit: int = 10) -> List[Dict[str, Any]]` (lines 204-256) - Combined semantic and keyword search with configurable weighting
  - `get_collection_stats() -> Dict[str, Any]` (lines 359-367) - Get collection statistics
- **Private Methods**:
  - `_calculate_relevance_score(query: str, result: Dict) -> float` (lines 258-278) - Multi-factor relevance scoring with authority and recency boosts
  - `_calculate_recency_boost(date_str: Optional[str]) -> float` (lines 280-299) - Boost scores based on document age (1.3x for <1yr, 1.1x for <5yr, 0.9x otherwise)
  - `_calculate_authority_boost(payload: Dict) -> float` (lines 301-316) - Boost by court level (1.5x Supreme, 1.2x Appeal) and source authority (1.3x Official)
  - `_analyze_precedent_relevance(case_description: str, precedent: Dict) -> float` (lines 318-336) - Keyword overlap analysis for precedent relevance
  - `_calculate_keyword_score(query: str, result: Dict, keyword_filters: Optional[List[str]]) -> float` (lines 338-357) - Compute keyword match scores
- **Responsibilities**:
  - Semantic and hybrid search across constitutional documents
  - Multi-factor relevance ranking (semantic similarity, authority, recency)
  - Precedent retrieval with domain-specific filtering
  - Constitutional provision targeting

---

#### 8. **LLMReasoner**
- **File**: `llm_reasoner.py` (lines 27-502)
- **Type**: Concrete Class
- **Purpose**: LLM-powered reasoning engine for enhanced decision support using retrieved context
- **Key Methods**:
  - `__init__(retrieval_engine: RetrievalEngine, openai_api_key: Optional[str], model_name: str = "gpt-4")` (lines 30-59) - Initialize ChatOpenAI with low temperature (0.1) for consistent legal reasoning
  - `reason_with_context(query: str, context_documents: List[Dict[str, Any]], decision_criteria: Optional[Dict[str, Any]]) -> Dict[str, Any]` (lines 61-151) - Perform structured reasoning with constitutional context, returning recommendation, confidence, key factors, and counterarguments
  - `analyze_precedent_conflict(case_description: str, conflicting_precedents: List[Dict[str, Any]]) -> Dict[str, Any]` (lines 153-227) - Analyze conflicts between multiple precedents and recommend reconciliation approach
  - `generate_decision_explanation(decision: Dict[str, Any], context_used: List[Dict[str, Any]]) -> str` (lines 229-291) - Generate human-readable explanation of legal decision
  - `assess_decision_consistency(decision: Dict[str, Any], historical_decisions: List[Dict[str, Any]]) -> Dict[str, Any]` (lines 293-363) - Check consistency with historical decisions and identify patterns
- **Private Methods**:
  - `_summarize_context(documents: List[Dict]) -> str` (lines 365-380) - Summarize top 5 documents for LLM context
  - `_format_decision_criteria(criteria: Optional[Dict]) -> str` (lines 382-391) - Format criteria for LLM prompt
  - `_summarize_precedent(precedent: Dict) -> str` (lines 393-401) - Summarize precedent for analysis
  - `_fallback_reasoning(...)` (lines 403-435) - Rule-based fallback when LLM unavailable
  - `_fallback_conflict_analysis(...)` (lines 437-451) - Simple conflict detection fallback
  - `_fallback_explanation(...)` (lines 453-469) - Basic explanation generation fallback
  - `_fallback_consistency_check(...)` (lines 471-501) - Simple consistency scoring fallback
- **Dependencies**: `langchain_openai.ChatOpenAI`, `langchain_core` prompting and parsing
- **Responsibilities**:
  - Structured LLM reasoning with JSON output parsing
  - Constitutional and legal analysis with precedent application
  - Decision consistency validation
  - Explainability for governance decisions
  - Graceful fallback to rule-based reasoning

---

#### 9. **FeedbackLoop**
- **File**: `feedback_loop.py` (lines 20-453)
- **Type**: Concrete Class
- **Purpose**: Feedback collection and continuous improvement mechanism for knowledge base optimization
- **Key Methods**:
  - `__init__(vector_db: VectorDatabaseManager, doc_processor: DocumentProcessor, retrieval_engine: RetrievalEngine)` (lines 23-48) - Initialize with minimum feedback threshold (5) and update interval (7 days)
  - `collect_decision_feedback(query: str, retrieved_documents: List[Dict], decision: Dict[str, Any], user_feedback: Optional[Dict]) -> str` (lines 50-90) - Collect feedback with retrieval quality assessment and auto-trigger updates
  - `update_index_from_feedback() -> Dict[str, Any]` (lines 92-134) - Analyze patterns and apply index updates
  - `add_new_knowledge(documents: List[Dict[str, Any]], source: str = "manual") -> bool` (lines 136-170) - Add new documents to knowledge base
  - `get_performance_metrics() -> Dict[str, Any]` (lines 172-190) - Return current performance metrics
  - `optimize_retrieval_parameters() -> Dict[str, Any]` (lines 192-218) - Generate parameter optimization recommendations
- **Private Methods**:
  - `_assess_retrieval_quality(documents: List[Dict], decision: Dict) -> Dict[str, Any]` (lines 220-245) - Assess document relevance and identify issues
  - `_analyze_feedback_patterns() -> Dict[str, Any]` (lines 247-290) - Aggregate feedback statistics and patterns
  - `_generate_index_updates(feedback_analysis: Dict) -> List[Dict[str, Any]]` (lines 292-330) - Generate update recommendations based on patterns
  - `_apply_index_updates(updates: List[Dict[str, Any]]) -> Dict[str, Any]` (lines 332-364) - Execute update operations
  - `_update_performance_metrics(...)` (lines 366-379) - Update internal metrics
  - `_check_and_trigger_update() -> None` (lines 381-390) - Auto-trigger updates when thresholds met
  - `_analyze_retrieval_performance() -> Dict[str, Any]` (lines 392-425) - Calculate performance statistics
  - `_generate_parameter_recommendations(performance: Dict) -> Dict[str, Any]` (lines 427-452) - Recommend parameter adjustments
- **Responsibilities**:
  - Collect and analyze user feedback on decisions
  - Identify quality issues and gaps in knowledge base
  - Recommend and apply index optimizations
  - Track performance metrics and trends
  - Support continuous improvement cycle

---

#### 10. **MultiAgentCoordinator**
- **File**: `multi_agent_coordinator.py` (lines 20-150+)
- **Type**: Concrete Class
- **Purpose**: Enable multiple agents to collaborate through shared vector knowledge base
- **Key Methods**:
  - `__init__(vector_db: VectorDatabaseManager, retrieval_engine: RetrievalEngine, llm_reasoner: LLMReasoner, feedback_loop: FeedbackLoop)` (lines 23-61) - Initialize coordinator with component references and settings (max 10 concurrent agents, 30-minute timeout)
  - `register_agent(agent_id: str, agent_info: Dict[str, Any]) -> bool` (lines 63-107) - Register agent with type, capabilities, and permissions validation
  - `start_collaboration_session(agent_id: str, session_purpose: str) -> Optional[str]` (lines 109-150+) - Start named session with up to 3 concurrent per agent
- **Public Attributes**:
  - `registered_agents: Dict[str, Dict[str, Any]]` - Registry of active agents with metadata
  - `active_sessions: Dict[str, Dict[str, Any]]` - Current collaboration sessions
  - `knowledge_permissions: Dict[str, Set[str]]` - Access control per agent (read/write)
  - `collaboration_metrics: Dict[str, Any]` - Tracks total agents, active sessions, queries, contributions
- **Responsibilities**:
  - Multi-agent service discovery and lifecycle management
  - Session creation and timeout management
  - Knowledge base access control (read/write permissions)
  - Collaboration metrics tracking
  - Shared resource coordination

---

### Function Signatures Summary

| Function | Module | Signature | Returns | Purpose |
|----------|--------|-----------|---------|---------|
| `create_vector_db_manager` | vector_database | `(db_type: str = "qdrant", **kwargs) -> VectorDatabaseManager` | Manager instance | Factory for vector DB selection |
| `process_constitutional_document` | document_processor | `(content: str, metadata: Dict) -> List[Dict]` | Chunked documents | Convert raw constitutional docs to chunks |
| `process_precedent_document` | document_processor | `(content: str, metadata: Dict) -> List[Dict]` | Chunked precedents | Extract and chunk precedent sections |
| `generate_embeddings` | document_processor | `(texts: List[str]) -> List[List[float]]` | Embedding vectors | Generate 384-dim embeddings |
| `initialize_collections` | retrieval_engine | `() -> bool` | Success status | Create database collections |
| `index_documents` | retrieval_engine | `(documents: List[Dict]) -> bool` | Success status | Insert documents into index |
| `retrieve_similar_documents` | retrieval_engine | `(query: str, limit: int = 5, filters: Optional[Dict]) -> List[Dict]` | Ranked results | Semantic document search |
| `retrieve_precedents_for_case` | retrieval_engine | `(case_desc: str, legal_domain: Optional[str], limit: int = 10) -> List[Dict]` | Precedent list | Find relevant legal precedents |
| `retrieve_constitutional_provisions` | retrieval_engine | `(query: str, rights: Optional[List[str]], limit: int = 5) -> List[Dict]` | Provisions | Find constitutional articles |
| `hybrid_search` | retrieval_engine | `(query: str, keywords: Optional[List[str]], semantic_w: float = 0.7, keyword_w: float = 0.3, limit: int = 10) -> List[Dict]` | Hybrid results | Combined semantic + keyword search |
| `reason_with_context` | llm_reasoner | `(query: str, context: List[Dict], criteria: Optional[Dict]) -> Dict` | Reasoning result | LLM-enhanced decision reasoning |
| `analyze_precedent_conflict` | llm_reasoner | `(case: str, precedents: List[Dict]) -> Dict` | Conflict analysis | Reconcile conflicting precedents |
| `generate_decision_explanation` | llm_reasoner | `(decision: Dict, context: List[Dict]) -> str` | Explanation text | Human-readable decision justification |
| `assess_decision_consistency` | llm_reasoner | `(decision: Dict, history: List[Dict]) -> Dict` | Consistency report | Check historical alignment |
| `collect_decision_feedback` | feedback_loop | `(query: str, docs: List[Dict], decision: Dict, feedback: Optional[Dict]) -> str` | Feedback ID | Record decision feedback |
| `update_index_from_feedback` | feedback_loop | `() -> Dict` | Update results | Apply feedback-driven optimizations |
| `add_new_knowledge` | feedback_loop | `(documents: List[Dict], source: str = "manual") -> bool` | Success status | Add new knowledge documents |
| `optimize_retrieval_parameters` | feedback_loop | `() -> Dict` | Recommendations | Suggest parameter tuning |
| `register_agent` | multi_agent_coordinator | `(agent_id: str, info: Dict) -> bool` | Success status | Register collaborative agent |
| `start_collaboration_session` | multi_agent_coordinator | `(agent_id: str, purpose: str) -> Optional[str]` | Session ID | Initiate agent session |

---

## Dependencies

### Internal Dependencies

1. **Vector Database Layer**:
   - Cross-module imports: `from vector_database import VectorDatabaseManager`
   - Used by: `RetrievalEngine`, `FeedbackLoop`, `MultiAgentCoordinator`

2. **Document Processing**:
   - Cross-module imports: `from document_processor import DocumentProcessor`
   - Used by: `RetrievalEngine`, `FeedbackLoop`, `MultiAgentCoordinator`

3. **Retrieval Engine**:
   - Cross-module imports: `from retrieval_engine import RetrievalEngine`
   - Used by: `LLMReasoner`, `FeedbackLoop`, `MultiAgentCoordinator`

4. **LLM Reasoner**:
   - Cross-module imports: `from llm_reasoner import LLMReasoner`
   - Used by: `MultiAgentCoordinator`

5. **Feedback Loop**:
   - Cross-module imports: `from feedback_loop import FeedbackLoop`
   - Used by: `MultiAgentCoordinator`

### External Dependencies

#### Core Libraries
- **langchain-openai** (>= 0.1.0) - ChatOpenAI LLM integration with streaming support
- **langchain-core** (>= 0.1.0) - Prompting, output parsing (JsonOutputParser, ChatPromptTemplate)

#### Embeddings & NLP
- **sentence-transformers** (>= 2.2.0) - Pre-trained embedding models (all-MiniLM-L6-v2, 384-dimensional vectors)
- **transformers** (>= 4.30.0) - Hugging Face model hub integration

#### Vector Databases
- **qdrant-client** (>= 2.4.0) - Qdrant vector database client with COSINE distance support
- **pymilvus** (>= 2.3.0) - Milvus vector database client with IVF_FLAT indexing

#### Standard Library
- **logging** - Structured logging throughout modules
- **datetime** - Timestamp and date operations with timezone awareness
- **typing** - Type hints (TYPE_CHECKING, Optional, Dict, List, Any)
- **pathlib** - Path operations for document loading
- **re** - Regular expressions for text processing and extraction
- **json** - JSON file handling in document processor
- **collections** - defaultdict for statistics aggregation
- **abc** - Abstract base classes for VectorDatabaseManager

#### Optional Dependencies (Graceful Degradation)
- LangChain components optional with `LANGCHAIN_AVAILABLE` flag
- Hugging Face models optional with `HUGGINGFACE_AVAILABLE` flag
- Vector database clients optional with `QDRANT_AVAILABLE`, `MILVUS_AVAILABLE` flags

---

## Code-Level Relationships

### Composition & Dependency Hierarchy

```mermaid
---
title: Code Relationships - Constitutional Retrieval Service
---
classDiagram
    namespace "Vector Database Layer" {
        class VectorDatabaseManager {
            <<abstract>>
            +connect() bool
            +disconnect() void
            +create_collection() bool
            +insert_vectors() bool
            +search_vectors() List
            +delete_vectors() bool
            +update_vectors() bool
        }
        class QdrantManager {
            -host: str
            -port: int
            -client: QdrantClient
        }
        class MilvusManager {
            -host: str
            -port: str
            -connection_alias: str
        }
        class MockVectorManager {
            -vectors: Dict
        }
    }

    namespace "Document Processing" {
        class DocumentProcessor {
            -embedding_model: SentenceTransformer
            -vector_dim: int = 384
            +process_constitutional_document() List
            +process_precedent_document() List
            +generate_embeddings() List
            +load_documents_from_directory() List
        }
    }

    namespace "Retrieval & Reasoning" {
        class RetrievalEngine {
            -vector_db: VectorDatabaseManager
            -doc_processor: DocumentProcessor
            -collection_name: str
            +initialize_collections() bool
            +index_documents() bool
            +retrieve_similar_documents() List
            +retrieve_precedents_for_case() List
            +retrieve_constitutional_provisions() List
            +hybrid_search() List
        }
        class LLMReasoner {
            -retrieval_engine: RetrievalEngine
            -llm: ChatOpenAI
            -model_name: str
            +reason_with_context() Dict
            +analyze_precedent_conflict() Dict
            +generate_decision_explanation() str
            +assess_decision_consistency() Dict
        }
    }

    namespace "Feedback & Optimization" {
        class FeedbackLoop {
            -vector_db: VectorDatabaseManager
            -doc_processor: DocumentProcessor
            -retrieval_engine: RetrievalEngine
            -feedback_history: List
            -performance_metrics: Dict
            +collect_decision_feedback() str
            +update_index_from_feedback() Dict
            +add_new_knowledge() bool
            +get_performance_metrics() Dict
            +optimize_retrieval_parameters() Dict
        }
    }

    namespace "Multi-Agent Coordination" {
        class MultiAgentCoordinator {
            -vector_db: VectorDatabaseManager
            -retrieval_engine: RetrievalEngine
            -llm_reasoner: LLMReasoner
            -feedback_loop: FeedbackLoop
            -registered_agents: Dict
            -active_sessions: Dict
            +register_agent() bool
            +start_collaboration_session() Optional~str~
        }
    }

    VectorDatabaseManager <|-- QdrantManager
    VectorDatabaseManager <|-- MilvusManager
    VectorDatabaseManager <|-- MockVectorManager

    RetrievalEngine --> VectorDatabaseManager
    RetrievalEngine --> DocumentProcessor

    LLMReasoner --> RetrievalEngine

    FeedbackLoop --> VectorDatabaseManager
    FeedbackLoop --> DocumentProcessor
    FeedbackLoop --> RetrievalEngine

    MultiAgentCoordinator --> VectorDatabaseManager
    MultiAgentCoordinator --> RetrievalEngine
    MultiAgentCoordinator --> LLMReasoner
    MultiAgentCoordinator --> FeedbackLoop
```

### Data Flow Architecture

```
┌─────────────────────┐
│  Constitutional     │
│  Documents &        │
│  Precedents         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────┐
│  Document Processor             │
│  - Clean & normalize text       │
│  - Semantic chunking (512 chars)│
│  - Extract precedent sections   │
│  - Generate embeddings (384-dim)│
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  Vector Database                │
│  (Qdrant/Milvus)                │
│  - Store embeddings + metadata  │
│  - COSINE similarity indexing   │
│  - Support filtering & updates  │
└──────────┬──────────────────────┘
           │
           ├─────────────────────────────────┐
           │                                 │
           ▼                                 ▼
┌─────────────────────┐        ┌──────────────────────────┐
│  Retrieval Engine   │        │   Feedback Loop          │
│  - Semantic search  │        │   - Collect feedback     │
│  - Hybrid search    │        │   - Analyze patterns     │
│  - Relevance boost  │        │   - Generate updates     │
│  - Authority filter │        │   - Optimize parameters  │
└────────┬────────────┘        └──────────┬───────────────┘
         │                                │
         └────────────┬───────────────────┘
                      │
                      ▼
         ┌──────────────────────────┐
         │   LLM Reasoner           │
         │   - Structured reasoning │
         │   - Precedent analysis   │
         │   - Consistency check    │
         │   - Explanation gen.     │
         └────────┬─────────────────┘
                  │
                  ▼
         ┌──────────────────────────┐
         │  Decision + Confidence   │
         │  + Key Factors           │
         │  + Reasoning Trace       │
         └──────────────────────────┘
```

### Type Flow Analysis

**Query Processing Pipeline**:
```
str (query)
  │
  ├─→ DocumentProcessor.generate_embeddings()
  │     └─→ List[float] (384-dim query vector)
  │
  └─→ RetrievalEngine.retrieve_similar_documents()
      ├─→ VectorDatabaseManager.search_vectors()
      │   └─→ List[Dict{id, score, payload}]
      │
      └─→ List[Dict] (enhanced_results with relevance_score)
          │
          └─→ LLMReasoner.reason_with_context()
              └─→ Dict{recommendation, confidence, key_factors, ...}
```

---

## Data Structures

### Document Chunk Structure
```python
{
    "content": str,  # Text chunk (512 chars max)
    "metadata": {
        "chunk_id": str,        # Unique identifier
        "chunk_index": int,     # Position in document
        "total_chunks": int,    # Document chunk count
        "content_length": int,  # Chunk character count
        "processed_at": str,    # ISO datetime
        "doc_type": str,        # "constitution", "precedent", "document"
        "date": str,            # Document date if found
        # Additional: title, source_file, court, legal_domain, etc.
    }
}
```

### Search Result Structure
```python
{
    "id": str,                  # Vector ID
    "score": float,             # Similarity score (0-1)
    "payload": Dict,            # Metadata
    "relevance_score": float,   # Computed relevance (with boosts)
    "precedent_relevance": float,  # Precedent-specific relevance
    "hybrid_score": float       # Semantic + keyword combined
}
```

### Reasoning Result Structure
```python
{
    "issue_summary": str,
    "constitutional_analysis": str,
    "precedent_application": str,
    "recommendation": str,      # "approve" | "deny" | "further_review"
    "confidence": float,        # 0.0-1.0
    "key_factors": List[str],
    "counterarguments": List[str],
    "reasoning_trace": str,
    "reasoned_by": str,         # "llm_reasoner" | "fallback_reasoner"
    "model": str,               # "gpt-4" if LLM used
    "timestamp": str,           # ISO datetime
}
```

### Feedback Entry Structure
```python
{
    "feedback_id": str,
    "timestamp": str,
    "query": str,
    "documents_retrieved": int,
    "decision": Dict,
    "user_feedback": Dict,
    "retrieval_quality": {
        "quality_score": float,
        "average_score": float,
        "high_relevance_count": int,
        "total_documents": int,
        "issues": List[str]
    },
    "decision_confidence": float,
    "processed": bool
}
```

### Agent Registration Structure
```python
{
    "agent_id": str,
    "agent_type": str,          # e.g., "constitutional_expert"
    "capabilities": List[str],  # ["constitutional_analysis", ...]
    "permissions": Set[str],    # ["read", "write"]
    "registered_at": str,       # ISO datetime
    "last_active": str,         # ISO datetime
    "status": str               # "active", "inactive"
}
```

### Session Structure
```python
{
    "session_id": str,
    "agent_id": str,
    "purpose": str,
    "started_at": str,          # ISO datetime
    "status": str,              # "active", "completed", "timeout"
    "queries_made": int,
    "knowledge_accessed": List[str]
}
```

---

## Performance Characteristics

### Embedding Generation
- **Model**: sentence-transformers/all-MiniLM-L6-v2
- **Vector Dimension**: 384
- **Inference Time**: ~5ms per document chunk (async)
- **Memory**: ~100MB for model weights

### Vector Search
- **Qdrant**: COSINE distance metric, GPU acceleration optional
- **Milvus**: IVF_FLAT index with ~1ms query latency
- **Expected Retrieval**: <100ms for 1M vectors

### LLM Reasoning
- **Model**: gpt-4 (temperature=0.1 for consistency)
- **Typical Latency**: 1-3 seconds per reasoning request
- **Fallback**: Rule-based reasoning <50ms if LLM unavailable

### Feedback Processing
- **Batch Size**: Minimum 5 feedback items before index update
- **Update Interval**: 7 days or threshold-triggered
- **Analysis Time**: ~500ms for 50 feedback entries

---

## Configuration & Defaults

| Setting | Default | Purpose |
|---------|---------|---------|
| Embedding Model | sentence-transformers/all-MiniLM-L6-v2 | 384-dim semantic vectors |
| Vector Dimension | 384 | Embedding size for all models |
| Max Chunk Size | 512 characters | Semantic chunking boundary |
| Retrieval Limit | 5-10 documents | Number of results per query |
| LLM Temperature | 0.1 | Low temperature for consistent legal reasoning |
| Min Feedback Threshold | 5 entries | Before automatic index update |
| Update Interval | 7 days | Manual update frequency |
| Semantic Weight | 0.7 | Hybrid search weighting |
| Keyword Weight | 0.3 | Hybrid search weighting |
| Max Concurrent Agents | 10 | Multi-agent coordination limit |
| Session Timeout | 30 minutes | Collaboration session duration |
| Relevance Boost - Supreme Court | 1.5x | Authority-based scoring |
| Relevance Boost - Recent (<1yr) | 1.3x | Recency-based scoring |

---

## Error Handling & Fallbacks

### Vector Database Errors
- **Connection Failures**: Log error, return False, allow graceful degradation
- **Missing Collections**: Auto-create on initialization
- **Insert Failures**: Log and skip with error tracking
- **Search Failures**: Return empty results list, log exception

### LLM Reasoning Errors
- **API Failures**: Fall back to rule-based reasoning (confidence 0.3-0.7)
- **LangChain Unavailable**: Use fallback implementations
- **Parsing Errors**: Return fallback result with simplified reasoning
- **Timeout**: Use cached results or return low-confidence decision

### Document Processing Errors
- **Invalid Files**: Skip with logging, continue batch processing
- **Encoding Errors**: Attempt UTF-8 fallback, then skip
- **Memory Limits**: Process in smaller batches
- **Model Loading**: Log warning, use zero vectors as fallback

### Feedback Loop Errors
- **Index Update Failures**: Log and continue, don't break service
- **Performance Analysis Errors**: Return last known metrics
- **Optimization Errors**: Use conservative recommendations

---

## Test Coverage

The system includes comprehensive tests in `/test_constitutional_retrieval.py`:
- **Vector Database Operations**: CRUD operations for all backends
- **Document Processing**: Chunking, embedding, section extraction
- **Retrieval Functions**: Semantic, hybrid, precedent, and constitutional searches
- **LLM Reasoning**: Structured reasoning, precedent analysis, consistency checks
- **Feedback Mechanisms**: Collection, analysis, and index updates
- **Multi-Agent**: Registration, sessions, permissions
- **Error Handling**: Fallback behavior, graceful degradation

---

## Constitutional Compliance

All code elements enforce constitutional hash validation `cdd01ef066bc6cf2` at import level:
- Hash verified before module execution
- Immutable governance decision tracking
- Cryptographic validation of compliance principles
- Audit trail generation for all constitutional operations

---

## Future Extensibility

The architecture supports:

1. **Additional Vector Databases**: Implement VectorDatabaseManager interface (Pinecone, Weaviate, etc.)
2. **Alternative LLMs**: Replace ChatOpenAI with other LangChain-compatible models
3. **Custom Embedding Models**: Swap SentenceTransformer with specialized domain models
4. **Advanced Reasoning**: Extend LLMReasoner with chain-of-thought, few-shot learning
5. **Distributed Feedback**: Aggregate feedback from multiple systems
6. **Real-time Analytics**: Streaming metrics collection and analysis
7. **Knowledge Graph Integration**: Link related documents and concepts
8. **Explanation Transparency**: Enhanced decision tracing and audit trails

---

## Deployment Considerations

### Docker
```dockerfile
FROM python:3.11-slim
RUN pip install qdrant-client pymilvus langchain langchain-openai sentence-transformers
COPY . /app
WORKDIR /app
EXPOSE 8000
```

### Dependencies Installation
```bash
pip install qdrant-client pymilvus langchain langchain-openai sentence-transformers transformers
```

### Environment Setup
```bash
export OPENAI_API_KEY="your-key"
export QDRANT_URL="http://localhost:6333"  # or Milvus equivalent
```

### Scaling Strategies
- **Horizontal**: Distribute agents across machines, share vector database
- **Vertical**: Increase compute for LLM reasoning and embedding generation
- **Caching**: Redis layer for frequently accessed results
- **Load Balancing**: Distribute retrieval queries across replicated databases

---

## Notes

- All async operations use Python 3.11+ async/await syntax
- Type hints provided throughout for IDE support and validation
- Structured logging with consistent log levels (INFO, WARNING, ERROR)
- ISO 8601 datetime format with UTC timezone throughout
- Graceful degradation when optional dependencies (LangChain, HuggingFace) unavailable
- Support for multiple vector database backends without code duplication
- Extensible feedback mechanism for continuous system improvement
- Multi-agent collaboration foundation for enterprise governance scenarios
