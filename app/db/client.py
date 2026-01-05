import os
import atexit
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/character_chat")
MONGODB_DB = os.getenv("MONGODB_DB", "character_chat")

_async_client = AsyncIOMotorClient(MONGODB_URI)
_sync_client = MongoClient(MONGODB_URI)


def get_async_client() -> AsyncIOMotorClient:
    """Return the shared Motor client."""
    return _async_client


def get_sync_client() -> MongoClient:
    """Return the shared synchronous Mongo client."""
    return _sync_client


def get_async_database():
    """Return the async database handle."""
    return _async_client[MONGODB_DB]


def get_sync_database():
    """Return the sync database handle."""
    return _sync_client[MONGODB_DB]


def close_connections():
    """Close all MongoDB connections gracefully."""
    global _async_client, _sync_client
    try:
        if _async_client is not None:
            _async_client.close()
        if _sync_client is not None:
            _sync_client.close()
        print("MongoDB connections closed")
    except Exception as e:
        print(f"Error closing MongoDB connections: {e}")


# Register cleanup function to run at exit
atexit.register(close_connections)
