import sys
import os
import logging
from pathlib import Path
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Setup paths
project_root = Path(__file__).parent.parent.parent.parent
backend_dir = project_root / 'backend'
python_services_dir = project_root / 'backend/python_services'

# Add project root to Python path
if str(python_services_dir) not in sys.path:
    sys.path.append(str(python_services_dir))

# Load environment variables
load_dotenv(backend_dir / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our modules
from core.agent.context_manager import RinContext

async def test_summarization():
    """Test the conversation summarization functionality"""
    try:
        # Verify required environment variables
        required_vars = ["MONGO_URI", "GROQ_API_KEY"]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            logger.error(f"Missing required environment variables: {', '.join(missing)}")
            return None

        # Initialize context manager
        logger.info("Starting test - initializing context manager...")
        mongo_uri = os.getenv("MONGO_URI")
        context = RinContext(mongo_uri)
        await context.initialize()
        logger.info("Context manager initialized successfully")
        
        # Create test session
        session_id = f"test_summary_{datetime.utcnow().isoformat()}"
        logger.info(f"Created test session with ID: {session_id}")
        
        # Create base conversation that establishes context
        test_conversation = [
            ("user", "Hey Rin! Let's have a deep discussion about crypto, tech, and the future of AI."),
            ("assistant", "Hi there! 💖 I'd love to dive deep into those topics! I'm particularly passionate about the intersection of crypto, AI, and how they're shaping our digital future. Where would you like to start? We could discuss blockchain technology, the latest in AI developments, or perhaps how these technologies complement each other! 🚀"),
        ]
        
        # Generate extensive technical discussions to reach token threshold
        technical_topics = [
            "Bitcoin's Lightning Network and Layer 2 scaling",
            "Ethereum's transition to Proof of Stake",
            "Zero-knowledge proofs and privacy",
            "Smart contract security and auditing",
            "DeFi protocols and yield farming",
            "NFT marketplaces and digital art",
            "Cross-chain bridges and interoperability",
            "AI in blockchain and crypto trading",
            "Tokenomics and game theory",
            "DAO governance models"
        ] * 4  # Repeat topics 4 times to generate more content

        # For each topic, generate even more detailed responses
        for i, topic in enumerate(technical_topics):
            variation = f"Part {(i // 10) + 1}: " # Add parts to make each discussion unique
            
            test_conversation.extend([
                ("user", f"Can you explain {variation}{topic} in extreme detail? I want to understand every technical aspect."),
                ("assistant", f"""Let me provide an in-depth analysis of {topic}! 🔍

1. Technical Foundation:
   - Core concepts and principles
     * Fundamental architecture
     * Key algorithms
     * Protocol design
     * Network topology
   - Historical development
     * Initial implementation
     * Major upgrades
     * Critical milestones
     * Community feedback
   - Technical components
     * Data structures
     * Consensus mechanisms
     * Network layers
     * Security protocols
   - Current state
     * Performance metrics
     * Adoption statistics
     * Technical challenges
     * Ongoing developments

2. Implementation Details:
   - Architecture patterns
     * System design
     * Component interaction
     * Data flow
     * State management
   - Protocol specifications
     * Message formats
     * Network rules
     * Validation logic
     * Error handling
   - Security considerations
     * Attack vectors
     * Defense mechanisms
     * Risk assessment
     * Mitigation strategies
   - Performance optimization
     * Caching systems
     * Load balancing
     * Resource management
     * Scaling solutions

3. Advanced Topics:
   - Cryptographic primitives
   - Zero-knowledge proofs
   - Multi-party computation
   - Threshold signatures
   - State channels
   - Layer 2 scaling
   - Cross-chain communication
   - Privacy preservation

Would you like me to elaborate on any of these aspects? I can provide even more technical details! 💫"""),
                ("user", f"That's fascinating! Can you dive deeper into the implementation challenges and solutions for {variation}{topic}?"),
                ("assistant", f"""Absolutely! Let's explore the complex implementation challenges and solutions for {topic}! 🛡️

Technical Implementation Challenges:

1. Scalability Issues:
   - Transaction throughput limitations
     * Block size constraints
     * Network congestion
     * Processing overhead
     * State growth
   - Proposed Solutions:
     * Sharding mechanisms
     * Layer 2 protocols
     * State channels
     * Rollup technologies

2. Security Considerations:
   - Attack Vectors:
     * Front-running
     * MEV exploitation
     * Oracle manipulation
     * Reentrancy risks
   - Protection Measures:
     * Access controls
     * Rate limiting
     * Secure randomness
     * Time-locks

3. Performance Optimization:
   - Bottlenecks:
     * Database operations
     * Network latency
     * Computation overhead
     * Memory constraints
   - Solutions:
     * Caching layers
     * Index optimization
     * Batch processing
     * Parallel execution

4. Integration Challenges:
   - Cross-chain compatibility
   - API standardization
   - Data consistency
   - Error recovery

5. Future Considerations:
   - Upgrade paths
   - Backward compatibility
   - Resource scaling
   - Community governance

Would you like me to elaborate on any specific challenge or solution? 🔧"""),
                ("user", f"How does this compare to other implementations in the space? Especially regarding {variation}{topic}?"),
                ("assistant", f"""Let me break down the comparative analysis of {topic} with other solutions! 📊

Detailed Comparison:

1. Architecture Comparison:
   - Infrastructure:
     * Network topology
     * Node requirements
     * Consensus mechanisms
     * Storage solutions
   - Performance:
     * Transaction speed
     * Finality time
     * Resource usage
     * Scalability limits

2. Feature Analysis:
   - Core Capabilities:
     * Smart contract support
     * Privacy features
     * Cross-chain compatibility
     * Governance mechanisms
   - Advanced Features:
     * Custom primitives
     * Extension support
     * Plugin architecture
     * API flexibility

3. Security Models:
   - Trust Assumptions:
     * Validator requirements
     * Economic security
     * Cryptographic proofs
     * Attack resistance
   - Risk Profiles:
     * Vulnerability surface
     * Attack vectors
     * Mitigation strategies
     * Recovery procedures

4. Market Analysis:
   - Adoption Metrics:
     * User base growth
     * Transaction volume
     * Developer activity
     * Market integration
   - Ecosystem:
     * Tool availability
     * Documentation
     * Community support
     * Corporate backing

Would you like to explore any specific aspect of these comparisons in more detail? 🔍""")
            ])

        # Track metrics
        summarization_count = 0
        total_tokens = 0
        
        # Store messages and check tokens
        for role, content in test_conversation:
            # Store message
            await context.db.add_message(session_id, role, content)
            
            # Get updated token count
            total_tokens = await context._count_tokens(session_id)
            logger.info(f"Current token count: {total_tokens}")
            
            if total_tokens > context.TOKEN_THRESHOLD:
                logger.info(f"Token threshold ({context.TOKEN_THRESHOLD}) exceeded!")
                
                # Do synchronous summarization (like in agent.py)
                success = await context.summarize_conversation_context(session_id)
                
                if success:
                    summarization_count += 1
                    new_total = await context._count_tokens(session_id)
                    reduction = ((total_tokens - new_total) / total_tokens) * 100
                    
                    # Get the latest configuration to check summary
                    config = await context.db.get_context_configuration(session_id)
                    
                    logger.info(f"✅ Summarization #{summarization_count} complete:")
                    logger.info(f"  - Original tokens: {total_tokens}")
                    logger.info(f"  - New tokens: {new_total}")
                    logger.info(f"  - Reduction: {reduction:.1f}%")
                    
                    if config and config.get("latest_summary"):
                        # Verify summary quality
                        summary = config["latest_summary"]["content"]
                        logger.info("\n📝 Summary Preview:")
                        logger.info("-" * 50)
                        logger.info(summary[:500] + "..." if len(summary) > 500 else summary)
                        logger.info("-" * 50)
                        
                        # Check retained messages
                        retained_msgs = await context.db.get_messages_by_ids(
                            session_id, 
                            config.get("active_message_ids", [])
                        )
                        logger.info(f"\n📌 Retained {len(retained_msgs)} recent messages")
                        
                        # Token analysis
                        logger.info("\n📊 Token Analysis:")
                        logger.info(f"  - Summary tokens: {len(context.enc.encode(summary))}")
                        logger.info(f"  - Retained message tokens: {sum(len(context.enc.encode(msg['content'])) for msg in retained_msgs)}")
                        logger.info(f"  - Total tokens after summarization: {new_total}")
                else:
                    logger.warning("Summarization failed or was skipped")

        logger.info("\n🎯 Test Summary:")
        logger.info(f"- Messages processed: {len(test_conversation)}")
        logger.info(f"- Summarizations triggered: {summarization_count}")
        logger.info(f"- Final token count: {await context._count_tokens(session_id)}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(test_summarization())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)