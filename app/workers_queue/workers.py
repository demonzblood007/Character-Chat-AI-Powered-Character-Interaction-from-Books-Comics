"""
comic_rag_worker.py
===================

Worker that:
1. pulls a PDF comic uploaded by the user,
2. extracts and chunks the text,
3. embeds the chunks into Qdrant for retrieval,
4. mines all main characters plus their relationships, powers / abilities and major story arcs with a LangGraph workflow,
5. stores the resulting knowledge graph in Neo4j,
6. exposes a chat entry-point that returns lore-consistent answers while persisting conversation history.
"""

from __future__ import annotations
import asyncio
import json
import os
import uuid
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypedDict, Coroutine

import fitz  # PyMuPDF
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import StateGraph, END, START
from neo4j import GraphDatabase
from pydantic import BaseModel
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from rq import Retry
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue
from app.workers_queue.q import q
from app.utils.qdrant_compat import query_points_compat
from app.utils.qdrant_names import qdrant_collection_name_for_dim, qdrant_collection_name_for_vector
from app.llm import get_llm, get_embeddings
from app.llm.providers.base import BaseLLM, BaseEmbeddings
import httpx

# Load environment variables from .env file
load_dotenv()

# ────────────────────────────────
# Logging Configuration
# ────────────────────────────────
# Ensure logs directory exists
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOGS_DIR, 'worker.log'))
    ]
)

logger = logging.getLogger(__name__)

# ────────────────────────────────
# Configuration
# ────────────────────────────────
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/character_chat")
MONGODB_DB = os.getenv("MONGODB_DB", "character_chat")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", None)
MAX_CONCURRENT_LLM_CALLS = int(os.getenv("MAX_CONCURRENT_LLM_CALLS", 10))

# Embedding Configuration
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", None)

# Vector dimension mapping for different embedding models
EMBEDDING_DIMENSIONS = {
    # OpenAI models
    "text-embedding-3-large": 3072,
    "text-embedding-3-small": 1536,
    "text-embedding-ada-002": 1536,
    # Ollama / local embedding models (common defaults)
    "nomic-embed-text": 768,
    "mxbai-embed-large": 1024,
    # Add other providers as needed
    # "sentence-transformers/all-MiniLM-L6-v2": 384,
    # "BAAI/bge-large-en-v1.5": 1024,
}

def get_vector_size() -> int:
    """Dynamically determine vector size based on embedding model"""
    # Check if dimension is explicitly set in environment
    explicit_size = os.getenv("VECTOR_SIZE")
    if explicit_size:
        return int(explicit_size)
    
    # Otherwise, look up based on model name
    return EMBEDDING_DIMENSIONS.get(EMBEDDING_MODEL, 1536)  # default to 1536

VECTOR_SIZE = get_vector_size()

# Log configuration for debugging
print(f"🔧 Embedding Model: {EMBEDDING_MODEL}")
print(f"📐 Vector Dimension: {VECTOR_SIZE}")

# Processing Configuration
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1400))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))
RAG_RETRIEVAL_K = int(os.getenv("RAG_RETRIEVAL_K", 4))

# ────────────────────────────────
# Abstract LLM Interface
# ────────────────────────────────
class AbstractLLM(ABC):
    @abstractmethod
    def invoke(self, prompt: str) -> str:
        pass
    @abstractmethod
    def get_model_name(self) -> str:
        pass

class AbstractEmbeddings(ABC):
    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        pass
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        pass

class OpenAILLM(AbstractLLM):
    def __init__(self, model: str, temperature: float, api_key: str, base_url: Optional[str] = None):
        self.model = model
        self.temperature = temperature
        self.api_key = api_key
        self.base_url = base_url
        self.client = ChatOpenAI(
            model=model,
            temperature=temperature,
            openai_api_key=api_key,
            openai_api_base=base_url
        )
    def invoke(self, prompt: str) -> str:
        return self.client.invoke(prompt).content
    
    async def ainvoke(self, prompt: str) -> Coroutine[Any, Any, str]:
        """Asynchronous invocation"""
        response = await self.client.ainvoke(prompt)
        return response.content
        
    def get_model_name(self) -> str:
        return self.model

class OllamaLLM(AbstractLLM):
    """
    Minimal Ollama text generation wrapper for the worker.
    Uses /api/generate with stream disabled.
    """
    def __init__(self, model: str, temperature: float, base_url: str):
        self.model = model
        self.temperature = temperature
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")

    def invoke(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        r = httpx.post(url, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        return data.get("response", "") or ""

    async def ainvoke(self, prompt: str) -> Coroutine[Any, Any, str]:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            return data.get("response", "") or ""

    def get_model_name(self) -> str:
        return self.model

class OpenAIEmbeddingsWrapper(AbstractEmbeddings):
    def __init__(self, model: str, api_key: str, base_url: Optional[str] = None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.client = OpenAIEmbeddings(
            model=model,
            openai_api_key=api_key,
            openai_api_base=base_url
        )
    def embed_query(self, text: str) -> List[float]:
        return self.client.embed_query(text)
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.client.embed_documents(texts)

class OllamaEmbeddingsWrapper(AbstractEmbeddings):
    """
    Minimal Ollama embeddings wrapper for the worker.
    Uses /api/embeddings (one prompt at a time).
    """
    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")

    def embed_query(self, text: str) -> List[float]:
        url = f"{self.base_url}/api/embeddings"
        r = httpx.post(url, json={"model": self.model, "prompt": text}, timeout=120)
        r.raise_for_status()
        data = r.json()
        return data.get("embedding", []) or []

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Ollama embeddings endpoint is single-prompt; do a simple loop.
        return [self.embed_query(t) for t in texts]

def create_llm() -> BaseLLM:
    """
    Create an LLM using the shared provider-agnostic factory (env-driven).
    Supports: OpenAI, vLLM, Ollama.
    """
    return get_llm()

def create_embeddings() -> BaseEmbeddings:
    """
    Create embeddings using the shared provider-agnostic factory (env-driven).
    Supports: OpenAI, vLLM, Ollama/local.
    """
    return get_embeddings()

# ────────────────────────────────
# State Management
# ────────────────────────────────
class ComicState(TypedDict, total=False):
    file_id: str
    user_id: str
    text: str
    chunks: List[str]
    all_character_mentions: List[str]  # All names mentioned (before deduplication)
    characters: List[Dict[str, Any]]   # Deduplicated characters with aliases
    current_character: Optional[str]
    character_detail: Optional[Dict[str, Any]]
    graph_job_done: bool
    relationships: List[Dict[str, Any]]
    relationship_extraction_done: bool
    messages: List[Dict[str, str]]
    # Non-serializable context objects
    semaphore: asyncio.Semaphore

# ────────────────────────────────
# Validation & Health Checks
# ────────────────────────────────
def validate_pdf_file(path: str) -> tuple[bool, Optional[str]]:
    """
    Validate PDF file before processing
    Returns: (is_valid, error_message)
    """
    try:
        # Check file exists
        if not os.path.exists(path):
            return False, f"File not found: {path}"
        
        # Check file size
        file_size_mb = os.path.getsize(path) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            return False, f"File too large: {file_size_mb:.1f}MB (max: {MAX_FILE_SIZE_MB}MB)"
        
        if file_size_mb == 0:
            return False, "File is empty"
        
        # Try to open PDF (checks if corrupted)
        doc = fitz.open(path)
        page_count = doc.page_count
        doc.close()
        
        if page_count == 0:
            return False, "PDF has no pages"
        
        logger.info(f"PDF validation passed: {page_count} pages, {file_size_mb:.1f}MB")
        return True, None
        
    except Exception as e:
        error_msg = f"PDF validation failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def verify_database_connections() -> tuple[bool, Optional[str]]:
    """
    Verify all database connections before processing
    Returns: (all_healthy, error_message)
    """
    errors = []
    
    # Check Neo4j
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        logger.info("Neo4j connection verified")
    except Exception as e:
        errors.append(f"Neo4j connection failed: {e}")
        logger.error(errors[-1])
    
    # Check Qdrant
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        client.get_collections()
        logger.info("Qdrant connection verified")
    except Exception as e:
        errors.append(f"Qdrant connection failed: {e}")
        logger.error(errors[-1])
    
    # Check MongoDB
    try:
        from pymongo import MongoClient
        mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        mongo_client.server_info()
        mongo_client.close()
        logger.info("MongoDB connection verified")
    except Exception as e:
        errors.append(f"MongoDB connection failed: {e}")
        logger.error(errors[-1])
    
    if errors:
        return False, "; ".join(errors)
    return True, None


# ────────────────────────────────
# PDF Processing
# ────────────────────────────────
def load_pdf_text(path: str) -> str:
    """Load text from PDF with error handling"""
    try:
        logger.info(f"Loading PDF: {path}")
        doc = fitz.open(path)
        text = ""
        page_count = doc.page_count
        
        for i, page in enumerate(doc):
            page_text = page.get_text()
            text += page_text
            if (i + 1) % 50 == 0:  # Log progress every 50 pages
                logger.info(f"Processed {i + 1}/{page_count} pages")
        
        doc.close()
        logger.info(f"Successfully loaded {page_count} pages, {len(text)} characters")
        return text
        
    except Exception as e:
        logger.error(f"Failed to load PDF: {e}", exc_info=True)
        raise


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """Chunk text with configurable parameters"""
    chunk_size = chunk_size or CHUNK_SIZE
    overlap = overlap or CHUNK_OVERLAP
    
    logger.info(f"Chunking text: {len(text)} chars with size={chunk_size}, overlap={overlap}")
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
    )
    chunks = splitter.split_text(text)
    logger.info(f"Created {len(chunks)} chunks")
    return chunks

# ────────────────────────────────
# Qdrant Integration
# ────────────────────────────────
def ensure_qdrant_collection(client: QdrantClient, name: str, size: int) -> None:
    """
    Ensure Qdrant collection exists with the given vector size.

    Important: do NOT rely on VECTOR_SIZE env var here; use the actual embedding
    vector length (size) to avoid dimension mismatch errors.
    """
    if name not in [c.name for c in client.get_collections().collections]:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=int(size), distance=Distance.COSINE
            ),
        )

def store_chunks_in_qdrant(chunks: List[str], file_id: str, embeddings: AbstractEmbeddings, user_id: str):
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    base = os.getenv("QDRANT_CHUNKS_COLLECTION", "comic_chunks")
    # Use the actual embedding vector dimension to pick the right collection.
    vectors = embeddings.embed_documents(chunks)
    dim = len(vectors[0]) if vectors else VECTOR_SIZE
    collection = qdrant_collection_name_for_dim(base, dim)
    ensure_qdrant_collection(client, collection, dim)
    client.upload_collection(
        collection_name=collection,
        vectors=vectors,
        payload=[{"type": "chunk", "file_id": file_id, "text": chunk, "user_id": user_id} for chunk in chunks],
        ids=[str(uuid.uuid4()) for _ in vectors],
    )

def retrieve_context_from_qdrant(query: str, k: int = 4, file_id: Optional[str] = None, character_name: Optional[str] = None, user_id: Optional[str] = None) -> str:
    """
    Enhanced RAG retrieval with filtering by file_id and character name
    
    Args:
        query: Search query
        k: Number of results to return
        file_id: Optional file_id to filter results
        character_name: Optional character name to include in query for better context
    """
    embeddings = create_embeddings()
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    # Enhance query with character name for better semantic matching
    enhanced_query = query
    if character_name:
        enhanced_query = f"{character_name} {query}"
    
    v = embeddings.embed_query(enhanced_query)
    
    # Build filter conditions
    filter_conditions = [FieldCondition(key="type", match=MatchValue(value="chunk"))]
    if file_id:
        filter_conditions.append(FieldCondition(key="file_id", match=MatchValue(value=file_id)))
    if user_id:
        filter_conditions.append(FieldCondition(key="user_id", match=MatchValue(value=user_id)))
    
    q_filter = Filter(must=filter_conditions) if filter_conditions else None

    collection = qdrant_collection_name_for_vector(os.getenv("QDRANT_CHUNKS_COLLECTION", "comic_chunks"), v)
    points = query_points_compat(
        client,
        collection_name=collection,
        query_vector=v,
        limit=k,
        query_filter=q_filter,
        with_payload=True,
    )

    texts: List[str] = []
    for hit in points:
        payload = getattr(hit, "payload", None) or {}
        text = payload.get("text", "")
        if text:
            texts.append(text)
    return "\n".join(texts)

# ────────────────────────────────
# Neo4j Integration
# ────────────────────────────────
class Neo4jCharacterStore:
    def __init__(self, driver):
        self.driver = driver
    
    def upsert_character(self, char: Dict[str, Any]) -> None:
        """Create or update a character node with aliases support"""
        with self.driver.session() as session:
            session.run(
                """
                MERGE (c:Character {name: $name})
                SET c.description = $description,
                    c.powers = $powers,
                    c.story_arcs = $story_arcs,
                    c.file_id = $file_id,
                    c.aliases = $aliases,
                    c.user_id = $user_id
                """,
                name=char["name"],
                description=char.get("description", ""),
                powers=char.get("powers", []),
                story_arcs=char.get("story_arcs", []),
                file_id=char.get("file_id"),
                aliases=char.get("aliases", []),
                user_id=char.get("user_id")
            )
    
    def batch_upsert_characters(self, characters: List[Dict[str, Any]]) -> None:
        """Batch create or update character nodes."""
        if not characters:
            return
        
        query = """
        UNWIND $characters as char
        MERGE (c:Character {name: char.name})
        SET c.description = char.description,
            c.powers = char.powers,
            c.story_arcs = char.story_arcs,
            c.file_id = char.file_id,
            c.aliases = char.aliases,
            c.user_id = char.user_id
        """
        
        with self.driver.session() as session:
            session.run(query, characters=characters)

    def get_all_characters(self, file_id: str, user_id: str) -> List[str]:
        """Get all character names from database for a specific file and user"""
        with self.driver.session() as session:
            result = session.run(
                "MATCH (c:Character {file_id: $file_id, user_id: $user_id}) RETURN c.name as name",
                file_id=file_id,
                user_id=user_id
            )
            return [record["name"] for record in result]
    
    def upsert_relationship(self, rel: Dict[str, Any]) -> None:
        """Create or update a BIDIRECTIONAL relationship with evidence"""
        with self.driver.session() as session:
            # Create both directions for symmetric relationships
            session.run(
                """
                MATCH (a:Character {name: $source})
                MATCH (b:Character {name: $target})
                MERGE (a)-[r:RELATION {type: $type}]->(b)
                SET r.description = $description,
                    r.strength = $strength,
                    r.evidence = $evidence
                """,
                source=rel.get("source", ""),
                target=rel.get("target", ""),
                type=rel.get("type", "unknown"),
                description=rel.get("description", ""),
                strength=rel.get("strength", 1.0),
                evidence=rel.get("evidence", []),
                user_id=rel.get("user_id")
            )
            
            # Create reverse relationship for bidirectional types
            bidirectional_types = ["friend", "ally", "enemy", "rival", "family", "colleague"]
            if rel.get("type") in bidirectional_types:
                session.run(
                    """
                    MATCH (a:Character {name: $target})
                    MATCH (b:Character {name: $source})
                    MERGE (a)-[r:RELATION {type: $type}]->(b)
                    SET r.description = $description,
                        r.strength = $strength,
                        r.evidence = $evidence
                    """,
                    source=rel.get("source", ""),
                    target=rel.get("target", ""),
                    type=rel.get("type", "unknown"),
                    description=rel.get("description", ""),
                    strength=rel.get("strength", 1.0),
                    evidence=rel.get("evidence", []),
                    user_id=rel.get("user_id")
                )

    def batch_upsert_relationships(self, relationships: List[Dict[str, Any]]) -> None:
        """Batch create or update bidirectional relationships."""
        if not relationships:
            return

        # Separate relationships into forward and reverse for bidirectional types
        forward_rels = []
        reverse_rels = []
        bidirectional_types = ["friend", "ally", "enemy", "rival", "family", "colleague"]

        for rel in relationships:
            forward_rels.append(rel)
            if rel.get("type") in bidirectional_types:
                # Create a reverse relationship
                reverse_rel = rel.copy()
                reverse_rel["source"] = rel["target"]
                reverse_rel["target"] = rel["source"]
                reverse_rels.append(reverse_rel)

        query = """
        UNWIND $rels as r
        MATCH (a:Character {name: r.source})
        MATCH (b:Character {name: r.target})
        // Ensure both characters belong to the same user as a safeguard
        WHERE a.user_id = r.user_id AND b.user_id = r.user_id
        MERGE (a)-[rel:RELATION {type: r.type}]->(b)
        SET rel.description = r.description,
            rel.strength = r.strength,
            rel.evidence = r.evidence
        """
        
        with self.driver.session() as session:
            if forward_rels:
                session.run(query, rels=forward_rels)
            if reverse_rels:
                session.run(query, rels=reverse_rels)

# ────────────────────────────────
# LangGraph Workflow
# ────────────────────────────────
async def node_extract_characters(state: ComicState) -> ComicState:
    """Extract characters from ALL chunks in parallel, then deduplicate and resolve aliases"""
    llm = create_llm()
    semaphore = state["semaphore"]
    error_count = 0
    
    # Phase 1: Parallel extraction from all chunks
    async def extract_from_chunk(chunk: str) -> List[str]:
        nonlocal error_count
        prompt = f"""
        Extract all character names (people) from this text section. 
        Return only a JSON array of names, nothing else.
        Text: {chunk}
        Format: ["Name1", "Name2", ...]
        """
        try:
            async with semaphore:
                response = await llm.ainvoke(prompt)
            # Clean response and parse JSON
            response = response.strip().strip("```json").strip("```").strip()
            return json.loads(response)
        except (json.JSONDecodeError, TypeError):
            # Model responded but not valid JSON; treat as a soft failure for this chunk.
            error_count += 1
            return []
        except Exception as e:
            # Hard failure (network/model missing/etc). Count it so we can fail the job
            # instead of silently "succeeding" with 0 characters.
            error_count += 1
            try:
                logger.warning(f"Character extraction failed for a chunk: {type(e).__name__}: {e}")
            except Exception:
                pass
            return []

    chunks = state.get("chunks", [])
    tasks = [extract_from_chunk(chunk) for chunk in chunks]
    results = await asyncio.gather(*tasks)
    
    all_mentions = [name for sublist in results for name in sublist]
    
    # Store all mentions
    state["all_character_mentions"] = all_mentions
    print(f"Total character mentions across all chunks: {len(all_mentions)}")

    # If we got zero mentions but had failures, treat it as a pipeline failure (not a valid "0 characters" result).
    # This prevents marking the file as 'done' when the model is missing or the backend is unreachable.
    if len(all_mentions) == 0 and error_count > 0:
        provider = os.getenv("LLM_PROVIDER", "openai")
        base_url = os.getenv("LLM_BASE_URL", "")
        model = os.getenv("LLM_MODEL", "")
        raise RuntimeError(
            f"LLM character extraction failed for {error_count}/{len(chunks)} chunks. "
            f"provider={provider} model={model} base_url={base_url}. "
            "Fix by setting env vars correctly and ensuring the model is available (e.g., `ollama pull <model>` or vLLM is running)."
        )
    
    # Phase 2: Deduplicate and resolve aliases (single LLM call)
    if all_mentions:
        unique_characters = await deduplicate_characters(all_mentions, llm, semaphore)
        # Add file_id to each character
        file_id = state["file_id"]
        user_id = state["user_id"]
        for char in unique_characters:
            char["file_id"] = file_id
            char["user_id"] = user_id
        state["characters"] = unique_characters
        print(f"After deduplication: {len(unique_characters)} unique characters")
    else:
        state["characters"] = []
    
    return state


async def deduplicate_characters(all_mentions: List[str], llm: AbstractLLM, semaphore: asyncio.Semaphore) -> List[Dict[str, Any]]:
    """Use LLM to identify duplicate characters and aliases"""
    if not all_mentions:
        return []
    
    # Get unique mentions and limit if necessary
    unique_mentions = list(set(all_mentions))
    if len(unique_mentions) > 50:
        from collections import Counter
        counter = Counter(all_mentions)
        unique_mentions = [name for name, count in counter.most_common(50)]
    
    prompt = f"""
    Given this list of character names, identify which ones refer to the same person.
    Names: {json.dumps(unique_mentions)}
    
    Group aliases together and choose one primary name for each character.
    Return JSON format:
    [
        {{"name": "Primary Name", "aliases": ["Alias1", "Alias2"]}},
        {{"name": "Another Character", "aliases": []}}
    ]
    
    Return ONLY the JSON array, no other text.
    """
    
    try:
        async with semaphore:
            response = await llm.ainvoke(prompt)
        response = response.strip().strip("```json").strip("```").strip()
        deduplicated = json.loads(response)
        if isinstance(deduplicated, list):
            return deduplicated
    except Exception as e:
        print(f"Deduplication failed: {e}, using all unique mentions")
    
    # Fallback
    return [{"name": name, "aliases": []} for name in unique_mentions]


async def node_extract_all_character_details(state: ComicState) -> ComicState:
    """Extract details for all characters in parallel using RAG"""
    characters_to_process = state.get("characters", [])
    if not characters_to_process:
        return state

    llm = create_llm()
    file_id = state["file_id"]
    user_id = state["user_id"]
    semaphore = state["semaphore"]
    
    # Create a task for each character
    tasks = [
        extract_single_character_detail(char["name"], char.get("aliases", []), file_id, llm, semaphore, user_id)
        for char in characters_to_process
    ]
    
    character_details = await asyncio.gather(*tasks)
    
    # Filter out any failed extractions (None) and update state
    state["characters"] = [detail for detail in character_details if detail]
    
    return state


async def extract_single_character_detail(
    character_name: str, aliases: List[str], file_id: str, llm: AbstractLLM, semaphore: asyncio.Semaphore, user_id: str
) -> Optional[Dict[str, Any]]:
    """Extracts details for a single character."""
    try:
        # RAG retrieval
        relevant_text = retrieve_context_from_qdrant(
            query=f"{character_name} character description powers abilities",
            k=5,
            file_id=file_id,
            user_id=user_id
        )
        if not relevant_text:
            return None # Skip if no context found

        prompt = f"""
        Extract detailed information about the character "{character_name}" from this text.
        {"Also known as: " + ", ".join(aliases) if aliases else ""}
        
        Return a JSON object with: description, powers (array), story_arcs (array).
        
        Text: {relevant_text}
        
        Format: {{"description": "...", "powers": [...], "story_arcs": [...]}}
        Return ONLY valid JSON.
        """
        
        async with semaphore:
            response = await llm.ainvoke(prompt)
        response = response.strip().strip("```json").strip("```").strip()
        detail = json.loads(response)
        
        # Combine with existing data
        detail["name"] = character_name
        detail["aliases"] = aliases
        detail["file_id"] = file_id
        detail["user_id"] = user_id
        return detail

    except Exception as e:
        print(f"Failed to extract detail for {character_name}: {e}")
        return None


def node_write_characters(state: ComicState, store: Neo4jCharacterStore) -> ComicState:
    """Batch write all character details to Neo4j"""
    characters_with_details = state.get("characters", [])
    
    if characters_with_details:
        # Ensure all required fields are present with defaults
        for char in characters_with_details:
            char.setdefault("description", "")
            char.setdefault("powers", [])
            char.setdefault("story_arcs", [])
            char.setdefault("user_id", state["user_id"]) # Ensure user_id is present
        
        store.batch_upsert_characters(characters_with_details)
        print(f"Batch wrote {len(characters_with_details)} characters to Neo4j")
        
    return state


async def node_extract_relationships(state: ComicState) -> ComicState:
    """Extract relationships in parallel after pre-calculating co-occurrence."""
    from itertools import combinations
    from pymongo import MongoClient
    from bson import ObjectId
    from datetime import datetime

    # Update status
    await update_file_status_async(state["file_id"], "extracting_relationships")
    
    llm = create_llm()
    file_id = state["file_id"]
    user_id = state["user_id"]
    
    # Get characters from the state (they were just processed)
    character_names = [char["name"] for char in state.get("characters", [])]
    if len(character_names) < 2:
        state["relationships"] = []
        return state

    print(f"Optimizing relationship extraction for {len(character_names)} characters...")

    # 1. Build co-occurrence map
    co_occurrence = {name: set() for name in character_names}
    for chunk in state.get("chunks", []):
        present_chars = [name for name in character_names if name.lower() in chunk.lower()]
        for char1, char2 in combinations(present_chars, 2):
            co_occurrence[char1].add(char2)
            co_occurrence[char2].add(char1)
            
    # 2. Create candidate pairs
    candidate_pairs = set()
    for char1, others in co_occurrence.items():
        for char2 in others:
            # Sort to avoid duplicates like (A,B) and (B,A)
            candidate_pairs.add(tuple(sorted((char1, char2))))

    print(f"Reduced from {len(list(combinations(character_names, 2)))} total pairs to {len(candidate_pairs)} candidate pairs.")

    # 3. Extract relationships in parallel
    semaphore = state["semaphore"]
    tasks = [
        extract_relationship_for_pair(char_a, char_b, file_id, llm, semaphore, user_id)
        for char_a, char_b in candidate_pairs
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Filter out null results (no relationship found)
    relationships = [rel for rel in results if rel]
    
    state["relationships"] = relationships
    print(f"Total relationships extracted: {len(relationships)}")
    return state


async def extract_relationship_for_pair(
    char_a: str, char_b: str, file_id: str, llm: AbstractLLM, semaphore: asyncio.Semaphore, user_id: str
) -> Optional[Dict[str, Any]]:
    """Analyzes a single character pair for a relationship."""
    try:
        # RAG retrieval for the pair
        context = retrieve_context_from_qdrant(
            query=f'interaction between "{char_a}" and "{char_b}"',
            k=3,
            file_id=file_id,
            user_id=user_id
        )
        
        # Anti-hallucination check: ensure both characters are mentioned
        if not (char_a.lower() in context.lower() and char_b.lower() in context.lower()):
            return None

        prompt = f"""
        Analyze the relationship between "{char_a}" and "{char_b}" based on this text.
        
        Text: {context}
        
        Return a JSON object with "type" (e.g., friend, enemy, ally) and "description".
        If no clear relationship, return {{"type": "unknown"}}.
        
        Format: {{"type": "...", "description": "..."}}
        Return ONLY valid JSON.
        """
        
        async with semaphore:
            response = await llm.ainvoke(prompt)
        response = response.strip().strip("```json").strip("```").strip()
        rel_data = json.loads(response)

        if rel_data.get("type") != "unknown":
            return {
                "source": char_a,
                "target": char_b,
                "type": rel_data.get("type", "unknown"),
                "description": rel_data.get("description", ""),
                "strength": 0.5, # Default strength
                "evidence": [context[:200] + "..."], # Simple evidence
                "user_id": user_id # Tag relationship with user_id
            }
        return None
    except Exception:
        return None


def node_write_relationships(state: ComicState, store: Neo4jCharacterStore) -> ComicState:
    """Batch write all relationships to Neo4j"""
    relationships = state.get("relationships", [])
    if relationships:
        store.batch_upsert_relationships(relationships)
        print(f"Batch wrote {len(relationships)} relationships to Neo4j.")
    
    state["relationship_extraction_done"] = True
    return state


async def update_file_status_async(file_id: str, status: str, **kwargs):
    """Asynchronous helper to update file status in MongoDB."""
    from bson import ObjectId
    from datetime import datetime
    import motor.motor_asyncio
    
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DB]
    
    update_data = {"status": status, "updatedAt": datetime.utcnow()}
    update_data.update(kwargs)
    
    await db["files"].update_one(
        {"_id": ObjectId(file_id)},
        {"$set": update_data}
    )
    print(f"Status updated asynchronously: {status}")
    client.close()


def build_comic_graph(neo4j_driver) -> StateGraph:
    """
    Builds the optimized, asynchronous LangGraph workflow.
    """
    store = Neo4jCharacterStore(neo4j_driver)
    workflow = StateGraph(ComicState)

    # Phase 1: Character Extraction (fully parallel)
    workflow.add_node("extract_characters", node_extract_characters)
    workflow.add_node("extract_all_character_details", node_extract_all_character_details)
    workflow.add_node("write_characters", lambda state: node_write_characters(state, store))

    # Phase 2: Relationship Extraction (fully parallel)
    workflow.add_node("extract_relationships", node_extract_relationships)
    workflow.add_node("write_relationships", lambda state: node_write_relationships(state, store))
    
    # Workflow Edges
    workflow.set_entry_point("extract_characters")
    workflow.add_edge("extract_characters", "extract_all_character_details")
    workflow.add_edge("extract_all_character_details", "write_characters")
    workflow.add_edge("write_characters", "extract_relationships")
    workflow.add_edge("extract_relationships", "write_relationships")
    workflow.add_edge("write_relationships", END)
    
    return workflow.compile()


async def process_pdf_file_async(file_record: Dict[str, Any]) -> None:
    """
    Asynchronous version of the main processing function.
    """
    from pymongo import MongoClient
    from datetime import datetime
    from bson import ObjectId

    file_id = str(file_record["_id"])
    user_id = file_record["user_id"] # <-- Extract user_id here
    file_name = file_record.get('name', 'unknown')
    file_path = file_record.get("path")

    # Helper for status updates
    async def update_status(status: str, **kwargs):
        await update_file_status_async(file_id, status, **kwargs)

    try:
        # --- Validation (can remain synchronous) ---
        db_healthy, db_error = verify_database_connections()
        if not db_healthy:
            await update_status("failed", error=f"DB health check failed: {db_error}")
            return

        # --- LLM/Embeddings Preflight (fail fast, avoid '0 characters' from misconfig) ---
        try:
            llm = create_llm()
            ok = await llm.health_check()
            if not ok:
                await update_status(
                    "failed",
                    error=(
                        "LLM health check failed. Check LLM_PROVIDER/LLM_MODEL/LLM_BASE_URL "
                        "(inside Docker, localhost will not reach host services)."
                    ),
                )
                return
        except Exception as e:
            await update_status("failed", error=f"LLM initialization/health check failed: {type(e).__name__}: {e}")
            return

        is_valid, validation_error = validate_pdf_file(file_path)
        if not is_valid:
            await update_status("failed", error=validation_error)
            return

        await update_status("processing")
        
        # --- PDF Processing and Embedding (remains synchronous) ---
        text = load_pdf_text(file_path)
        chunks = chunk_text(text)
        await update_status("processing", chunk_count=len(chunks))
        
        embeddings = create_embeddings()
        store_chunks_in_qdrant(chunks, file_id, embeddings, user_id)
        print(f"Stored {len(chunks)} chunks in Qdrant for file {file_id}")
        
        # --- LangGraph Workflow (now asynchronous) ---
        state = ComicState(
            file_id=file_id,
            user_id=user_id, # <-- Add user_id to the initial state
            text=text, chunks=chunks,
            characters=[], relationships=[],
            semaphore=asyncio.Semaphore(MAX_CONCURRENT_LLM_CALLS)
        )
        
        await update_status("extracting_characters")
        
        neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        graph = build_comic_graph(neo4j_driver)
        
        try:
            # Invoke the async graph
            final_state = await graph.ainvoke(state, config={"recursion_limit": 50})
            
            # --- Final Status Update ---
            character_count = len(final_state.get("characters", []))
            relationship_count = len(final_state.get("relationships", []))
            mention_count = len(final_state.get("all_character_mentions", []) or [])

            # If we extracted candidate mentions but ended up saving 0 character profiles,
            # this is almost always a downstream failure (e.g., retrieval/LLM step) and should not be marked "done".
            if character_count == 0 and mention_count > 0:
                await update_status(
                    "failed",
                    character_count=0,
                    relationship_count=0,
                    processed_at=datetime.utcnow(),
                    error=(
                        "Character extraction produced candidate mentions but no character profiles were saved. "
                        "This indicates a downstream failure during character detail extraction. Please retry or delete this upload."
                    ),
                )
                return

            await update_status(
                "done",
                character_count=character_count,
                relationship_count=relationship_count,
                processed_at=datetime.utcnow()
            )
            print(f"Successfully processed file: {file_name}")

        finally:
            neo4j_driver.close()

    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = f"Error processing file: {str(e)}"
        await update_status("failed", error=error_msg)


def process_pdf_file_sync_wrapper(file_record: Dict[str, Any]) -> None:
    """Synchronous wrapper to run the async processing function."""
    asyncio.run(process_pdf_file_async(file_record))


# ────────────────────────────────
# Personality System
# ────────────────────────────────
def get_character_personality_note(character_name: str) -> str:
    """
    Get personality and speaking style notes for common characters
    Enhances LLM responses with character-specific voice
    """
    
    # Personality database (can be expanded or moved to DB)
    personalities = {
        "Batman": """
        SPEAKING STYLE:
        - Terse, brooding, intense
        - Uses short, punchy sentences
        - Rarely jokes or shows warmth
        - Mentions darkness, shadows, night, fear
        - Speaks in first person ("I will...", "I've seen...")
        - Shows controlled emotion - anger, determination
        - Example: "Crime doesn't sleep. Neither do I."
        """,
        
        "Joker": """
        SPEAKING STYLE:
        - Chaotic, rambling, theatrical
        - Laughs mid-sentence (heh, haha, HAHAHA)
        - Makes dark jokes, puns, wordplay
        - Unpredictable topic changes
        - Questions everything, especially norms
        - Example: "Why so serious? Life's just one big joke, and the punchline? *laughs* You!"
        """,
        
        "Superman": """
        SPEAKING STYLE:
        - Optimistic, earnest, inspirational
        - Clear, articulate, heroic tone
        - References hope, justice, doing the right thing
        - Encouraging and supportive
        - Humble despite powers
        - Example: "There's always hope. As long as people believe in doing good, we can overcome anything."
        """,
        
        "Spider-Man": """
        SPEAKING STYLE:
        - Quippy, sarcastic, jokes under pressure
        - Makes pop culture references
        - Self-deprecating humor
        - Youthful, energetic tone
        - Balances humor with responsibility
        - Example: "With great power comes great... need for better one-liners. Working on it!"
        """,
        
        "Hermione Granger": """
        SPEAKING STYLE:
        - Intelligent, bookish, precise
        - Often explains things thoroughly
        - References books, rules, facts
        - Can be bossy but caring
        - Shows passion when discussing knowledge
        - Example: "According to Hogwarts: A History, which you'd know if you'd actually read it..."
        """,
        
        "Sherlock Holmes": """
        SPEAKING STYLE:
        - Analytical, deductive, matter-of-fact
        - Points out details others miss
        - Can be condescending (unintentionally)
        - Precise vocabulary, British formal
        - Explains his reasoning process
        - Example: "Elementary. The mud on your shoes indicates you walked through Regent's Park this morning..."
        """,
    }
    
    # Check if we have personality data for this character
    if character_name in personalities:
        return personalities[character_name]
    
    # Check for partial matches (e.g., "Peter Parker" contains "Spider")
    for known_char, personality in personalities.items():
        if known_char.lower() in character_name.lower() or character_name.lower() in known_char.lower():
            return personality
    
    # Default personality note for unknown characters
    return """
    SPEAKING STYLE:
    - Stay true to this character's established personality
    - Use their typical vocabulary and speech patterns
    - Match their emotional range and tone
    - Be consistent with how they've spoken before
    """

# ────────────────────────────────
# Chat Interface
# ────────────────────────────────
class ChatRequest(BaseModel):
    user_id: str
    character_name: str
    message: str

def chat_with_character(req: ChatRequest) -> Dict[str, str]:
    """
    Chat with a character with conversation history persistence and enhanced RAG
    
    Features:
    - Retrieves conversation history from MongoDB
    - Uses history for context-aware responses
    - Enhanced RAG with character-specific filtering
    - Saves messages to MongoDB for future reference
    """
    from pymongo import MongoClient
    from datetime import datetime
    
    llm = create_llm()
    neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    mongo_client = MongoClient(MONGODB_URI)
    
    try:
        # 1. Get character information from Neo4j
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (c:Character {name: $name, user_id: $user_id})
                RETURN c.description as description, 
                       c.powers as powers, 
                       c.story_arcs as story_arcs,
                       c.file_id as file_id
            """, name=req.character_name, user_id=req.user_id)
            record = result.single()
            
            if not record:
                return {"response": f"Character '{req.character_name}' not found."}
            
            character_context = f"""
            Character: {req.character_name}
            Description: {record['description'] or 'No description available'}
            Powers: {', '.join(record['powers'] or [])}
            Story Arcs: {', '.join(record['story_arcs'] or [])}
            """
            file_id = record.get('file_id')
        
        # 2. Retrieve conversation history from MongoDB
        db = mongo_client[MONGODB_DB]
        chat_sessions = db["chat_sessions"]
        
        session_doc = chat_sessions.find_one({
            "user_id": req.user_id,
            "character": req.character_name
        })
        
        # Get last 10 messages for context (conversation memory)
        conversation_history = []
        if session_doc and "messages" in session_doc:
            conversation_history = session_doc["messages"][-10:]  # Last 10 messages
        
        # Format conversation history for prompt
        history_text = ""
        if conversation_history:
            history_text = "\n\nConversation History:\n"
            for msg in conversation_history:
                role = "User" if msg["role"] == "user" else req.character_name
                history_text += f"{role}: {msg['content']}\n"
        
        # 3. Enhanced RAG: Retrieve relevant context with character filtering
        rag_context = retrieve_context_from_qdrant(
            query=req.message,
            k=5,
            file_id=file_id,
            character_name=req.character_name,
            user_id=req.user_id
        )
        
        # 4. Get personality traits for better voice
        personality_note = get_character_personality_note(req.character_name)
        
        # 5. Build comprehensive prompt with all context
        prompt = f"""
        You are {req.character_name}. Respond to the user's message in character, 
        maintaining consistency with your personality and previous conversation.
        
        {personality_note}
        
        Character Information:
        {character_context}
        
        Relevant Story Context:
        {rag_context}
        {history_text}
        
        Current User Message: {req.message}
        
        Respond as {req.character_name} (stay in character, be natural and engaging):
        """
        
        # 6. Generate response
        response_text = llm.invoke(prompt)
        
        # 7. Save conversation to MongoDB
        timestamp = datetime.utcnow()
        
        # Create message objects
        user_message = {
            "role": "user",
            "content": req.message,
            "timestamp": timestamp
        }
        
        assistant_message = {
            "role": "assistant",
            "content": response_text,
            "timestamp": timestamp
        }
        
        # Update or create chat session
        chat_sessions.update_one(
            {
                "user_id": req.user_id,
                "character": req.character_name
            },
            {
                "$push": {
                    "messages": {
                        "$each": [user_message, assistant_message]
                    }
                },
                "$set": {
                    "last_message_at": timestamp,
                    "updated_at": timestamp
                },
                "$setOnInsert": {
                    "created_at": timestamp
                }
            },
            upsert=True  # Create if doesn't exist
        )
        
        print(f"Chat message saved for user {req.user_id} with {req.character_name}")
        
        return {
            "response": response_text,
            "character": req.character_name,
            "timestamp": timestamp.isoformat()
        }
        
    except Exception as e:
        print(f"Error in chat_with_character: {e}")
        import traceback
        traceback.print_exc()
        return {
            "response": f"I apologize, but I'm having trouble responding right now. Please try again.",
            "error": str(e)
        }
    finally:
        neo4j_driver.close()
        mongo_client.close()


async def chat_with_character_streaming(req: ChatRequest):
    """
    Streaming version of chat_with_character - yields response chunks in real-time
    
    Yields:
        {"type": "status", "message": "Retrieving character info..."}
        {"type": "chunk", "content": "I am "}
        {"type": "chunk", "content": "Batman. "}
        {"type": "done", "character": "Batman", "timestamp": "..."}
    """
    import asyncio
    from typing import AsyncGenerator
    from pymongo import MongoClient
    from datetime import datetime
    
    try:
        # Status update: Starting
        yield {"type": "status", "message": "Connecting to databases..."}
        
        llm = create_llm()
        neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        mongo_client = MongoClient(MONGODB_URI)
        
        # 1. Get character information
        yield {"type": "status", "message": "Retrieving character profile..."}
        
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (c:Character {name: $name, user_id: $user_id})
                RETURN c.description as description, 
                       c.powers as powers, 
                       c.story_arcs as story_arcs,
                       c.file_id as file_id
            """, name=req.character_name, user_id=req.user_id)
            record = result.single()
            
            if not record:
                yield {"type": "error", "message": f"Character '{req.character_name}' not found."}
                return
            
            character_context = f"""
            Character: {req.character_name}
            Description: {record['description'] or 'No description available'}
            Powers: {', '.join(record['powers'] or [])}
            Story Arcs: {', '.join(record['story_arcs'] or [])}
            """
            file_id = record.get('file_id')
        
        # 2. Retrieve conversation history
        yield {"type": "status", "message": "Loading conversation history..."}
        
        db = mongo_client[MONGODB_DB]
        chat_sessions = db["chat_sessions"]
        
        session_doc = chat_sessions.find_one({
            "user_id": req.user_id,
            "character": req.character_name
        })
        
        conversation_history = []
        if session_doc and "messages" in session_doc:
            conversation_history = session_doc["messages"][-10:]
        
        history_text = ""
        if conversation_history:
            history_text = "\n\nConversation History:\n"
            for msg in conversation_history:
                role = "User" if msg["role"] == "user" else req.character_name
                history_text += f"{role}: {msg['content']}\n"
        
        # 3. Enhanced RAG retrieval
        yield {"type": "status", "message": "Searching story context..."}
        
        rag_context = retrieve_context_from_qdrant(
            query=req.message,
            k=5,
            file_id=file_id,
            character_name=req.character_name,
            user_id=req.user_id
        )
        
        # 4. Get personality traits for better voice
        yield {"type": "status", "message": f"Channeling {req.character_name}..."}
        personality_note = get_character_personality_note(req.character_name)
        
        # 5. Build comprehensive prompt
        prompt = f"""
        You are {req.character_name}. Respond to the user's message in character, 
        maintaining consistency with your personality and previous conversation.
        
        {personality_note}
        
        Character Information:
        {character_context}
        
        Relevant Story Context:
        {rag_context}
        {history_text}
        
        Current User Message: {req.message}
        
        Respond as {req.character_name} (stay in character, be natural and engaging):
        """
        
        # 6. Stream response from LLM
        yield {"type": "start", "character": req.character_name}
        
        full_response = ""
        
        # Generate response (simulate streaming for non-streaming LLMs)
        response_text = llm.invoke(prompt)
        full_response = response_text
        
        # Simulate word-by-word streaming for better UX
        words = response_text.split()
        for i, word in enumerate(words):
            content = word + (" " if i < len(words) - 1 else "")
            yield {"type": "chunk", "content": content}
            await asyncio.sleep(0.03)  # 30ms delay between words
        
        # 7. Save conversation
        timestamp = datetime.utcnow()
        
        user_message = {
            "role": "user",
            "content": req.message,
            "timestamp": timestamp
        }
        
        assistant_message = {
            "role": "assistant",
            "content": full_response,
            "timestamp": timestamp
        }
        
        chat_sessions.update_one(
            {
                "user_id": req.user_id,
                "character": req.character_name
            },
            {
                "$push": {
                    "messages": {
                        "$each": [user_message, assistant_message]
                    }
                },
                "$set": {
                    "last_message_at": timestamp,
                    "updated_at": timestamp
                },
                "$setOnInsert": {
                    "created_at": timestamp
                }
            },
            upsert=True
        )
        
        # Final status
        yield {
            "type": "done", 
            "character": req.character_name,
            "timestamp": timestamp.isoformat(),
            "full_text": full_response
        }
        
    except Exception as e:
        yield {"type": "error", "message": str(e)}
        import traceback
        traceback.print_exc()
    finally:
        try:
            neo4j_driver.close()
            mongo_client.close()
        except:
            pass


def enqueue_file_processing(file_path: str, file_id: Any, user_id: str) -> None:
    """
    Enqueue file processing job with retry logic, including user_id
    
    Features:
    - Automatic retry on transient failures (max 2 retries)
    - Job timeout (30 minutes)
    - Failure callback for cleanup
    """
    file_record = {
        "_id": file_id,
        "name": os.path.basename(file_path),
        "path": file_path,
        "user_id": user_id  # Pass user_id to the job
    }
    
    logger.info(f"Enqueueing file for processing: {file_record['name']} (ID: {file_id}) for user {user_id}")
    
    try:
        job = q.enqueue(
            process_pdf_file_sync_wrapper,
            file_record,
            job_timeout='30m',  # Max 30 minutes per job
            retry=Retry(max=2),  # Retry 2 times on failure
            result_ttl=86400,  # Keep results for 24 hours
            failure_ttl=86400,  # Keep failed job info for 24 hours
            on_failure=on_job_failure  # Callback on job failure
        )
        logger.info(f"Job enqueued successfully: {job.id}")
        
    except Exception as e:
        logger.error(f"Failed to enqueue job: {e}", exc_info=True)
        raise


def on_job_failure(job, connection, type, value, traceback):
    """
    Callback when job fails - update file status
    """
    logger.error(f"Job {job.id} failed: {value}")
    
    # Extract file_id from job args
    try:
        from pymongo import MongoClient
        from datetime import datetime
        from bson import ObjectId
        
        file_record = job.args[0] if job.args else {}
        file_id = file_record.get("_id")
        
        if file_id:
            mongo_client = MongoClient(MONGODB_URI)
            db = mongo_client[MONGODB_DB]
            files_collection = db["files"]
            
            files_collection.update_one(
                {"_id": ObjectId(file_id)},
                {"$set": {
                    "status": "failed",
                    "error": f"Job failed: {str(value)}",
                    "updatedAt": datetime.utcnow()
                }}
            )
            mongo_client.close()
            logger.info(f"Updated file {file_id} status to failed")
    except Exception as e:
        logger.error(f"Failed to update status on job failure: {e}")
