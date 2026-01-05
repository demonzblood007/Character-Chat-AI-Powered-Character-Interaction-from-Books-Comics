"""
Character Repository
====================

Data access layer for character operations.
Handles MongoDB storage and Neo4j sync.
"""

import os
from typing import Optional, List, Tuple
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from neo4j import GraphDatabase

from .models import Character, CharacterCategory, CharacterVisibility


# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


class CharacterRepository:
    """
    Repository for character CRUD operations.
    
    Stores characters in MongoDB for rich queries.
    Syncs to Neo4j for chat integration.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db
        self._characters: AsyncIOMotorCollection = db["characters"]
        self._favorites: AsyncIOMotorCollection = db["user_favorites"]
        self._neo4j_driver = None
    
    async def ensure_indexes(self):
        """Create MongoDB indexes for efficient queries."""
        # Primary lookups
        await self._characters.create_index("creator_id")
        await self._characters.create_index("visibility")
        await self._characters.create_index("is_official")
        await self._characters.create_index("category")
        
        # Text search
        await self._characters.create_index([
            ("name", "text"),
            ("tagline", "text"),
            ("tags", "text"),
            ("source", "text"),
        ])
        
        # Popularity sorting
        await self._characters.create_index("chat_count")
        await self._characters.create_index("favorite_count")
        
        # Compound index for discovery
        await self._characters.create_index([
            ("visibility", 1),
            ("category", 1),
            ("chat_count", -1),
        ])
        
        # Favorites
        await self._favorites.create_index([
            ("user_id", 1),
            ("character_id", 1),
        ], unique=True)
    
    # ─────────────────────────────────────────────────────────────────
    # Character CRUD
    # ─────────────────────────────────────────────────────────────────
    
    async def create(self, character: Character) -> Character:
        """Create a new character."""
        doc = character.to_dict()
        doc["created_at"] = datetime.utcnow()
        doc["updated_at"] = datetime.utcnow()
        
        result = await self._characters.insert_one(doc)
        character.id = str(result.inserted_id)
        
        # Sync to Neo4j for chat integration
        await self._sync_to_neo4j(character)
        
        return character
    
    async def get_by_id(self, character_id: str) -> Optional[Character]:
        """Get character by ID."""
        # Avoid 500s on non-ObjectId inputs (e.g., frontend accidentally passing a name like "Poseidon")
        if not ObjectId.is_valid(character_id):
            return None
        doc = await self._characters.find_one({"_id": ObjectId(character_id)})
        return Character.from_dict(doc) if doc else None
    
    async def get_by_name_and_user(
        self, 
        name: str, 
        user_id: str
    ) -> Optional[Character]:
        """Get character by name for a specific user (including public)."""
        doc = await self._characters.find_one({
            "name": name,
            "$or": [
                {"creator_id": user_id},
                {"visibility": CharacterVisibility.PUBLIC.value},
            ]
        })
        return Character.from_dict(doc) if doc else None
    
    async def update(self, character: Character) -> Character:
        """Update an existing character."""
        character.updated_at = datetime.utcnow()
        
        await self._characters.update_one(
            {"_id": ObjectId(character.id)},
            {"$set": character.to_dict()}
        )
        
        # Sync to Neo4j
        await self._sync_to_neo4j(character)
        
        return character
    
    async def delete(self, character_id: str, user_id: str) -> bool:
        """Delete a character (only if owned by user)."""
        result = await self._characters.delete_one({
            "_id": ObjectId(character_id),
            "creator_id": user_id,
            "is_official": False,  # Can't delete official characters
        })
        
        if result.deleted_count > 0:
            # Remove from Neo4j
            await self._remove_from_neo4j(character_id, user_id)
            return True
        return False
    
    # ─────────────────────────────────────────────────────────────────
    # Discovery & Search
    # ─────────────────────────────────────────────────────────────────
    
    async def search(
        self,
        query: Optional[str] = None,
        category: Optional[CharacterCategory] = None,
        official_only: bool = False,
        limit: int = 20,
        skip: int = 0,
    ) -> Tuple[List[Character], int]:
        """
        Search public characters.
        
        Returns:
            Tuple of (characters, total_count)
        """
        filter_query = {"visibility": CharacterVisibility.PUBLIC.value}
        
        if query:
            filter_query["$text"] = {"$search": query}
        
        if category:
            filter_query["category"] = category.value
        
        if official_only:
            filter_query["is_official"] = True
        
        # Get total count
        total = await self._characters.count_documents(filter_query)
        
        # Get results
        cursor = self._characters.find(filter_query)
        
        # Sort by relevance if text search, otherwise by popularity
        if query:
            cursor = cursor.sort([("score", {"$meta": "textScore"})])
        else:
            cursor = cursor.sort([("chat_count", -1)])
        
        cursor = cursor.skip(skip).limit(limit)
        
        characters = []
        async for doc in cursor:
            characters.append(Character.from_dict(doc))
        
        return characters, total
    
    async def get_official_characters(
        self,
        category: Optional[CharacterCategory] = None,
        limit: int = 50,
    ) -> List[Character]:
        """Get official (pre-built) characters."""
        filter_query = {"is_official": True}
        
        if category:
            filter_query["category"] = category.value
        
        cursor = self._characters.find(filter_query).sort("chat_count", -1).limit(limit)
        
        characters = []
        async for doc in cursor:
            characters.append(Character.from_dict(doc))
        
        return characters
    
    async def get_user_characters(
        self,
        user_id: str,
        limit: int = 50,
    ) -> List[Character]:
        """Get characters created by a user."""
        cursor = self._characters.find({
            "creator_id": user_id
        }).sort("updated_at", -1).limit(limit)
        
        characters = []
        async for doc in cursor:
            characters.append(Character.from_dict(doc))
        
        return characters
    
    async def get_popular_characters(
        self,
        category: Optional[CharacterCategory] = None,
        limit: int = 10,
    ) -> List[Character]:
        """Get most popular public characters."""
        filter_query = {"visibility": CharacterVisibility.PUBLIC.value}
        
        if category:
            filter_query["category"] = category.value
        
        cursor = self._characters.find(filter_query).sort("chat_count", -1).limit(limit)
        
        characters = []
        async for doc in cursor:
            characters.append(Character.from_dict(doc))
        
        return characters
    
    async def get_by_category(
        self,
        category: CharacterCategory,
        limit: int = 20,
    ) -> List[Character]:
        """Get public characters by category."""
        cursor = self._characters.find({
            "visibility": CharacterVisibility.PUBLIC.value,
            "category": category.value,
        }).sort("chat_count", -1).limit(limit)
        
        characters = []
        async for doc in cursor:
            characters.append(Character.from_dict(doc))
        
        return characters
    
    # ─────────────────────────────────────────────────────────────────
    # Favorites
    # ─────────────────────────────────────────────────────────────────
    
    async def add_favorite(self, user_id: str, character_id: str) -> bool:
        """Add character to user's favorites."""
        try:
            await self._favorites.insert_one({
                "user_id": user_id,
                "character_id": character_id,
                "created_at": datetime.utcnow(),
            })
            
            # Increment favorite count
            await self._characters.update_one(
                {"_id": ObjectId(character_id)},
                {"$inc": {"favorite_count": 1}}
            )
            
            return True
        except Exception:
            # Already favorited
            return False
    
    async def remove_favorite(self, user_id: str, character_id: str) -> bool:
        """Remove character from user's favorites."""
        result = await self._favorites.delete_one({
            "user_id": user_id,
            "character_id": character_id,
        })
        
        if result.deleted_count > 0:
            # Decrement favorite count
            await self._characters.update_one(
                {"_id": ObjectId(character_id)},
                {"$inc": {"favorite_count": -1}}
            )
            return True
        return False
    
    async def get_user_favorites(
        self,
        user_id: str,
        limit: int = 50,
    ) -> List[Character]:
        """Get user's favorite characters."""
        # Get favorite character IDs
        cursor = self._favorites.find({"user_id": user_id}).limit(limit)
        
        character_ids = []
        async for doc in cursor:
            character_ids.append(ObjectId(doc["character_id"]))
        
        if not character_ids:
            return []
        
        # Get characters
        cursor = self._characters.find({"_id": {"$in": character_ids}})
        
        characters = []
        async for doc in cursor:
            characters.append(Character.from_dict(doc))
        
        return characters
    
    async def is_favorite(self, user_id: str, character_id: str) -> bool:
        """Check if character is in user's favorites."""
        doc = await self._favorites.find_one({
            "user_id": user_id,
            "character_id": character_id,
        })
        return doc is not None
    
    # ─────────────────────────────────────────────────────────────────
    # Stats
    # ─────────────────────────────────────────────────────────────────
    
    async def increment_chat_count(self, character_id: str):
        """Increment chat count when a conversation starts."""
        await self._characters.update_one(
            {"_id": ObjectId(character_id)},
            {"$inc": {"chat_count": 1}}
        )
    
    # ─────────────────────────────────────────────────────────────────
    # Neo4j Sync (for chat integration)
    # ─────────────────────────────────────────────────────────────────
    
    def _get_neo4j_driver(self):
        """Get or create Neo4j driver."""
        if self._neo4j_driver is None:
            self._neo4j_driver = GraphDatabase.driver(
                NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
        return self._neo4j_driver
    
    async def _sync_to_neo4j(self, character: Character):
        """Sync character to Neo4j for chat integration."""
        try:
            driver = self._get_neo4j_driver()
            with driver.session() as session:
                session.run("""
                    MERGE (c:Character {name: $name, user_id: $user_id})
                    SET c.description = $description,
                        c.character_id = $character_id,
                        c.is_library_character = true,
                        c.updated_at = datetime()
                """,
                    name=character.name,
                    user_id=character.creator_id,
                    description=character.persona.description,
                    character_id=character.id,
                )
        except Exception as e:
            print(f"Failed to sync character to Neo4j: {e}")
    
    async def _remove_from_neo4j(self, character_id: str, user_id: str):
        """Remove character from Neo4j."""
        try:
            driver = self._get_neo4j_driver()
            with driver.session() as session:
                session.run("""
                    MATCH (c:Character {character_id: $character_id, user_id: $user_id})
                    DETACH DELETE c
                """,
                    character_id=character_id,
                    user_id=user_id,
                )
        except Exception as e:
            print(f"Failed to remove character from Neo4j: {e}")

