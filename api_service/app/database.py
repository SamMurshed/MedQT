"""Database utilities for managing the MongoDB client and database instance.

This module provides helper functions to retrieve a shared async MongoDB client
using Motor. The client is lazily created on first use and reused for performance.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

_mongo_client_instance: AsyncIOMotorClient | None = None


def _build_connection_string() -> str:
    """Construct and return a MongoDB connection URI from settings."""
    return (
        f"mongodb://{settings.mongo_username}:{settings.mongo_password}"
        f"@{settings.mongo_host}:{settings.mongo_port}/"
        f"{settings.mongo_database_name}?authSource={settings.mongo_database_name}"
    )


def get_mongo_client() -> AsyncIOMotorClient:
    """
    Return the shared async MongoDB client instance.
    If none exists, create one using configuration values.

    Returns
    -------
    AsyncIOMotorClient
        The cached or newly created MongoDB client.
    """
    global _mongo_client_instance

    if _mongo_client_instance is None:
        _mongo_client_instance = AsyncIOMotorClient(_build_connection_string())

    return _mongo_client_instance


def close_mongo_client() -> None:
    """
    Close and reset the MongoDB client.

    This is mainly used in testing to avoid event loop conflicts or
    leftover async connections.
    """
    global _mongo_client_instance

    if _mongo_client_instance:
        _mongo_client_instance.close()
        _mongo_client_instance = None


def get_database():
    """
    Return a Motor async database instance for the configured DB name.

    Returns
    -------
    motor.motor_asyncio.AsyncIOMotorDatabase
        The database object associated with the MongoDB client.
    """
    return get_mongo_client()[settings.mongo_database_name]
