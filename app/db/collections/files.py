from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import BaseModel, Field

from ..db import database


class FileSchema(BaseModel):
    name: str = Field(..., description="Name of the file")
    user_id: str = Field(..., description="The ID of the user who owns the file")
    status: str = Field(..., description="Status of the file (queued, processing, extracting_characters, extracting_relationships, done, failed)")
    path: Optional[str] = Field(None, description="Path to the uploaded file")
    error: Optional[str] = Field(None, description="Error message if processing failed")
    processed_at: Optional[datetime] = Field(None, description="Timestamp when processing completed")
    character_count: Optional[int] = Field(None, description="Number of characters extracted")
    relationship_count: Optional[int] = Field(None, description="Number of relationships extracted")
    chunk_count: Optional[int] = Field(None, description="Number of text chunks created")


COLLECTION_NAME = "files"
files_collection: AsyncIOMotorCollection = database[COLLECTION_NAME]
