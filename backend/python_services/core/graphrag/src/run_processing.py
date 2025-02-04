import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
import logging
from datetime import datetime
from core.graphrag.src.message_processor import process_messages, connect_to_mongodb, fix_session_ids, process_existing_messages
from core.graphrag.src.conversation_processor import (
    diagnose_conversations,
    analyze_conversations,
    update_conversation_analysis,
    deduplicate_conversations
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_connections():
    """Initialize all necessary connections"""
    try:
        # Connect to MongoDB first
        logger.info("Connecting to MongoDB...")
        messages_collection = connect_to_mongodb()
        
        # Connect to Neo4j
        logger.info("Connecting to Neo4j...")
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
        )
        
        # Test Neo4j connection
        with driver.session() as session:
            session.run("RETURN 1").single()
        
        return messages_collection, driver
    
    except Exception as e:
        logger.error(f"Error initializing connections: {e}")
        raise

def main():
    try:
        # 1. Initialize connections
        logger.info("Connecting to Neo4j and MongoDB...")
        messages_collection = connect_to_mongodb()
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
        )
        
        # 2. Run initial diagnostics
        logger.info("\nChecking initial state...")
        diagnose_conversations(driver)
        check_neo4j_state(driver)
        
        # 3. Process new messages from MongoDB to Neo4j
        logger.info("\nProcessing messages from MongoDB...")
        process_messages()
        
        # 4. Fix any missing session IDs
        logger.info("\nFixing missing session IDs...")
        fix_session_ids(driver, messages_collection)
        
        # 5. Run deduplication
        logger.info("\nRunning message deduplication...")
        while deduplicate_conversations(driver):
            logger.info("Processed batch of duplicates")
            
        # 6. Process existing messages without sentiment
        logger.info("\nProcessing messages without sentiment...")
        while process_existing_messages(driver):
            logger.info("Processed batch of messages")
            
        # 7. Analyze conversations
        logger.info("\nAnalyzing conversations...")
        while analyze_conversations(driver):
            logger.info("Processed batch of conversation analysis")
            
        # 8. Update quality metrics
        logger.info("\nUpdating conversation quality metrics...")
        while update_conversation_analysis(driver):
            logger.info("Updated batch with quality metrics")
            
        # 9. Run final diagnostics
        logger.info("\nRunning final diagnostics...")
        diagnose_conversations(driver)
        check_neo4j_state(driver)
        
    except Exception as e:
        logger.error(f"Error in processing pipeline: {e}")
        raise
    finally:
        if 'driver' in locals():
            driver.close()

if __name__ == "__main__":
    main()
