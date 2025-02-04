import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
import logging
from langchain_openai import ChatOpenAI
from langchain.chains import GraphCypherQAChain
from langchain_community.graphs import Neo4jGraph
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Neo4jVector
from langchain.schema import Document

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from project root
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

def setup_schema():
    """Set up Neo4j schema with constraints and indexes"""
    try:
        # Get Neo4j credentials
        neo4j_uri = os.getenv('NEO4J_URI')
        neo4j_username = os.getenv('NEO4J_USERNAME')
        neo4j_password = os.getenv('NEO4J_PASSWORD')
        
        logger.info("\nChecking Neo4j credentials:")
        logger.info(f"URI: {neo4j_uri}")
        logger.info(f"Username: {neo4j_username}")
        logger.info(f"Password: {'*' * len(neo4j_password) if neo4j_password else 'Not found'}")
        
        if not all([neo4j_uri, neo4j_username, neo4j_password]):
            raise ValueError("Missing Neo4j credentials in environment variables")
        
        logger.info("\nAttempting to connect to Neo4j...")
        
        driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_username, neo4j_password)
        )
        
        logger.info("Successfully connected to Neo4j!")
        
        with driver.session() as session:
            # Create constraints and indexes
            constraints = [
                "CREATE CONSTRAINT conversation_id IF NOT EXISTS FOR (c:Conversation) REQUIRE c.session_id IS UNIQUE",
                "CREATE CONSTRAINT message_id IF NOT EXISTS FOR (m:Message) REQUIRE m.id IS UNIQUE",
                "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
                "CREATE CONSTRAINT topic_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE"
            ]
            
            indexes = [
                "CREATE INDEX message_timestamp IF NOT EXISTS FOR (m:Message) ON (m.timestamp)",
                "CREATE INDEX message_content IF NOT EXISTS FOR (m:Message) ON (m.content)",
                "CREATE VECTOR INDEX messageEmbeddings IF NOT EXISTS FOR (m:Message) ON m.voyage_embedding"
            ]
            
            try:
                # Apply constraints
                for constraint in constraints:
                    session.run(constraint)
                logger.info("\nConstraints created successfully!")
                
                # Apply indexes
                for index in indexes:
                    session.run(index)
                logger.info("Indexes created successfully!")
                
            except Exception as e:
                logger.error(f"\nError setting up schema: {e}")
                raise e
            
    except Exception as e:
        logger.error(f"Error in setup_schema: {e}")
        raise
    finally:
        if 'driver' in locals():
            driver.close()

def initialize_graph():
    # Initialize Neo4j Graph after environment variables are loaded
    graph = Neo4jGraph(
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD")
    )
    return graph

if __name__ == "__main__":
    setup_schema()
    
    # Then initialize the graph
    graph = initialize_graph()
    logger.info("\nNeo4j graph initialized successfully!") 