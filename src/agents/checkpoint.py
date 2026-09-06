"""
MongoDB Checkpoint Configuration for LangGraph State Persistence.
Provides MongoDB-based checkpointing for the investment agent workflow.
"""

import os
from typing import Optional
from pymongo import MongoClient
from langgraph.checkpoint.mongodb import MongoDBSaver
from loguru import logger
from dotenv import load_dotenv

# ============================================
# FIX: Load environment variables FIRST
# ============================================
load_dotenv()


def get_mongodb_uri() -> str:
    """
    Retrieves MongoDB URI from environment variables.
    
    Returns:
        MongoDB connection URI string
    
    Raises:
        ValueError: If MONGODB_URI is not set in environment
    """
    # Reload .env to ensure latest values
    load_dotenv()
    
    mongodb_uri = os.getenv("MONGODB_URI")
    
    if not mongodb_uri:
        raise ValueError(
            "MONGODB_URI environment variable is not set. "
            "Please set it in your .env file or environment."
        )
    
    return mongodb_uri


def get_mongodb_database_name() -> str:
    """
    Retrieves MongoDB database name from environment variables.
    Defaults to 'investment_agents_db' if not set.
    
    Returns:
        MongoDB database name
    """
    # Reload .env to ensure latest values
    load_dotenv()
    
    return os.getenv("MONGODB_DB_NAME", os.getenv("MONGODB_DATABASE", "investment_agents_db"))


def get_mongodb_collection_name() -> str:
    """
    Retrieves MongoDB collection name for checkpoints from environment variables.
    Defaults to 'agent_checkpoints' if not set.
    
    Returns:
        MongoDB collection name for checkpoints
    """
    # Reload .env to ensure latest values
    load_dotenv()
    
    return os.getenv("MONGODB_COLLECTION_NAME", os.getenv("MONGODB_CHECKPOINT_COLLECTION", "checkpoints"))


def create_mongodb_checkpointer(
    mongodb_uri: Optional[str] = None,
    database_name: Optional[str] = None,
    collection_name: Optional[str] = None
) -> MongoDBSaver:
    """
    Creates a MongoDB checkpointer for LangGraph state persistence.
    
    Args:
        mongodb_uri: Optional MongoDB connection URI. If not provided, 
                    will be retrieved from MONGODB_URI environment variable.
        database_name: Optional database name. If not provided, will be retrieved
                      from MONGODB_DATABASE environment variable or use default.
        collection_name: Optional collection name. If not provided, will be 
                       retrieved from MONGODB_CHECKPOINT_COLLECTION environment 
                       variable or use default.
    
    Returns:
        MongoDBSaver instance for checkpointing
    
    Raises:
        ValueError: If MongoDB URI is not provided or cannot be retrieved
        Exception: If MongoDB connection fails
    """
    try:
        # Reload .env to ensure latest values
        load_dotenv()
        
        # Get MongoDB URI
        if not mongodb_uri:
            mongodb_uri = get_mongodb_uri()
        
        # Get database and collection names
        if not database_name:
            database_name = get_mongodb_database_name()
        if not collection_name:
            collection_name = get_mongodb_collection_name()
        
        logger.info(f"Creating MongoDB checkpointer for database: {database_name}, collection: {collection_name}")
        
        # Create MongoDB client
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        logger.info("MongoDB connection successful")
        
        # Create MongoDBSaver
        checkpointer = MongoDBSaver(
            client,
            database_name,
            collection_name
        )
        
        logger.info("MongoDB checkpointer created successfully")
        
        return checkpointer
        
    except Exception as e:
        logger.error(f"Failed to create MongoDB checkpointer: {str(e)}")
        raise


def create_mongodb_checkpointer_with_env() -> MongoDBSaver:
    """
    Creates a MongoDB checkpointer using environment variables.
    Convenience function that reads all configuration from environment.
    
    Returns:
        MongoDBSaver instance for checkpointing
    
    Raises:
        ValueError: If required environment variables are not set
        Exception: If MongoDB connection fails
    """
    return create_mongodb_checkpointer()


def test_mongodb_connection(mongodb_uri: Optional[str] = None) -> bool:
    """
    Tests MongoDB connection without creating a checkpointer.
    
    Args:
        mongodb_uri: Optional MongoDB connection URI. If not provided,
                    will be retrieved from MONGODB_URI environment variable.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        # Reload .env to ensure latest values
        load_dotenv()
        
        if not mongodb_uri:
            mongodb_uri = get_mongodb_uri()
        
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        logger.info("MongoDB connection test successful")
        return True
        
    except Exception as e:
        logger.error(f"MongoDB connection test failed: {str(e)}")
        return False


def clear_mongodb_checkpoints(
    mongodb_uri: Optional[str] = None,
    database_name: Optional[str] = None,
    collection_name: Optional[str] = None
) -> int:
    """
    Clears all checkpoints from MongoDB collection.
    Use with caution - this will delete all checkpoint data.
    
    Args:
        mongodb_uri: Optional MongoDB connection URI
        database_name: Optional database name
        collection_name: Optional collection name
    
    Returns:
        Number of documents deleted
    
    Raises:
        Exception: If deletion fails
    """
    try:
        # Reload .env to ensure latest values
        load_dotenv()
        
        if not mongodb_uri:
            mongodb_uri = get_mongodb_uri()
        if not database_name:
            database_name = get_mongodb_database_name()
        if not collection_name:
            collection_name = get_mongodb_collection_name()
        
        logger.warning(f"Clearing all checkpoints from {database_name}.{collection_name}")
        
        client = MongoClient(mongodb_uri)
        db = client[database_name]
        collection = db[collection_name]
        
        result = collection.delete_many({})
        
        logger.info(f"Cleared {result.deleted_count} checkpoints from MongoDB")
        
        return result.deleted_count
        
    except Exception as e:
        logger.error(f"Failed to clear MongoDB checkpoints: {str(e)}")
        raise


# ============================================================================
# EXAMPLE USAGE
# ============================================================================
if __name__ == "__main__":
    # Test MongoDB connection
    logger.info("Testing MongoDB connection...")
    if test_mongodb_connection():
        logger.info("MongoDB connection test passed")
        
        # Create checkpointer
        checkpointer = create_mongodb_checkpointer_with_env()
        logger.info("MongoDB checkpointer created successfully")
        
        # Note: The checkpointer is now ready to be used with LangGraph
        # Example: app = create_investment_graph(checkpointer=checkpointer)
        
    else:
        logger.error("MongoDB connection test failed. Please check your MONGODB_URI environment variable.")