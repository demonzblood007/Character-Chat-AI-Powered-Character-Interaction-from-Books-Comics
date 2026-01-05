from fastapi import FastAPI, UploadFile, HTTPException, Query, Header, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import os
import json
import asyncio
import shutil
from pathlib import Path
from bson import ObjectId
from neo4j import GraphDatabase
from typing import AsyncGenerator, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from app.db.collections.files import FileSchema
from app.utils.file import save_to_disk
from app.db.collections.files import files_collection

# Authentication imports
from app.auth import auth_router, get_current_user, get_current_user_optional
from app.users.models import User
from app.db.db import database

# New chat service imports
from app.chat.manager import get_chat_manager, get_chat_service
from app.chat.service import ChatService

app = FastAPI(
    title="Character Chat API",
    version="2.0.0",
    description="AI-powered character interaction from books and comics",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication router
app.include_router(auth_router)

# Include v2 chat router (with memory integration)
from app.chat.router import router as chat_v2_router
app.include_router(chat_v2_router)

# Include character library router
from app.characters.router import router as character_router
app.include_router(character_router)

# Database & storage configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "character_chat")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
UPLOAD_ROOT = Path(os.getenv("UPLOAD_ROOT", "uploads")).resolve()
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


async def _rm_tree(path: Path) -> None:
    """Remove a directory tree without blocking the event loop."""
    if not path.exists():
        return
    await asyncio.to_thread(shutil.rmtree, path, True)

# Neo4j connection pool (shared driver instance)
_neo4j_driver = None

def get_neo4j_driver():
    """Get or create a shared Neo4j driver instance with connection pooling."""
    global _neo4j_driver
    if _neo4j_driver is None:
        _neo4j_driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
            connection_acquisition_timeout=60
        )
    return _neo4j_driver


@app.get("/")
def hello():
    return {"status": "health",
            "message": "Comic Character Chat API is running"}


@app.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint
    Verifies all services (MongoDB, Neo4j, Qdrant, Redis) are accessible
    """
    from redis import Redis
    import os
    
    health_status = {
        "status": "healthy",
        "services": {},
        "timestamp": None
    }
    
    from datetime import datetime
    health_status["timestamp"] = datetime.utcnow().isoformat()
    
    # Check MongoDB
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        await mongo.server_info()
        health_status["services"]["mongodb"] = "healthy"
        mongo.close()
    except Exception as e:
        health_status["services"]["mongodb"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Neo4j
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        health_status["services"]["neo4j"] = "healthy"
    except Exception as e:
        health_status["services"]["neo4j"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Qdrant
    try:
        from qdrant_client import QdrantClient
        qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        client = QdrantClient(host=qdrant_host, port=qdrant_port, timeout=5)
        client.get_collections()
        health_status["services"]["qdrant"] = "healthy"
    except Exception as e:
        health_status["services"]["qdrant"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_conn = Redis(host=redis_host, port=redis_port, socket_timeout=5)
        redis_conn.ping()
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Set overall status based on critical services
    unhealthy_count = sum(1 for v in health_status["services"].values() if "unhealthy" in v)
    if unhealthy_count >= 3:
        health_status["status"] = "unhealthy"
    
    return health_status


async def get_user_id(
    current_user: Optional[User] = Depends(get_current_user_optional),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
) -> str:
    """
    Get user ID from JWT token or X-User-ID header.
    Supports both new JWT auth and legacy header auth for backward compatibility.
    """
    if current_user:
        return current_user.id
    if x_user_id:
        return x_user_id
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide JWT token or X-User-ID header."
    )

class LegacyChatRequest(BaseModel):
    """
    Legacy chat request model (deprecated).

    - `user_id` is accepted for backwards compatibility but ignored; auth context wins.
    - v2 chat uses the `X-User-ID` header or JWT token instead.
    """
    character_name: str
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None


@app.post("/upload")
async def upload_file(
    file: UploadFile,
    user_id: str = Depends(get_user_id),
):
    """Upload a PDF file for processing with comprehensive validation"""
    import os
    
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400,
                                detail="Only PDF files are supported")
        
        # Read file content for validation
        file_content = await file.read()
        file_size_mb = len(file_content) / (1024 * 1024)
        
        # Validate file size
        max_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", 50))
        if file_size_mb > max_size_mb:
            raise HTTPException(
                status_code=413,  # Payload Too Large
                detail=f"File too large: {file_size_mb:.1f}MB (max: {max_size_mb}MB)"
            )
        
        if file_size_mb == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Validate PDF header (magic bytes)
        if not file_content.startswith(b'%PDF'):
            raise HTTPException(status_code=400, detail="File is not a valid PDF")

        file_doc = FileSchema(
            name=file.filename,
            status="saving",
            user_id=user_id
        )

        # Insert file record
        db_file = await files_collection.insert_one(
            document=file_doc.model_dump()
        )

        # Create upload directory using user_id for isolation
        file_dir = UPLOAD_ROOT / user_id / str(db_file.inserted_id)
        file_dir.mkdir(parents=True, exist_ok=True)
        file_path = file_dir / file.filename
        
        # Save file to disk (file_content already read for validation)
        await save_to_disk(file=file_content, path=str(file_path))
        
        print(f"File saved: {file.filename} ({file_size_mb:.2f}MB)")

        # Update file record with path
        await files_collection.update_one(
            {"_id": db_file.inserted_id},
            {"$set": {"path": str(file_path), "status": "queued"}}
        )

        # Enqueue for processing with user_id context
        from app.workers_queue.workers import enqueue_file_processing
        enqueue_file_processing(file_path, db_file.inserted_id, user_id)

        # Return response matching BookFile schema
        from datetime import datetime
        upload_date = datetime.utcnow().isoformat()
        return {
            "id": str(db_file.inserted_id),
            "filename": file.filename,
            "upload_date": upload_date,
            "status": "queued",
            "character_count": None,
            "relationship_count": None,
        }

    except Exception as e:
        print(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/files")
async def get_files(user_id: str = Depends(get_user_id)):
    """Get all uploaded files with their status for a specific user"""
    try:
        print(f"🔍 Fetching files for user_id: {user_id}")
        cursor = files_collection.find({"user_id": user_id})
        files = []
        count = 0
        async for doc in cursor:
            count += 1
            # Get upload date from ObjectId generation time or createdAt
            upload_date = None
            if doc.get("_id"):
                upload_date = doc["_id"].generation_time.isoformat()
            elif doc.get("createdAt"):
                upload_date = doc["createdAt"].isoformat() if hasattr(doc["createdAt"], "isoformat") else str(doc["createdAt"])
            
            files.append({
                "id": str(doc["_id"]),
                "filename": doc["name"],
                "upload_date": upload_date or "",
                "status": doc["status"],
                "character_count": doc.get("character_count"),
                "relationship_count": doc.get("relationship_count"),
            })
        print(f"✅ Found {count} files for user_id: {user_id}")
        return files
    except Exception as e:
        print(f"❌ Error fetching files: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to fetch files")


@app.get("/files/{file_id}")
async def get_file_status(file_id: str, user_id: str = Depends(get_user_id)):
    """Get status of a specific file, ensuring it belongs to the user"""
    try:
        doc = await files_collection.find_one({"_id": ObjectId(file_id), "user_id": user_id})
        if not doc:
            raise HTTPException(status_code=404, detail="File not found or access denied")

        # Get upload date from ObjectId generation time or createdAt
        upload_date = None
        if doc.get("_id"):
            upload_date = doc["_id"].generation_time.isoformat()
        elif doc.get("createdAt"):
            upload_date = doc["createdAt"].isoformat() if hasattr(doc["createdAt"], "isoformat") else str(doc["createdAt"])

        return {
            "id": str(doc["_id"]),
            "filename": doc["name"],
            "upload_date": upload_date or "",
            "status": doc["status"],
            "character_count": doc.get("character_count"),
            "relationship_count": doc.get("relationship_count"),
        }
    except Exception as e:
        print(f"Error fetching file status: {e}")
        raise HTTPException(status_code=500,
                            detail="Failed to fetch file status")


@app.post("/files/{file_id}/reprocess")
async def reprocess_file(file_id: str, user_id: str = Depends(get_user_id)):
    """
    Re-queue an existing upload for processing.
    This is the primary recovery path if a previous run failed due to transient dependency issues.
    """
    try:
        doc = await files_collection.find_one({"_id": ObjectId(file_id), "user_id": user_id})
        if not doc:
            raise HTTPException(status_code=404, detail="File not found or access denied")

        file_path = doc.get("path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=400, detail="Stored file path is missing; please re-upload the file.")

        await files_collection.update_one(
            {"_id": ObjectId(file_id), "user_id": user_id},
            {"$set": {"status": "queued", "error": None, "character_count": None, "relationship_count": None}},
        )

        from app.workers_queue.workers import enqueue_file_processing
        enqueue_file_processing(file_path, ObjectId(file_id), user_id)

        upload_date = doc["_id"].generation_time.isoformat() if doc.get("_id") else ""
        return {
            "id": str(doc["_id"]),
            "filename": doc.get("name", ""),
            "upload_date": upload_date or "",
            "status": "queued",
            "character_count": None,
            "relationship_count": None,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error reprocessing file: {e}")
        raise HTTPException(status_code=500, detail="Failed to reprocess file")


@app.delete("/files/{file_id}")
async def delete_file(file_id: str, user_id: str = Depends(get_user_id)):
    """
    Delete an upload and its derived artifacts so it disappears from the user's uploads list.
    This addresses the UX case where a user uploaded a file but extraction failed / produced nothing.
    """
    try:
        doc = await files_collection.find_one({"_id": ObjectId(file_id), "user_id": user_id})
        if not doc:
            raise HTTPException(status_code=404, detail="File not found or access denied")

        deleted = {
            "deleted_file_id": file_id,
            "deleted_upload_dir": False,
            "deleted_qdrant_chunks": 0,
            "deleted_qdrant_memories": 0,
            "deleted_neo4j_characters": 0,
            "deleted_chat_sessions": 0,
            "deleted_memories": 0,
            "deleted_entities": 0,
            "character_names": [],
        }

        # 0) Resolve which extracted characters belong to this file (used to cascade-delete chats/memory)
        try:
            driver = get_neo4j_driver()
            with driver.session() as session:
                res = session.run(
                    "MATCH (c:Character {file_id: $file_id, user_id: $user_id}) RETURN c.name AS name",
                    file_id=file_id,
                    user_id=user_id,
                )
                deleted["character_names"] = [r["name"] for r in res if r.get("name")]
        except Exception as ne:
            print(f"Warning: failed to list Neo4j characters for file {file_id}: {ne}")
            deleted["character_names"] = []

        # 1) Delete uploaded file from disk
        upload_dir = UPLOAD_ROOT / user_id / file_id
        await _rm_tree(upload_dir)
        deleted["deleted_upload_dir"] = True

        # 2) Delete vector chunks from Qdrant (filter by file_id + user_id)
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            from app.utils.qdrant_names import qdrant_collection_name

            qdrant = QdrantClient(
                host=os.getenv("QDRANT_HOST", "qdrant"),
                port=int(os.getenv("QDRANT_PORT", "6333")),
            )
            q_filter = Filter(must=[
                FieldCondition(key="file_id", match=MatchValue(value=file_id)),
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            ])
            base = os.getenv("QDRANT_CHUNKS_COLLECTION", "comic_chunks")
            cols = [c.name for c in qdrant.get_collections().collections]
            # Best-effort delete across base and dimension-suffixed variants.
            for c in cols:
                if c == base or c.startswith(f"{base}_d"):
                    qdrant.delete(collection_name=c, points_selector=q_filter, wait=True)
                    deleted["deleted_qdrant_chunks"] += 1
        except Exception as qe:
            # Non-fatal: we still remove the upload record to fix the user's UI.
            print(f"Warning: failed to delete Qdrant points for file {file_id}: {qe}")

        # 2b) Cascade delete chats/memories/entities associated with extracted characters from this file
        try:
            names = deleted["character_names"]
            if names:
                sessions_col = database["chat_sessions"]
                entities_col = database["entities"]
                memories_col = database["memories"]

                # Delete sessions (contains full message history + working memory)
                res = await sessions_col.delete_many({"user_id": user_id, "character_name": {"$in": names}})
                deleted["deleted_chat_sessions"] = int(res.deleted_count or 0)

                # Delete entities extracted for this user/character scope
                res = await entities_col.delete_many({"user_id": user_id, "character_name": {"$in": names}})
                deleted["deleted_entities"] = int(res.deleted_count or 0)

                # Collect embedding ids before deleting memory docs
                embedding_ids = []
                cursor = memories_col.find(
                    {"user_id": user_id, "character_name": {"$in": names}},
                    projection={"embedding_id": 1},
                )
                async for m in cursor:
                    eid = m.get("embedding_id")
                    if eid:
                        embedding_ids.append(eid)

                res = await memories_col.delete_many({"user_id": user_id, "character_name": {"$in": names}})
                deleted["deleted_memories"] = int(res.deleted_count or 0)

                # Delete memory vectors from Qdrant (best-effort across base + dim-suffixed)
                if embedding_ids:
                    try:
                        from qdrant_client import QdrantClient

                        qdrant = QdrantClient(
                            host=os.getenv("QDRANT_HOST", "qdrant"),
                            port=int(os.getenv("QDRANT_PORT", "6333")),
                        )
                        memory_base = os.getenv("QDRANT_MEMORY_COLLECTION", "character_memories")
                        cols = [c.name for c in qdrant.get_collections().collections]
                        for c in cols:
                            if c == memory_base or c.startswith(f"{memory_base}_d"):
                                qdrant.delete(collection_name=c, points_selector=embedding_ids, wait=True)
                                deleted["deleted_qdrant_memories"] += 1
                    except Exception as me:
                        print(f"Warning: failed to delete Qdrant memory vectors for file {file_id}: {me}")
        except Exception as ce:
            print(f"Warning: cascade delete failed for file {file_id}: {ce}")

        # 3) Delete characters/relationships from Neo4j for that file+user
        try:
            driver = get_neo4j_driver()
            with driver.session() as session:
                result = session.run(
                    "MATCH (c:Character {file_id: $file_id, user_id: $user_id}) DETACH DELETE c",
                    file_id=file_id,
                    user_id=user_id,
                )
                # Neo4j python driver does not reliably expose deleted counts; we approximate via pre-query list length
                deleted["deleted_neo4j_characters"] = len(deleted["character_names"])
        except Exception as ne:
            print(f"Warning: failed to delete Neo4j nodes for file {file_id}: {ne}")

        # 4) Delete file record from Mongo (this removes it from /files list)
        await files_collection.delete_one({"_id": ObjectId(file_id), "user_id": user_id})

        deleted["ok"] = True
        return deleted
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting file: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete file")


@app.get("/characters")
async def get_characters(
    file_id: str = Query(..., description="File ID to get characters from"),
    user_id: str = Depends(get_user_id),
):
    """Get characters extracted from a processed file, verifying user ownership"""
    try:
        # First check if file exists, belongs to the user, and is processed
        file_doc = await files_collection.find_one({"_id": ObjectId(file_id), "user_id": user_id})
        if not file_doc:
            raise HTTPException(status_code=404, detail="File not found or access denied")

        if file_doc["status"] != "done":
            raise HTTPException(status_code=400,
                                detail="File is not yet processed")

        # Get characters from Neo4j, filtered by file_id AND user_id for security
        driver = get_neo4j_driver()
        with driver.session() as session:
            result = session.run(
                "MATCH (c:Character {file_id: $file_id, user_id: $user_id}) RETURN c.name as name, c.description as description, c.powers as powers, c.story_arcs as story_arcs",
                file_id=file_id,
                user_id=user_id
            )
            characters = []
            for record in result:
                character = {
                    "name": record["name"],
                    "description": record["description"],
                    "powers": record["powers"] or [],
                    "story_arcs": record["story_arcs"] or [],
                    "avatar": f"https://api.dicebear.com/7.x/avataaars/svg?seed={record['name']}"
                }
                characters.append(character)

        return characters

    except Exception as e:
        print(f"Error fetching characters: {e}")
        raise HTTPException(status_code=500,
                            detail="Failed to fetch characters")


@app.get("/characters/{character_name}")
async def get_character_profile(character_name: str, user_id: str = Depends(get_user_id)):
    """Get detailed profile of a specific character, ensuring it belongs to the user"""
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            # Get character details, filtering by name AND user_id
            result = session.run(
                """
                MATCH (c:Character {name: $name, user_id: $user_id})
                RETURN c.name as name, c.description as description, c.powers as powers,
                       c.story_arcs as story_arcs
                """,
                name=character_name,
                user_id=user_id
            )
            record = result.single()

            if not record:
                raise HTTPException(status_code=404,
                                    detail="Character not found")

            # Get relationships
            rel_result = session.run(
                """
                MATCH (c:Character {name: $name, user_id: $user_id})-[r:RELATION]->(target:Character)
                RETURN target.name as target, r.type as type
                """,
                name=character_name,
                user_id=user_id
            )

            relationships = []
            for rel_record in rel_result:
                relationships.append({
                    "target": rel_record["target"],
                    "type": rel_record["type"]
                })

            profile = {
                "name": record["name"],
                "description": record["description"] or "",
                "powers": record["powers"] or [],
                "story_arcs": record["story_arcs"] or [],
                "relationships": relationships,
                "personality_traits": [],  # Could be extracted from description
                "emotional_state": "neutral",  # Default
                "motivations": []  # Could be extracted from description
            }
        return profile

    except Exception as e:
        print(f"Error fetching character profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch character profile")


@app.get("/characters/{character_name}/relationships")
async def get_character_relationships(character_name: str, user_id: str = Depends(get_user_id)):
    """Get relationships for a specific character, ensuring it belongs to the user"""
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            result = session.run(
                """
                MATCH (c:Character {name: $name, user_id: $user_id})-[r:RELATION]->(target:Character)
                RETURN target.name as target, r.type as type
                """,
                name=character_name,
                user_id=user_id
            )

            relationships = []
            for record in result:
                relationships.append({
                    "target": record["target"],
                    "type": record["type"],
                    "strength": 1,  # Default strength
                    "description": f"{character_name} has a {record['type']} relationship with {record['target']}"
                })

        return {"character": character_name, "relationships": relationships}

    except Exception as e:
        print(f"Error fetching character relationships: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch character relationships")


@app.get("/characters/{character_name}/status")
async def get_character_status(character_name: str, user_id: str = Depends(get_user_id)):
    """
    Check if a character is ready for chat, ensuring it belongs to the user
    Returns readiness status and processing state
    """
    driver = get_neo4j_driver()
    
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (c:Character {name: $name, user_id: $user_id})
                RETURN c.name as name, 
                       c.description as description,
                       c.file_id as file_id
            """, name=character_name, user_id=user_id)
            record = result.single()
            
            if record:
                # Character exists, check file processing status
                file_id = record.get('file_id')
                
                if file_id:
                    file_doc = await files_collection.find_one({
                        "_id": ObjectId(file_id),
                        "user_id": user_id  # Verify user ownership of the file
                    })
                    
                    if file_doc:
                        status = file_doc.get('status', 'unknown')
                        
                        return {
                            "ready": True,
                            "character": character_name,
                            "status": status,
                            "message": get_status_message(status),
                            "can_chat": status in ['extracting_relationships', 'done'],
                            "warning": "Relationship data still processing" if status == 'extracting_relationships' else None
                        }
                
                # Character exists but no file status
                return {
                    "ready": True,
                    "character": character_name,
                    "can_chat": True,
                    "status": "available"
                }
            else:
                # Character not found
                return {
                    "ready": False,
                    "character": character_name,
                    "message": f"Character '{character_name}' not found. Still processing?",
                    "can_chat": False
                }
    except Exception as e:
        print(f"Error checking character status: {e}")
        raise HTTPException(status_code=500, detail="Failed to check character status")


def get_status_message(status: str) -> str:
    """Helper to get user-friendly status messages"""
    messages = {
        "queued": "Your file is queued for processing. This usually takes 1-2 minutes.",
        "processing": "Extracting text from your document...",
        "extracting_characters": "Finding characters in your story... Almost ready!",
        "extracting_relationships": "Character is ready! (Still analyzing relationships)",
        "done": "All set! Your character is fully ready.",
        "failed": "Processing failed. Please try uploading again."
    }
    return messages.get(status, "Processing...")


@app.post("/chat", deprecated=True, tags=["Chat (deprecated)"])
async def chat_with_character_endpoint(
    request: LegacyChatRequest,
    response: Response,
    user_id: str = Depends(get_user_id),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    DEPRECATED: Legacy chat endpoint.

    This endpoint is kept for backwards compatibility, but it now routes through
    the v2 chat service (memory + provider abstraction + metrics).

    Use: POST /v2/chat
    """
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</v2/chat>; rel="successor-version"'

    result = await chat_service.chat(
        user_id=user_id,
        character_name=request.character_name,
        message=request.message,
    )

    if result.error:
        if result.error == "CHARACTER_NOT_FOUND":
            raise HTTPException(status_code=404, detail=result.response)
        raise HTTPException(status_code=500, detail=result.error)

    # Keep legacy shape but include v2 metadata for clients that want it
    return {
        "response": result.response,
        "character": result.character,
        "timestamp": result.timestamp,
        "session_id": result.session_id,
        "memories_used": result.memories_used,
        "is_new_session": result.is_new_session,
        "tokens_used": result.tokens_used,
    }


@app.post("/chat/stream", deprecated=True, tags=["Chat (deprecated)"])
async def chat_with_character_stream(
    request: LegacyChatRequest,
    user_id: str = Depends(get_user_id),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    DEPRECATED: Legacy streaming chat endpoint.

    This endpoint is kept for backwards compatibility, but it now routes through
    the v2 chat service streaming path (true provider streaming when available).

    Use: POST /v2/chat/stream
    """
    async def generate_response() -> AsyncGenerator[str, None]:
        try:
            async for chunk in chat_service.chat_stream(
                user_id=user_id,
                character_name=request.character_name,
                message=request.message,
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            error_msg = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_msg)}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@app.get("/chat/history")
async def get_chat_history(
    character: str = Query(..., description="Character name"),
    user_id: str = Depends(get_user_id),
):
    """Get chat history for a user-character pair"""
    from motor.motor_asyncio import AsyncIOMotorClient
    mongo = AsyncIOMotorClient(MONGODB_URI)
    try:
        db = mongo[MONGODB_DB]
        chats = db["chat_sessions"]

        session = await chats.find_one(
            {"user_id": user_id, "character": character}
        )

        if not session:
            return {"messages": []}

        return {"messages": session.get("messages", [])}

    except Exception as e:
        print(f"Error fetching chat history: {e}")
        raise HTTPException(status_code=500,
                            detail="Failed to fetch chat history")
    finally:
        mongo.close()


@app.delete("/chat/history")
async def clear_chat_history(
    character: str = Query(..., description="Character name"),
    user_id: str = Depends(get_user_id),
):
    """Clear chat history for a user-character pair"""
    from motor.motor_asyncio import AsyncIOMotorClient
    mongo = AsyncIOMotorClient(MONGODB_URI)
    try:
        db = mongo[MONGODB_DB]
        chats = db["chat_sessions"]

        await chats.delete_one({"user_id": user_id, "character": character})
        return {"message": "Chat history cleared"}

    except Exception as e:
        print(f"Error clearing chat history: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear chat history")
    finally:
        mongo.close()


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


# Startup handler
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    print("🚀 Starting Character Chat API...")
    
    # Initialize chat service (LLM, memory, etc.)
    try:
        manager = get_chat_manager()
        await manager.initialize()
    except Exception as e:
        print(f"⚠️ Chat service initialization failed: {e}")
        print("   Chat v2 endpoints will initialize on first request.")
    
    # Initialize character library (seeds pre-built characters)
    try:
        from app.characters.service import get_character_service
        print("📚 Initializing Character Library...")
        await get_character_service()
        print("✅ Character Library ready!")
    except Exception as e:
        print(f"⚠️ Character library initialization failed: {e}")


# Shutdown handlers for graceful cleanup
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up database connections on shutdown."""
    global _neo4j_driver
    
    # Close Neo4j
    if _neo4j_driver is not None:
        _neo4j_driver.close()
        _neo4j_driver = None
        print("Neo4j driver closed")
    
    # Close chat service
    try:
        manager = get_chat_manager()
        await manager.shutdown()
    except Exception as e:
        print(f"Chat service shutdown error: {e}")
