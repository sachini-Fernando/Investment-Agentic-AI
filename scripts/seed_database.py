"""
Database seeding script for the Investment Agentic AI system.
Initializes ChromaDB for vector storage and MongoDB for state persistence.
"""

import os
import sys
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()


def seed_chroma_db():
    """
    Initializes ChromaDB for vector storage.
    """
    logger.info("Seeding ChromaDB...")
    
    try:
        from src.pipeline import NewsVectorStore

        vector_store = NewsVectorStore()
        if vector_store.available:
            _ = vector_store.collection
            logger.info(f"ChromaDB collection '{vector_store.collection_name}' is ready")
        else:
            logger.warning("ChromaDB is not available. Install chromadb to enable vector search.")
        
    except Exception as e:
        logger.error(f"Error seeding ChromaDB: {str(e)}")
        raise


def test_mongodb_connection():
    """
    Tests MongoDB connection if configured.
    """
    logger.info("Testing MongoDB connection...")
    
    try:
        from pymongo import MongoClient
        
        mongodb_uri = os.getenv("MONGODB_URI")
        
        if not mongodb_uri:
            logger.warning("MONGODB_URI not found in environment variables")
            logger.info("Skipping MongoDB connection test")
            return False
        
        # Test connection
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        client.server_info()
        
        logger.info("MongoDB connection successful!")
        
        # Test database/collection creation
        db_name = os.getenv("MONGODB_DB_NAME", "investment_agent")
        collection_name = os.getenv("MONGODB_COLLECTION_NAME", "checkpoints")
        
        db = client[db_name]
        collection = db[collection_name]
        
        # Insert a test document
        test_doc = {"test": "seed", "timestamp": "2024-01-01"}
        collection.insert_one(test_doc)
        
        # Clean up test document
        collection.delete_one({"test": "seed"})
        
        logger.info(f"MongoDB database '{db_name}' and collection '{collection_name}' are ready")
        
        client.close()
        return True
        
    except Exception as e:
        logger.error(f"MongoDB connection test failed: {str(e)}")
        logger.warning("MongoDB features will be unavailable")
        return False


def create_data_directories():
    """
    Creates necessary data directories if they don't exist.
    """
    logger.info("Creating data directories...")
    
    directories = [
        "data/raw",
        "data/processed",
        "data/chroma_db"
    ]
    
    for dir_path in directories:
        full_path = project_root / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {dir_path}")


def main():
    """
    Main function to seed all databases and initialize the system.
    """
    logger.info("="*80)
    logger.info("INVESTSAGE - DATABASE SEEDING")
    logger.info("="*80)
    
    try:
        # Create data directories
        create_data_directories()
        
        # Seed ChromaDB (placeholder)
        seed_chroma_db()
        
        # Test MongoDB connection
        test_mongodb_connection()
        
        logger.info("="*80)
        logger.info("DATABASE SEEDING COMPLETED")
        logger.info("="*80)
        logger.info("\nNext steps:")
        logger.info("1. Copy .env.example to .env and configure your API keys")
        logger.info("2. Run: python main.py AAPL")
        logger.info("3. Or run the Streamlit UI: streamlit run app/streamlit_app.py")
        
    except Exception as e:
        logger.error(f"Database seeding failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
