from fastapi import FastAPI, UploadFile, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import os
import json
from pathlib import Path
from bson import ObjectId
from neo4j import GraphDatabase
from typing import AsyncGenerator

from app.db.collections.files import FileSchema
from app.utils.file import save_to_disk
from app.db.collections.files import files_collection
from app.workers_queue.workers import chat_with_character, ChatRequest
from app.workers_queue.workers import enqueue_file_processing

app = FastAPI(title="Comic Character Chat API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database & storage configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "character_chat")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
UPLOAD_ROOT = Path(os.getenv("UPLOAD_ROOT", "uploads")).resolve()
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


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
        qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
        qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        client = QdrantClient(host=qdrant_host, port=qdrant_port, timeout=5)
        client.get_collections()
        health_status["services"]["qdrant"] = "healthy"
    except Exception as e:
        health_status["services"]["qdrant"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        redis_host = os.getenv("REDIS_HOST", "redis")
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


@app.post("/upload")
async def upload_file(file: UploadFile, user_id: str = Header(..., alias="X-User-ID")):
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
        enqueue_file_processing(file_path, db_file.inserted_id, user_id)

        return {"file_id": str(db_file.inserted_id), "status": "queued"}

    except Exception as e:
        print(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/files")
async def get_files(user_id: str = Header(..., alias="X-User-ID")):
    """Get all uploaded files with their status for a specific user"""
    try:
        cursor = files_collection.find({"user_id": user_id})
        files = []
        async for doc in cursor:
            files.append({
                "_id": str(doc["_id"]),
                "name": doc["name"],
                "status": doc["status"],
                "path": doc.get("path"),
                "createdAt": doc.get("_id").generation_time.isoformat()
                if doc.get("_id") else None,
                "updatedAt": doc.get("updatedAt")
            })
        return files
    except Exception as e:
        print(f"Error fetching files: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch files")


@app.get("/files/{file_id}")
async def get_file_status(file_id: str, user_id: str = Header(..., alias="X-User-ID")):
    """Get status of a specific file, ensuring it belongs to the user"""
    try:
        doc = await files_collection.find_one({"_id": ObjectId(file_id), "user_id": user_id})
        if not doc:
            raise HTTPException(status_code=404, detail="File not found or access denied")

        return {
            "_id": str(doc["_id"]),
            "name": doc["name"],
            "status": doc["status"],
            "path": doc.get("path"),
            "createdAt": doc["_id"].generation_time.isoformat()
            if doc.get("_id") else None,
            "updatedAt": doc.get("updatedAt")
        }
    except Exception as e:
        print(f"Error fetching file status: {e}")
        raise HTTPException(status_code=500,
                            detail="Failed to fetch file status")


@app.get("/characters")
async def get_characters(
    file_id: str = Query(..., description="File ID to get characters from"),
    user_id: str = Header(..., alias="X-User-ID")
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
        driver = GraphDatabase.driver(NEO4J_URI,
                                      auth=(NEO4J_USER, NEO4J_PASSWORD))
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

        driver.close()
        return characters

    except Exception as e:
        print(f"Error fetching characters: {e}")
        raise HTTPException(status_code=500,
                            detail="Failed to fetch characters")


@app.get("/characters/{character_name}")
async def get_character_profile(character_name: str, user_id: str = Header(..., alias="X-User-ID")):
    """Get detailed profile of a specific character, ensuring it belongs to the user"""
    try:
        driver = GraphDatabase.driver(NEO4J_URI,
                                      auth=(NEO4J_USER, NEO4J_PASSWORD))
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
        driver.close()
        return profile

    except Exception as e:
        print(f"Error fetching character profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch character profile")


@app.get("/characters/{character_name}/relationships")
async def get_character_relationships(character_name: str, user_id: str = Header(..., alias="X-User-ID")):
    """Get relationships for a specific character, ensuring it belongs to the user"""
    try:
        driver = GraphDatabase.driver(NEO4J_URI,
                                      auth=(NEO4J_USER, NEO4J_PASSWORD))
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

        driver.close()
        return {"character": character_name, "relationships": relationships}

    except Exception as e:
        print(f"Error fetching character relationships: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch character relationships")


@app.get("/characters/{character_name}/status")
async def get_character_status(character_name: str, user_id: str = Header(..., alias="X-User-ID")):
    """
    Check if a character is ready for chat, ensuring it belongs to the user
    Returns readiness status and processing state
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
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
    finally:
        driver.close()


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


@app.post("/chat")
async def chat_with_character_endpoint(
    request: ChatRequest,
    user_id: str = Header(..., alias="X-User-ID")
):
    """Chat with a character - with status validation and user context"""
    
    # Simple validation to ensure request's user_id matches header
    if request.user_id != user_id:
        raise HTTPException(status_code=403, detail="User ID mismatch")

    # Check if character is ready
    status_response = await get_character_status(request.character_name, user_id)
    
    if not status_response["can_chat"]:
        raise HTTPException(
            status_code=425,  # Too Early
            detail={
                "message": status_response["message"],
                "status": status_response.get("status", "not_ready"),
                "ready": False
            }
        )
    
    # Character is ready (possibly with warning)
    try:
        response = chat_with_character(request)
        
        # Add warning if relationships still processing
        if status_response.get("warning"):
            response["warning"] = status_response["warning"]
        
        return response
    except Exception as e:
        print(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail="Chat failed")


@app.post("/chat/stream")
async def chat_with_character_stream(
    request: ChatRequest,
    user_id: str = Header(..., alias="X-User-ID")
):
    """
    Streaming chat endpoint - responses appear word-by-word
    Provides real-time status updates and progressive response delivery
    """
    # Simple validation to ensure request's user_id matches header
    if request.user_id != user_id:
        raise HTTPException(status_code=403, detail="User ID mismatch")
        
    async def generate_response() -> AsyncGenerator[str, None]:
        try:
            # Import here to avoid circular dependency
            from app.workers_queue.workers import chat_with_character_streaming
            
            # Stream the response
            async for chunk in chat_with_character_streaming(request):
                # Send as Server-Sent Events (SSE) format
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
async def get_chat_history(character: str = Query(..., description="Character name"),
                           user_id: str = Header(..., alias="X-User-ID")):
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
async def clear_chat_history(character: str = Query(..., description="Character name"),
                             user_id: str = Header(..., alias="X-User-ID")):
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
