import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
from voyageai import Client  # Updated import
from neo4j import GraphDatabase
from datetime import datetime, timezone
import logging
from bson.objectid import ObjectId
from core.graphrag.src.conversation_processor import diagnose_conversations

# Update env path to be relative to project root
env_path = Path(__file__).parents[5] / '.env'
load_dotenv(dotenv_path=env_path)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def connect_to_mongodb():
    """Connect to MongoDB and return the collection"""
    print("\nConnecting to MongoDB...")
    mongo_uri = os.getenv('MONGO_URI')
    
    print(f"MongoDB URI: {mongo_uri}")
    
    try:
        client = MongoClient(mongo_uri)
        db = client['rin_db']
        collection = db['rin.messages']
        
        # Test the connection
        doc_count = collection.count_documents({})
        print(f"\nFound {doc_count} documents in rin.messages collection")
        
        return collection
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        raise e

def get_last_processed_time(driver):
    """Get the timestamp of the most recently processed message"""
    try:
        print("\nExecuting Neo4j timestamp query...")
        with driver.session() as session:
            # First check for messages in our target date range
            result = session.run("""
                MATCH (m:Message)
                WHERE m.timestamp >= datetime('2025-01-30T10:00:41.913000')  // Start from last processed
                AND m.timestamp <= datetime('2025-02-03T23:59:59')  // Process until Feb 3rd
                AND (m.voyage_embedding IS NULL  // Either no embedding
                    OR m.sentiment IS NULL      // Or no sentiment analysis
                    OR m.topics IS NULL)        // Or no topics
                RETURN count(m) as to_process,
                       min(m.timestamp) as earliest,
                       max(m.timestamp) as latest
            """)
            stats = result.single()
            print(f"\nFound {stats['to_process']} messages needing processing in Neo4j")
            
            return datetime(2025, 1, 30, 10, 0, 41, 913000, tzinfo=timezone.utc)
    except Exception as e:
        print(f"\nError in get_last_processed_time: {type(e).__name__} - {str(e)}")
        return datetime(2025, 1, 30, 10, 0, 41, 913000, tzinfo=timezone.utc)

def process_messages():
    try:
        print("\nInitializing connections...")
        messages_collection = connect_to_mongodb()
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
        )
        
        # Initialize counters
        processed = 0
        skipped = 0
        batch_size = 50
        
        # First check what's already in Neo4j
        with driver.session() as session:
            existing = session.run("""
            MATCH (m:Message)
            WHERE m.timestamp >= datetime('2025-01-30T10:00:41.913000')
            AND m.timestamp <= datetime('2025-02-03T23:59:59')
            RETURN count(m) as count, 
                   count(m.voyage_embedding) as with_embeddings,
                   count(m.session_id) as with_sessions
            """).single()
            
            logger.info(f"\nExisting messages in Neo4j: {existing['count']}")
            logger.info(f"Messages with embeddings: {existing['with_embeddings']}")
            logger.info(f"Messages with session IDs: {existing['with_sessions']}")
            
            if existing['count'] >= 4084:  # Total messages in range
                print("\nAll messages already processed. Skipping message processing.")
                return
            
        print("\nInitializing Voyage client...")
        voyage_api_key = os.getenv("VOYAGE_API_KEY")
        if not voyage_api_key:
            raise ValueError("Missing VOYAGE_API_KEY in environment variables")
            
        voyage_client = Client(api_key=voyage_api_key)
        print("Voyage client initialized successfully")
        
        # Define date range constants
        START_DATE = datetime(2025, 1, 30, 10, 0, 41, 913000, tzinfo=timezone.utc)
        END_DATE = datetime(2025, 2, 3, 23, 59, 59, tzinfo=timezone.utc)
        
        # Get total count for progress tracking
        total_new = messages_collection.count_documents({
            'timestamp': {
                '$gt': START_DATE,
                '$lte': END_DATE
            }
        })
        print(f"\nFound {total_new} messages in date range")
        
        with driver.session() as session:
            # Get current conversation groups
            result = session.run("""
            MATCH (m:Message)
            WITH m.timestamp as ts, count(*) as count
            WHERE duration.between(ts, ts + duration('PT1S')) > 1
            RETURN ts, count
            ORDER BY ts
            LIMIT 5
            """)
            logger.info("\nExisting conversation groups in Neo4j:")
            for record in result:
                logger.info(f"Timestamp: {record['ts']}, Messages: {record['count']}")
            
            # Continue with message processing
            for msg in messages_collection.find({
                'timestamp': {
                    '$gt': START_DATE,
                    '$lte': END_DATE
                }
            }):
                msg_id = str(msg['_id'])
                session_id = msg.get('session_id')
                
                logger.info(f"\nProcessing message {msg_id}")
                logger.info(f"Timestamp: {msg['timestamp']}")
                logger.info(f"Session ID: {session_id}")
                
                # Check if message exists in Neo4j
                exists = session.run("""
                MATCH (m:Message {id: $msg_id}) 
                RETURN count(m) > 0 as exists
                """, {'msg_id': msg_id}).single()['exists']
                
                logger.info(f"Message exists in Neo4j: {exists}")
                
                if exists:
                    skipped += 1
                    if skipped % 10 == 0:
                        logger.info(f"Skipped {skipped} existing messages")
                    continue
                
                try:
                    # Generate Voyage embedding for new message
                    content = msg.get('content', '')[:6000]
                    if content:
                        embedding = voyage_client.embed(content, model="voyage-3").embeddings[0]
                    else:
                        embedding = None

                    # Add new message with embedding
                    session.run("""
                    CREATE (m:Message {
                        id: $msg_id,
                        content: $content,
                        timestamp: datetime($timestamp),
                        role: $role,
                        session_id: $session_id,
                        voyage_embedding: $embedding,
                        processed_at: datetime()
                    })
                    """, {
                        'msg_id': msg_id,
                        'content': content,
                        'timestamp': msg['timestamp'].isoformat(),
                        'role': msg.get('role'),
                        'session_id': msg.get('session_id'),
                        'embedding': embedding
                    })
                    
                except Exception as e:
                    print(f"Error processing message {msg_id}: {str(e)}")
                
                if (processed + skipped) % batch_size == 0:
                    print(f"Progress: {processed}/{total_new} messages added to Neo4j")
                    print(f"Processed: {processed}, Skipped: {skipped}, Total: {processed + skipped}")
        
        print(f"\nFinal Summary:")
        print(f"New messages processed: {processed}")
        print(f"Messages skipped: {skipped}")
        print(f"Total messages seen: {processed + skipped}")
        
        # 3. Create conversations for new messages
        print("\nCreating conversations for new messages...")
        with driver.session() as session:
            # First, ensure all messages have session_ids
            result = session.run("""
            MATCH (m:Message)
            WHERE m.timestamp > datetime($start)
            AND m.timestamp <= datetime($end)
            AND m.session_id IS NOT NULL
            AND NOT (m)-[:IN_CONVERSATION]->(:Conversation)
            WITH m.session_id as sid, collect(m) as messages
            WHERE size(messages) > 0
            MERGE (c:Conversation {session_id: sid})
            SET c.analyzed = false,
                c.created_at = datetime()
            WITH c, messages
            UNWIND messages as msg
            MERGE (msg)-[:IN_CONVERSATION]->(c)
            RETURN count(distinct c) as new_conversations,
                   count(msg) as messages_connected
            """, {'start': START_DATE.isoformat(), 'end': END_DATE.isoformat()})
            stats = result.single()
            print(f"Created {stats['new_conversations']} new conversations")
            print(f"Connected {stats['messages_connected']} messages to conversations")

        # 4. Analyze new conversations
        print("\nAnalyzing new conversations...")
        with driver.session() as session:
            # Get unanalyzed conversations
            result = session.run("""
            MATCH (c:Conversation)
            WHERE c.analyzed = false
            MATCH (m:Message)-[:IN_CONVERSATION]->(c)
            WITH c, collect(m) as messages
            ORDER BY c.created_at DESC
            RETURN c.session_id as session_id,
                   [msg IN messages | {
                       content: msg.content,
                       role: msg.role,
                       timestamp: msg.timestamp
                   }] as messages
            LIMIT 100  // Process in batches
            """)
            
            conversations = list(result)
            print(f"\nFound {len(conversations)} conversations to analyze")
            
            analyzed = 0
            for conv in conversations:
                try:
                    # Format conversation for analysis
                    messages_text = "\n".join([
                        f"{m['role']}: {m['content']}" 
                        for m in sorted(conv['messages'], key=lambda x: x['timestamp'])
                    ])
                    
                    # Analyze conversation using graph_transformer
                    analysis = diagnose_conversations(messages_text)
                    
                    # Store analysis results
                    session.run("""
                    MATCH (c:Conversation {session_id: $session_id})
                    SET c.analyzed = true,
                        c.analyzed_at = datetime(),
                        c.sentiment = $sentiment,
                        c.topics = $topics,
                        c.engagement_level = $engagement,
                        c.relationship_dynamic = $dynamic
                    """, {
                        'session_id': conv['session_id'],
                        'sentiment': analysis.get('sentiment', 'neutral'),
                        'topics': analysis.get('topics', []),
                        'engagement': analysis.get('engagement_level', 'medium'),
                        'dynamic': analysis.get('relationship_dynamic', 'neutral')
                    })
                    
                    analyzed += 1
                    if analyzed % 10 == 0:  # Progress update every 10 conversations
                        print(f"Analyzed {analyzed}/{len(conversations)} conversations")
                        
                except Exception as e:
                    print(f"Error analyzing conversation {conv['session_id']}: {str(e)}")
                    continue
            
            print(f"\nCompleted analysis of {analyzed} conversations")

        # Add deduplication check before final analysis
        print("\nChecking for duplicate messages...")
        with driver.session() as session:
            result = session.run("""
            MATCH (m:Message)-[:IN_CONVERSATION]->(c:Conversation)
            WITH c, m.role as role, count(*) as count
            WHERE count > 1
            RETURN c.session_id as session_id, 
                   role,
                   count as message_count
            ORDER BY count DESC
            LIMIT 5
            """)
            
            for record in result:
                print(f"Session {record['session_id']}: {record['message_count']} {record['role']} messages")

    except Exception as e:
        print(f"Error during processing: {str(e)}")
        raise

def fix_session_ids(driver, messages_collection):
    """Fix missing session IDs by updating from MongoDB"""
    with driver.session() as session:
        result = session.run("""
        MATCH (m:Message)
        WHERE m.session_id IS NULL
        AND m.voyage_embedding IS NOT NULL
        AND m.timestamp >= datetime('2025-02-03T00:00:00')  // Updated date
        AND m.timestamp <= datetime('2025-02-03T23:59:59')  // Added end date
        RETURN 
            m.id as msg_id,
            m.timestamp as timestamp
        ORDER BY m.timestamp DESC
        """)
        missing_ids = [(record['msg_id'], record['timestamp']) for record in result]
        
        print(f"\nFound {len(missing_ids)} recent messages without session_ids")
        
        if missing_ids:
            print("\nTimestamp range:")
            if missing_ids:
                print(f"Latest: {missing_ids[0][1]}")
                print(f"Earliest: {missing_ids[-1][1]}")
            
            print("\nSample messages:")
            for msg_id, timestamp in missing_ids[:5]:
                print(f"ID: {msg_id}, Time: {timestamp}")
        
        # Batch process updates
        for msg_id, _ in missing_ids:
            try:
                # Get session_id from MongoDB
                mongo_msg = messages_collection.find_one({"_id": ObjectId(msg_id)})
                if mongo_msg and mongo_msg.get('session_id'):
                    session.run("""
                    MATCH (m:Message {id: $msg_id})
                    SET m.session_id = $session_id
                    """, {
                        'msg_id': msg_id,
                        'session_id': mongo_msg['session_id']
                    })
                    print(f"Updated session_id for message {msg_id}")
            except Exception as e:
                print(f"Error processing message {msg_id}: {str(e)}")
                continue

def check_neo4j_state(driver):
    """Check the current state of messages and conversations in Neo4j"""
    with driver.session() as session:
        result = session.run("""
        MATCH (m:Message)
        WHERE m.timestamp >= datetime('2025-01-30T10:00:41.913000')
        AND m.timestamp <= datetime('2025-02-03T23:59:59')
        WITH count(m) as total_messages
        MATCH (c:Conversation)
        RETURN 
            total_messages,
            count(c) as total_conversations,
            size([m IN collect(m) WHERE (m)-[:IN_CONVERSATION]->(:Conversation)]) as messages_in_conversations
        """)
        stats = result.single()
        print(f"""
Neo4j Database State:
Total Messages: {stats['total_messages']}
Total Conversations: {stats['total_conversations']}
Messages in Conversations: {stats['messages_in_conversations']}
        """)

if __name__ == "__main__":
    print("Starting message processing pipeline...")
    process_messages()
    print("Message processing completed!") 