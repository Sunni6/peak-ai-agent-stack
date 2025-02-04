import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.graphs import Neo4jGraph
from langchain.chains import GraphCypherQAChain
from langchain_openai import ChatOpenAI, OpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import json
from neo4j import GraphDatabase
from pymongo import MongoClient
import logging
from datetime import datetime
import time
import re
from voyageai import Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path('/Users/dleer.ious/development/rin_kg/chat-graphrag/.env')
load_dotenv(dotenv_path=env_path)

# Verify Neo4j connection details
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_username = os.getenv("NEO4J_USERNAME")
neo4j_password = os.getenv("NEO4J_PASSWORD")

if not all([neo4j_uri, neo4j_username, neo4j_password]):
    raise ValueError("Missing required Neo4j environment variables")

# Initialize OpenAI
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("Missing OpenAI API key")

# Define the structure we want the LLM to extract
class MessageEntity(BaseModel):
    topics: List[str] = Field(description="Main topics discussed in the message")
    entities: List[str] = Field(description="Named entities mentioned")
    sentiment: str = Field(description="Overall sentiment of the message")
    relationships: List[dict] = Field(description="Relationships between entities")
    quality_metrics: Optional[Dict[str, float]] = Field(description="Interaction quality scores")

# Create a more specific prompt for our chat messages
kg_prompt = ChatPromptTemplate.from_template("""
You are an AI that analyzes chat messages and extracts structured information for a knowledge graph.
The messages are 1-on-1 conversations between Rin (an AI crypto vtuber) and her fans from the catgirlrin.com website.

For the following chat message, please identify:
1. Main topics discussed (e.g., crypto, art, relationships, conspiracies)
2. Named entities (people, tokens, technologies, companies, locations)
3. Message sentiment (including flirty, mysterious, playful tones)
4. Relationships between entities

Message Content: {message_content}

Extract the information in the following format:
{format_instructions}

Remember:
- Topics should capture both explicit content and subtle undertones
- Pay special attention to crypto/token discussions and community dynamics
- Note any conspiracy theories or mysterious elements
- Track engagement patterns and relationship building
- Identify any artistic or creative elements mentioned

Provide your response in valid JSON format.
""")

def create_graph_transformer(model="gpt-4o"):
    """Initialize the graph transformation components"""
    # Initialize the LLM
    llm = ChatOpenAI(model=model, temperature=0)
    
    # Setup the output parser
    parser = PydanticOutputParser(pydantic_object=MessageEntity)
    
    # Combine prompt with parser
    prompt_with_parser = kg_prompt.partial(
        format_instructions=parser.get_format_instructions()
    )
    
    return llm, prompt_with_parser, parser

def process_message_content(message_content: str, llm, prompt, parser):
    """Process a single message and extract graph elements"""
    # Generate the full prompt
    formatted_prompt = prompt.format_messages(
        message_content=message_content
    )
    
    # Get LLM response
    response = llm.invoke(formatted_prompt)
    
    # Parse the response
    try:
        extracted_data = parser.parse(response.content)
        return extracted_data
    except Exception as e:
        print(f"Error parsing LLM response: {e}")
        return None

def create_graph_elements(driver, message_id: str, extracted_data: MessageEntity):
    """Create nodes and relationships in Neo4j"""
    with driver.session() as session:
        # Create topics
        for topic in extracted_data.topics:
            session.run("""
                MATCH (m:Message {id: $message_id})
                MERGE (t:Topic {name: $topic})
                CREATE (m)-[:DISCUSSES]->(t)
            """, {"message_id": message_id, "topic": topic})
        
        # Create entities
        for entity in extracted_data.entities:
            session.run("""
                MATCH (m:Message {id: $message_id})
                MERGE (e:Entity {name: $entity})
                CREATE (m)-[:MENTIONS]->(e)
            """, {"message_id": message_id, "entity": entity})
        
        # Create relationships between entities
        for rel in extracted_data.relationships:
            session.run("""
                MATCH (s:Entity {name: $source})
                MATCH (t:Entity {name: $target})
                CREATE (s)-[:RELATES_TO {type: $rel_type}]->(t)
            """, {
                "source": rel["source"],
                "target": rel["target"],
                "rel_type": rel["relationship_type"]
            })
        
        # Update message with sentiment
        session.run("""
            MATCH (m:Message {id: $message_id})
            SET m.sentiment = $sentiment
        """, {"message_id": message_id, "sentiment": extracted_data.sentiment})

def initialize_schema(driver):
    with driver.session() as session:
        # Create constraints and properties
        session.run("""
            CREATE CONSTRAINT message_id IF NOT EXISTS
            FOR (m:Message) REQUIRE m.id IS UNIQUE
        """)
        
        # Ensure sentiment property exists with default
        session.run("""
            MATCH (m:Message)
            WHERE m.sentiment IS NULL
            SET m.sentiment = 'undefined'
        """)

def process_existing_messages(driver, batch_size=100):
    with driver.session() as session:
        # Find messages without sentiment analysis
        result = session.run("""
            MATCH (m:Message)
            WHERE m.sentiment = 'undefined'
            RETURN m.id as id, m.content as content
            LIMIT $batch_size
        """, batch_size=batch_size)
        
        messages = list(result)
        if not messages:
            logger.info("No new messages to process")
            return False
        
        for record in messages:
            if not record.get('content'):
                continue
                
            sentiment = analyze_sentiment(record['content'])
            
            session.run("""
                MATCH (m:Message {id: $message_id})
                SET m.sentiment = $sentiment
            """, message_id=record['id'], sentiment=sentiment)
            
            logger.info(f"Processed message: {record['content'][:50]}... with sentiment: {sentiment}")
        
        return True

def connect_to_mongodb():
    client = MongoClient(os.getenv('MONGO_URI'))
    db = client['rin_db']
    return db['rin.messages']

def connect_to_neo4j():
    return GraphDatabase.driver(
        os.getenv('NEO4J_URI'),
        auth=(os.getenv('NEO4J_USERNAME'), os.getenv('NEO4J_PASSWORD'))
    )

def analyze_sentiment(text):
    try:
        if not text or len(text.strip()) == 0:
            return 'neutral'
            
        llm = OpenAI()
        prompt = f"""Analyze the sentiment of this message and respond with exactly one word - 
        'positive', 'negative', or 'neutral': "{text}" """
        response = llm.invoke(prompt).strip().lower()
        
        # Ensure valid sentiment value
        valid_sentiments = ['positive', 'negative', 'neutral']
        return response if response in valid_sentiments else 'neutral'
        
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        return 'neutral'

def create_message_node(tx, message):
    query = """
    MERGE (c:Conversation {session_id: $session_id})
    MERGE (u:User {role: $role})
    CREATE (m:Message {
        message_id: $message_id,
        content: $content,
        timestamp: datetime($timestamp),
        role: $role
    })
    CREATE (u)-[:SENT]->(m)
    CREATE (m)-[:IN_CONVERSATION]->(c)
    WITH m, c
    MATCH (prev:Message)-[:IN_CONVERSATION]->(c)
    WHERE prev.timestamp < m.timestamp
    WITH m, prev
    ORDER BY prev.timestamp DESC
    LIMIT 1
    CREATE (prev)-[:NEXT]->(m)
    """
    
    tx.run(query, {
        'message_id': str(message['_id']),
        'session_id': message['session_id'],
        'content': message['content'],
        'timestamp': message['timestamp'].isoformat(),
        'role': message['role']
    })

def process_messages(messages_collection, neo4j_driver):
    """Process messages from MongoDB to Neo4j"""
    with neo4j_driver.session() as session:
        # First find messages with embeddings but no conversation links
        result = session.run("""
        MATCH (m:Message)
        WHERE m.voyage_embedding IS NOT NULL  // Has embedding
        AND NOT (m)-[:IN_CONVERSATION]->(:Conversation)  // No conversation link
        AND m.session_id IS NOT NULL  // Has session_id
        WITH m.session_id as sid, collect(m) as messages
        WHERE size(messages) > 0
        MERGE (c:Conversation {session_id: sid})
        WITH c, messages
        UNWIND messages as msg
        MERGE (msg)-[:IN_CONVERSATION]->(c)
        RETURN count(distinct c) as new_conversations
        """)
        new_convs = result.single()['new_conversations']
        logger.info(f"Created {new_convs} new conversations from orphaned messages")

def cleanup_incomplete_analysis(driver):
    """Reset incomplete semantic analysis state"""
    with driver.session() as session:
        # Get counts before cleanup
        before_state = session.run("""
            MATCH (m:Message)
            RETURN 
                count(m) as total,
                count(CASE WHEN m.sentiment = 'undefined' THEN 1 END) as undefined,
                count(CASE WHEN m.sentiment IS NOT NULL AND m.sentiment <> 'undefined' THEN 1 END) as processed
        """).single()
        
        logger.info(f"""
        Before Cleanup:
        Total Messages: {before_state['total']}
        Undefined Sentiment: {before_state['undefined']}
        Processed: {before_state['processed']}
        """)
        
        # Reset incomplete analysis
        session.run("""
        MATCH (m:Message)
        WHERE m.sentiment = 'undefined'
        REMOVE m.sentiment
        """)
        
        # Verify cleanup
        after_state = session.run("""
            MATCH (m:Message)
            RETURN 
                count(m) as total,
                count(CASE WHEN m.sentiment IS NULL THEN 1 END) as unprocessed,
                count(CASE WHEN m.sentiment IS NOT NULL THEN 1 END) as processed
        """).single()
        
        logger.info(f"""
        After Cleanup:
        Total Messages: {after_state['total']}
        Unprocessed: {after_state['unprocessed']}
        Processed: {after_state['processed']}
        """)

def analyze_conversations(driver, specific_conversations=None):
    """Analyze unanalyzed conversations in batches"""
    try:
        with driver.session() as session:
            if specific_conversations:
                # Use provided conversations for reanalysis
                conversations = specific_conversations
                logger.info(f"Reanalyzing {len(conversations)} specific conversations")
            else:
                # Get unanalyzed conversations
                result = session.run("""
                MATCH (c:Conversation)
                WHERE c.analyzed IS NULL OR c.analyzed = false
                MATCH (m:Message)-[:IN_CONVERSATION]->(c)
                WITH c, collect(m) as messages
                ORDER BY c.created_at DESC
                RETURN c.session_id as session_id,
                       [msg IN messages | {
                           content: msg.content,
                           role: msg.role,
                           timestamp: msg.timestamp
                       }] as messages
                LIMIT 50
                """)
                conversations = list(result)
                logger.info(f"\nFound {len(conversations)} conversations to analyze")
            
            if not conversations:
                return False
                
            analyzed = 0
            for conv in conversations:
                try:
                    # Format conversation for analysis
                    messages_text = "\n".join([
                        f"{m['role']}: {m['content']}" 
                        for m in sorted(conv['messages'], key=lambda x: x['timestamp'])
                    ])
                    
                    # Get analysis
                    analysis = process_conversation(messages_text)
                    
                    # Store analysis results
                    session.run("""
                    MATCH (c:Conversation {session_id: $session_id})
                    SET c.analyzed = true,
                        c.analyzed_at = datetime(),
                        c.sentiment = $sentiment,
                        c.topics = $topics,
                        c.engagement_level = $engagement,
                        c.relationship_dynamic = $dynamic,
                        c.needs_reanalysis = false  // Clear reanalysis flag
                    """, {
                        'session_id': conv['session_id'],
                        'sentiment': analysis.get('sentiment', 'neutral'),
                        'topics': analysis.get('topics', []),
                        'engagement': analysis.get('engagement_level', 'medium'),
                        'dynamic': analysis.get('relationship_dynamic', 'neutral')
                    })
                    
                    analyzed += 1
                    if analyzed % 10 == 0:
                        logger.info(f"Analyzed {analyzed}/{len(conversations)} conversations")
                        
                except Exception as e:
                    logger.error(f"Error analyzing conversation {conv['session_id']}: {str(e)}")
                    continue
            
            logger.info(f"\nCompleted analysis of {analyzed} conversations")
            return True if not specific_conversations else False  # Continue only for regular analysis
            
    except Exception as e:
        logger.error(f"Error in analyze_conversations: {str(e)}")
        return False

def get_conversation_state(session):
    """Get accurate conversation-level state"""
    state = session.run("""
    // First get conversation stats
    MATCH (c:Conversation)
    OPTIONAL MATCH (m:Message)-[:IN_CONVERSATION]->(c)
    WITH c, collect(m) as messages
    RETURN {
        total_conversations: count(c),
        conversations_with_messages: count(CASE WHEN size(messages) > 0 THEN 1 END),
        avg_messages_per_conversation: avg(size(messages)),
        analyzed_conversations: count(CASE WHEN c.analyzed = true THEN 1 END)
    } as stats
    """).single()['stats']
    
    logger.info(f"""
    Conversation Analysis State:
    Total Conversations: {state['total_conversations']}
    With Messages: {state['conversations_with_messages']}
    Avg Messages/Conversation: {state['avg_messages_per_conversation']}
    Analyzed: {state['analyzed_conversations']}
    """)
    
    return state

def process_conversation(messages_text: str) -> dict:
    """Process a complete conversation and extract insights"""
    try:
        llm = ChatOpenAI(model="gpt-4o")
        
        prompt = ChatPromptTemplate.from_template("""You are analyzing conversations between Rin (an AI crypto vtuber) and users.
        For this conversation, provide ONLY a raw JSON object (no markdown, no backticks) with these exact fields:
        - sentiment: exactly one of ["positive", "negative", "neutral"]
        - topics: array of main topics discussed
        - engagement_level: exactly one of ["high", "medium", "low"]
        - relationship_dynamic: exactly one of ["friendly", "professional", "flirty"]
        
        Conversation:
        {messages}
        
        Return ONLY the raw JSON object. No markdown formatting, no backticks, no additional text.""")
        
        messages = prompt.format_messages(messages=messages_text)
        response = llm.invoke(messages)
        
        try:
            # Clean the response - remove markdown formatting
            clean_response = response.content.strip()
            if clean_response.startswith('```'):
                # Remove markdown code blocks
                clean_response = clean_response.replace('```json\n', '').replace('\n```', '')
            
            analysis = json.loads(clean_response)
            
            # Validate required fields
            required_fields = ['sentiment', 'topics', 'engagement_level', 'relationship_dynamic']
            if not all(field in analysis for field in required_fields):
                raise ValueError("Missing required fields in analysis")
                
            # Validate sentiment values
            if analysis['sentiment'] not in ['positive', 'negative', 'neutral']:
                analysis['sentiment'] = 'neutral'
                
            # Ensure topics is a list
            if not isinstance(analysis['topics'], list):
                analysis['topics'] = []
                
            logger.info(f"Successfully analyzed conversation with result: {analysis}")
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error: {e}\nResponse was: {response.content}")
            return {
                "sentiment": "neutral",
                "topics": [],
                "engagement_level": "low",
                "relationship_dynamic": "neutral"
            }
            
    except Exception as e:
        logger.error(f"Error in process_conversation: {str(e)}")
        return {
            "sentiment": "neutral",
            "topics": [],
            "engagement_level": "low",
            "relationship_dynamic": "neutral"
        }

class ConversationQuality(BaseModel):
    goal_completion: float = Field(description="How well user achieved their goals", ge=0.0, le=1.0)
    emotional_connection: float = Field(description="Level of emotional bonding", ge=0.0, le=1.0)
    topic_depth: float = Field(description="Depth of topic exploration", ge=0.0, le=1.0)
    user_satisfaction: float = Field(description="Signs of user satisfaction", ge=0.0, le=1.0)
    natural_conclusion: float = Field(description="How naturally conversation ended", ge=0.0, le=1.0)

def update_conversation_analysis(driver, batch_size=10):
    """Update existing analyzed conversations with quality metrics"""
    try:
        parser = PydanticOutputParser(pydantic_object=ConversationQuality)
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI analyzing conversation quality. Output only valid JSON matching the specified format."),
            ("human", """Analyze this conversation and rate each metric from 0.0 to 1.0:

Previous analysis:
Sentiment: {existing_sentiment}
Engagement: {existing_engagement}

Conversation:
{messages}

{format_instructions}""")
        ])

        with driver.session() as session:
            # Simplified query to only check for unprocessed conversations
            result = session.run("""
            MATCH (c:Conversation)
            WHERE 
                c.analyzed = true AND
                c.quality_goal_completion IS NULL  // Only check for main metric
            WITH c
            MATCH (m:Message)-[:IN_CONVERSATION]->(c)
            WITH c, collect(m) as messages
            RETURN 
                c.session_id as session_id,
                messages,
                c.sentiment as existing_sentiment,
                c.engagement_level as existing_engagement
            LIMIT $batch_size
            """, batch_size=batch_size)
            
            conversations = list(result)
            if not conversations:
                logger.info("No new conversations to analyze")
                return False

            logger.info(f"Processing batch of {len(conversations)} new conversations")
            processed = 0

            for idx, record in enumerate(conversations, 1):
                try:
                    messages_text = "\n".join([
                        f"{m['role']}: {m['content']}" 
                        for m in record['messages']
                    ])[:4000]  # Truncate to avoid token limits

                    _input = prompt.format_prompt(
                        messages=messages_text,
                        existing_sentiment=record['existing_sentiment'] or 'neutral',
                        existing_engagement=record['existing_engagement'] or 'medium',
                        format_instructions=parser.get_format_instructions()
                    )
                    
                    response = llm.invoke(_input.to_messages())
                    metrics = parser.parse(response.content)

                    # Update Neo4j with metrics and mark as processed
                    session.run("""
                    MATCH (c:Conversation {session_id: $session_id})
                    SET 
                        c.quality_goal_completion = $goal_completion,
                        c.quality_emotional_connection = $emotional_connection,
                        c.quality_topic_depth = $topic_depth,
                        c.quality_user_satisfaction = $user_satisfaction,
                        c.quality_natural_conclusion = $natural_conclusion,
                        c.quality_analyzed_at = datetime(),
                        c.quality_metrics_version = 1  // Add version tracking
                    """, {
                        'session_id': record['session_id'],
                        'goal_completion': float(metrics.goal_completion),
                        'emotional_connection': float(metrics.emotional_connection),
                        'topic_depth': float(metrics.topic_depth),
                        'user_satisfaction': float(metrics.user_satisfaction),
                        'natural_conclusion': float(metrics.natural_conclusion)
                    })

                    processed += 1
                    logger.info(f"Progress: {idx}/{len(conversations)} - Successfully processed: {record['session_id']}")

                except Exception as e:
                    logger.error(f"Error processing conversation {record['session_id']}: {str(e)}")
                    # Mark failed without using quality_analysis_failed property
                    session.run("""
                    MATCH (c:Conversation {session_id: $session_id})
                    SET 
                        c.quality_goal_completion = -1,  // Use sentinel value for failed analysis
                        c.quality_error = $error
                    """, {
                        'session_id': record['session_id'],
                        'error': str(e)
                    })
                    continue

            logger.info(f"Batch complete. Successfully processed: {processed}/{len(conversations)}")
            return processed > 0

    except Exception as e:
        logger.error(f"Fatal error in update_conversation_analysis: {str(e)}")
        raise

def get_unprocessed_state(driver):
    """Check for unprocessed messages and conversations"""
    with driver.session() as session:
        return {
            'unanalyzed_conversations': session.run("""
                // Find conversations without analysis
                MATCH (c:Conversation)
                WHERE c.analyzed IS NULL 
                   OR c.analyzed = false
                RETURN count(c) as count
            """).single()['count'],
            
            'pending_quality_metrics': session.run("""
                // Find analyzed conversations without quality metrics
                MATCH (c:Conversation)
                WHERE c.analyzed = true 
                AND c.quality_metrics_version IS NULL
                RETURN count(c) as count
            """).single()['count']
        }

def diagnose_conversations(driver):
    """Diagnose conversation state and distribution"""
    with driver.session() as session:
        # First get basic conversation stats
        result = session.run("""
        MATCH (c:Conversation)
        OPTIONAL MATCH (m:Message)-[:IN_CONVERSATION]->(c)
        WITH c, collect(m) as messages
        UNWIND messages as msg
        WITH c, messages, msg
        RETURN 
            c.session_id as session_id,
            size(messages) as message_count,
            min(msg.timestamp) as first_message,
            max(msg.timestamp) as last_message,
            c.analyzed as analyzed,
            c.quality_goal_completion as quality
        ORDER BY first_message DESC
        """)
        
        conversations = list(result)
        logger.info(f"\nFound {len(conversations)} total conversations")
        
        if conversations:
            logger.info("\nConversation Distribution:")
            logger.info("-" * 120)
            logger.info(f"{'Session ID':<36} | {'Messages':<8} | {'Length (mins)':<12} | {'Start Time':<20} | {'End Time':<20} | {'Analyzed':<8}")
            logger.info("-" * 120)
            
            for conv in conversations[:10]:  # Show first 10 for sample
                start_time = conv['first_message'].iso_format()[:19] if conv['first_message'] else "N/A"
                end_time = conv['last_message'].iso_format()[:19] if conv['last_message'] else "N/A"
                length_mins = 0
                if conv['first_message'] and conv['last_message']:
                    length_mins = int((conv['last_message'] - conv['first_message']).seconds / 60)
                
                logger.info(
                    f"{conv['session_id']:<36} | "
                    f"{conv['message_count']:<8} | "
                    f"{length_mins:<12} | "
                    f"{start_time:<20} | "
                    f"{end_time:<20} | "
                    f"{str(conv['analyzed']):<8}"
                )
            
            # Get orphaned messages with timestamps
            orphans = session.run("""
            MATCH (m:Message)
            WHERE m.session_id IS NOT NULL
            AND NOT (m)-[:IN_CONVERSATION]->(:Conversation)
            AND m.timestamp <= datetime('2025-02-03T23:59:59')  // Added date filter
            RETURN 
                count(m) as orphan_count,
                min(m.timestamp) as earliest_orphan,
                max(m.timestamp) as latest_orphan,
                collect(DISTINCT m.session_id)[..5] as sample_sessions
            """).single()
            
            logger.info(f"\nOrphan Messages: {orphans['orphan_count']}")
            if orphans['orphan_count'] > 0:
                logger.info(f"Orphan Time Range: {orphans['earliest_orphan']} to {orphans['latest_orphan']}")
                logger.info(f"Sample Session IDs: {orphans['sample_sessions']}")
            
            # Get message distribution stats
            stats = session.run("""
            MATCH (m:Message)-[:IN_CONVERSATION]->(c:Conversation)
            WITH c, count(m) as msg_count
            RETURN 
                count(c) as total_conversations,
                avg(msg_count) as avg_messages,
                min(msg_count) as min_messages,
                max(msg_count) as max_messages,
                count(CASE WHEN msg_count = 1 THEN 1 END) as single_message_convs
            """).single()
            
            logger.info("\nMessage Distribution:")
            logger.info(f"Total Conversations: {stats['total_conversations']}")
            logger.info(f"Average Messages/Conversation: {stats['avg_messages']:.1f}")
            logger.info(f"Min Messages: {stats['min_messages']}")
            logger.info(f"Max Messages: {stats['max_messages']}")
            logger.info(f"Single Message Conversations: {stats['single_message_convs']}")

def deduplicate_conversations(driver):
    """Remove duplicate messages within conversations and orphaned messages"""
    logger.info("\nStarting message deduplication...")
    
    with driver.session() as session:
        # 1. First check for duplicates including orphaned messages
        result = session.run("""
        MATCH (m1:Message)
        MATCH (m2:Message)
        WHERE id(m1) < id(m2)  // Avoid counting pairs twice
        AND m1.role = m2.role  // Same role (user/assistant)
        AND m1.session_id = m2.session_id  // Same conversation
        WITH m1, m2,
             CASE 
                WHEN m1.content = m2.content AND m1.timestamp = m2.timestamp THEN 'exact'
                WHEN m1.content = m2.content AND duration.between(m1.timestamp, m2.timestamp).seconds < 2 THEN 'near'
             END as duplicate_type
        WHERE duplicate_type IS NOT NULL
        RETURN 
            duplicate_type,
            count(*) as count,
            collect(DISTINCT m2.id)[..5] as sample_ids
        """)
        
        for record in result:
            logger.info(f"Found {record['count']} {record['duplicate_type']} duplicates")
            if record['sample_ids']:
                logger.info(f"Sample message IDs: {record['sample_ids']}")

        # 2. Remove exact duplicates
        result = session.run("""
        MATCH (m1:Message)
        MATCH (m2:Message)
        WHERE id(m1) < id(m2)
        AND m1.role = m2.role
        AND m1.session_id = m2.session_id
        AND m1.content = m2.content 
        AND m1.timestamp = m2.timestamp
        WITH m2
        DETACH DELETE m2
        RETURN count(*) as exact_duplicates_removed
        """)
        
        exact_dupes = result.single()['exact_duplicates_removed']
        logger.info(f"Removed {exact_dupes} exact duplicate messages")
        
        # 3. Remove near-duplicates
        result = session.run("""
        MATCH (m1:Message)
        MATCH (m2:Message)
        WHERE id(m1) < id(m2)
        AND m1.role = m2.role
        AND m1.session_id = m2.session_id
        AND m1.content = m2.content
        AND duration.between(m1.timestamp, m2.timestamp).seconds < 2
        WITH m2
        DETACH DELETE m2
        RETURN count(*) as near_duplicates_removed
        """)
        
        near_dupes = result.single()['near_duplicates_removed']
        logger.info(f"Removed {near_dupes} near-duplicate messages")
        
        return exact_dupes + near_dupes > 0

def main():
    try:
        driver = connect_to_neo4j()
        
        # Add diagnostic check
        logger.info("\nRunning conversation diagnostics...")
        diagnose_conversations(driver)
        
        # Check unprocessed state
        unprocessed = get_unprocessed_state(driver)
        logger.info(f"Found {unprocessed['unanalyzed_conversations']} unanalyzed conversations")
        logger.info(f"Found {unprocessed['pending_quality_metrics']} conversations needing quality metrics")
        
        # Skip conversation creation, only analyze existing ones
        logger.info("Starting conversation-level analysis...")
        while analyze_conversations(driver):
            logger.info("Processed batch of conversations")
            
        logger.info("Starting quality metrics update...")
        while update_conversation_analysis(driver):
            logger.info("Updated batch with quality metrics")

    except Exception as e:
        logger.error(f"Error in main process: {e}")
        raise
    finally:
        if 'driver' in locals():
            driver.close()

if __name__ == "__main__":
    main() 