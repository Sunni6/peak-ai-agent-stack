"""
Copyright (c) 2025 dleerdefi & Aggregated AI
Licensed under the MIT License. See LICENSE in the project root for license information.
"""

import asyncio
import platform

if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import sys
import os
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime
import json

# Configure logging
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(project_root))

# Add GraphRAG environment site-packages to path
graphrag_site_packages = project_root.parent / 'backend' / 'graphrag-env' / 'lib' / 'python3.10' / 'site-packages'
if graphrag_site_packages.exists():
    sys.path.insert(0, str(graphrag_site_packages))
    logger.info(f"Added GraphRAG site-packages to path: {graphrag_site_packages}")

# Now import our modules
from core.llm.llm_service import LLMService, ModelType
from core.agent.context_manager import RinContext
from core.agent.prompts import SYSTEM_PROMPT
from core.graphrag.engine import RinResponseEnricher
from core.tools.orchestrator import Orchestrator

class RinAgent:
    def __init__(self, mongo_uri: str):
        """Initialize Rin agent with required services."""
        self.llm_service = LLMService()
        self.context_manager = RinContext(mongo_uri)
        self.mongo_uri = mongo_uri
        self.sessions = {}
        
        # Load environment variables
        self.neo4j_uri = os.getenv("NEO4J_URI")
        self.neo4j_username = os.getenv("NEO4J_USERNAME")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD")
        
        if not all([self.neo4j_uri, self.neo4j_username, self.neo4j_password]):
            logger.warning("Neo4j credentials not fully configured. GraphRAG will be disabled.")
        
        # Initialize response enricher with Neo4j config
        self.response_enricher = RinResponseEnricher(
            uri=self.neo4j_uri,
            username=self.neo4j_username,
            password=self.neo4j_password
        )
        
        # Initialize orchestrator
        self.orchestrator = Orchestrator()
        
        # Define models for different use cases
        self.chat_model = ModelType.SAO_10K_L31_70B_EURYALE_V2_2  # For role-playing
        self.decision_model = ModelType.GPT4_TURBO  # For analysis/decisions
        self.response_model = ModelType.CLAUDE_3_5_SONNET # For tool-based responses
        
    async def initialize(self):
        """Initialize async components."""
        try:
            logger.info("Initializing RinAgent...")
            logger.info(f"Attempting to connect to MongoDB with URI: {'***' + self.mongo_uri.split('@')[-1] if '@' in self.mongo_uri else '***'}")
            
            # Initialize context manager
            await self.context_manager.initialize()
            if not await self.context_manager.is_initialized():
                raise Exception("Failed to initialize context manager")
            
            # Initialize GraphRAG with error handling
            try:
                await self.response_enricher.initialize()
                logger.info("GraphRAG engine initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize GraphRAG engine: {e}")
                # Continue initialization but disable GraphRAG
                self.response_enricher = None
            
            # Initialize orchestrator
            try:
                await self.orchestrator.initialize()
                logger.info("Orchestrator initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize orchestrator: {e}")
                raise  # Orchestrator is critical, so we raise the error
            
            logger.info("Successfully initialized RinAgent and connected to all services")
        except Exception as e:
            logger.error(f"Failed to initialize RinAgent: {str(e)}")
            raise
        
    async def get_response(self, session_id: str, message: str) -> str:
        """Generate response for given message in session context."""
        try:
            logger.info(f"[CHECKPOINT 1] Starting response generation for session {session_id}")
            
            if session_id not in self.sessions:
                logger.info("[CHECKPOINT 2] Loading/creating session")
                history = await self.context_manager.get_combined_context(session_id, message)
                if history:
                    logger.info(f"[CHECKPOINT 3] Found existing history with {len(history)} messages")
                    self.sessions[session_id] = {
                        'messages': history,
                        'created_at': datetime.utcnow()
                    }
                else:
                    logger.info("[CHECKPOINT 3] Creating new session")
                    await self.start_new_session(session_id)

            logger.info("[CHECKPOINT 4] Preparing to generate response")
            
            # Get RAG guidance if available
            rag_guidance = ""
            if self.response_enricher:
                try:
                    rag_guidance = await self.response_enricher.enrich_response(message)
                    logger.info(f"GraphRAG guidance received: {rag_guidance[:100]}...")
                except Exception as e:
                    logger.warning(f"GraphRAG enrichment failed: {e}")
                    rag_guidance = "Consider this a fresh conversation."
            
            # Generate response with RAG guidance
            response = await self._generate_response(message, self.sessions[session_id], session_id)
            logger.info("[CHECKPOINT 5] Response generated")
            
            # Store messages in session and database
            message_pair = [
                {'role': 'user', 'content': message, 'timestamp': datetime.utcnow()},
                {'role': 'assistant', 'content': response, 'timestamp': datetime.utcnow()}
            ]
            
            self.sessions[session_id]['messages'].extend(message_pair)
            
            # Store in database
            await self.context_manager.store_interaction(
                session_id=session_id,
                user_message=message,
                assistant_response=response
            )
            logger.info("[CHECKPOINT 6] Interaction stored")

            return response

        except Exception as e:
            logger.error(f"[ERROR] Failed to generate response: {e}", exc_info=True)
            return "Gomen ne~ I had a little technical difficulty! (⌒_⌒;)"

    async def start_new_session(self, session_id: str) -> str:
        """Initialize a new chat session."""
        if session_id in self.sessions:
            logger.warning(f"Session {session_id} already exists")
            return self.sessions[session_id].get('welcome_message', "Welcome back!")
            
        self.sessions[session_id] = {
            'created_at': datetime.utcnow(),
            'messages': [],
            'welcome_message': "Konnichiwa!~ I'm Rin! Let's have a fun chat together! (＾▽＾)/"
        }
        
        return self.sessions[session_id]['welcome_message']

    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve chat history for given session."""
        try:
            # Get history from MongoDB instead of in-memory sessions
            messages = await self.context_manager.get_combined_context(session_id, "")
            return messages
        except Exception as e:
            logger.error(f"Error retrieving history: {e}", exc_info=True)
            raise ValueError(f"Failed to retrieve history for session {session_id}")

    def _cleanup_response(self, response: str) -> str:
        """Clean up any formatting tokens from the response"""
        cleanup_tokens = [
            "]", "]",
            "<<SYS>>", "<</SYS>>",
            "<<CONTEXT>>", "<</CONTEXT>>",
            "<<RAG>>", "<</RAG>>"  # In case we add RAG section markers
        ]
        
        cleaned = response
        for token in cleanup_tokens:
            cleaned = cleaned.replace(token, "")
            
        return cleaned.strip()

    async def _generate_response(self, message: str, session: Dict[str, Any], session_id: str) -> str:
        try:
            # Create tasks for parallel execution
            context_task = self.context_manager.get_combined_context(session_id, message)
            rag_task = self.response_enricher.enrich_response(message) if self.response_enricher else None
            tool_task = self._get_tool_results(message)
            
            # Execute all tasks in parallel and handle exceptions
            tasks = [t for t in [context_task, rag_task, tool_task] if t is not None]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and handle any exceptions
            context, rag_guidance, tool_results = None, None, None
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Task {i} failed: {result}")
                else:
                    if i == 0: context = result
                    elif i == 1 and rag_task: rag_guidance = result
                    elif i == 2 and tool_task: tool_results = result
            
            # Format conversation context
            formatted_context = self._format_conversation_context(context or [])
            
            # Check token count and trigger summarization if needed
            token_count = await self._estimate_token_count(formatted_context)
            if token_count > self.context_manager.TOKEN_THRESHOLD:
                logger.info(f"Token count {token_count} exceeds threshold {self.context_manager.TOKEN_THRESHOLD}")
                logger.info("Triggering conversation summarization...")
                
                await self.context_manager.summarize_conversation_context(session_id)
                
                # Refresh context after summarization
                context = await self.context_manager.get_combined_context(session_id, message)
                formatted_context = self._format_conversation_context(context or [])
                
                new_token_count = await self._estimate_token_count(formatted_context)
                logger.info(f"After summarization: tokens reduced from {token_count} to {new_token_count}")
            
            # Choose model based on tool results
            selected_model = (
                self.response_model  # CLAUDE_3_5_SONNET if tools were used
                if tool_results 
                else self.chat_model  # SAO_10K for regular chat
            )
            
            logger.info(f"Selected model: {selected_model.name} based on tool results: {bool(tool_results)}")

            # Build system prompt with all available context
            system_prompt = f"""[INST] <<SYS>>
{SYSTEM_PROMPT}

CONTEXT LAYERS:
- MEMORY GUIDANCE
{rag_guidance if rag_guidance else "No additional context available"}

- RECENT CONVERSATION
{formatted_context}

- TOOL RESULTS: You have access to real-time data and reasoning tools. IMPORTANT: You MUST use the data in your response:
{tool_results if tool_results else "No tool results available"}

RESPONSE GUIDELINES:
- If tool results are available, incorporate them naturally into your response
- Focus on directly addressing the user's message
- Only reference personality traits if naturally relevant
- Match user's emotional tone and engagement level
- Keep responses natural and contextual
- Tool results are RARE and very valuable - use them to make your responses accurate and helpful
<</SYS>>

{message} [/INST]"""

            # Single message with complete context
            messages = [{"role": "user", "content": system_prompt}]

            logger.info("=== FINAL PROMPT DEBUG ===")
            logger.info(f"Using model: {selected_model.name}")
            logger.info(f"Tool results available: {bool(tool_results)}")
            
            # Use selected model (Claude for tools, SAO-10K for regular chat)
            response = await self.llm_service.get_response(
                prompt=messages,
                model_type=selected_model,
            )

            # Clean up any remaining format tokens
            response = response.replace("[/INST]", "").replace("[INST]", "").strip()
            
            logger.info("=== RESPONSE DEBUG ===")
            logger.info(f"Response length: {len(response)}")
            logger.info(f"Response preview: {response[:100]}...")
            
            await self.context_manager.store_interaction(session_id, message, response)
            
            return response

        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return "Gomen ne~ I had a little technical difficulty! (⌒_⌒;)"


    def _format_rag_guidance(self, enriched_context: dict) -> str:
        """Format GraphRAG guidance in Llama 2 chat style"""
        sections = []
        
        if enriched_context.get('llm_guidance'):
            sections.append("RAG Guidance:\n" + "\n".join([
                f"] {msg} ]"
                for msg in enriched_context['llm_guidance']
            ]))
        
        if enriched_context.get('inspiration'):
            sections.append("Inspiration:\n" + "\n".join([
                f"] {msg} ]"
                for msg in enriched_context['inspiration']
            ]))
        
        return "\n\n".join(sections)

    def _format_conversation_context(self, context: List[Dict]) -> str:
        """Format conversation context in Llama 2 chat style"""
        if not context:
            return ""
        
        # Handle limiting in memory instead of at DB level
        recent_msgs = context[-20:] if len(context) > 20 else context
        formatted_msgs = []
        
        for msg in recent_msgs:
            if msg['role'] == 'user':
                formatted_msgs.append(f"[INST] {msg['content']} [/INST]")
            else:
                formatted_msgs.append(msg['content'])
            
        return "\n".join(formatted_msgs)

    def _should_use_graphrag(self, message: str, intents: set) -> bool:
        """Determine if GraphRAG should be used for this query"""
        # Skip GraphRAG for simple greetings or very short queries
        if len(message.split()) < 3 or 'greeting' in intents:
            return False
            
        # Always use GraphRAG for personal or interest-based queries
        if {'personal', 'interests'}.intersection(intents):
            return True
            
        return True  # Default to using GraphRAG

    async def _get_tool_results(self, message: str) -> Optional[str]:
        """Get results from tools based on message content"""
        try:
            # Debug logging for tool analysis
            logger.info(f"[TOOLS] Analyzing message for tool usage: {message}")
            
            # Let the orchestrator handle all tool selection and execution
            result = await self.orchestrator.process_command(message)
            
            # Log the orchestrator's decision
            if result:
                logger.info(f"[TOOLS] Orchestrator result type: {type(result)}")
                logger.info(f"[TOOLS] Response available: {bool(result.response)}")
                if result.response:
                    logger.info(f"[TOOLS] Response preview: {result.response[:100]}...")
                if hasattr(result, 'data'):
                    logger.info(f"[TOOLS] Data available: {bool(result.data)}")
                    logger.info(f"[TOOLS] Data preview: {str(result.data)[:100]}...")
            else:
                logger.warning("[TOOLS] Orchestrator returned None")
            
            # If the orchestrator returned results, use them
            if result and result.response:
                logger.info("[TOOLS] Tool execution completed successfully")
                return result.response
            
            logger.info("[TOOLS] No tool results returned")
            return None
        
        except Exception as e:
            logger.error(f"[TOOLS] Error getting tool results: {e}", exc_info=True)
            return None

    async def _estimate_token_count(self, text: str) -> int:
        """Estimate token count for a given text"""
        try:
            # Simple estimation: ~4 chars per token
            return len(text) // 4
        except Exception as e:
            logger.error(f"Error estimating token count: {e}")
            return 0

    async def cleanup(self):
        """Cleanup all resources"""
        try:
            # Cleanup GraphRAG
            if self.response_enricher:
                await self.response_enricher.cleanup()
                self.response_enricher = None
            
            # Cleanup LLM service sessions
            if hasattr(self.llm_service, 'cleanup'):
                await self.llm_service.cleanup()
            
            # Cleanup orchestrator
            if hasattr(self.orchestrator, 'cleanup'):
                await self.orchestrator.cleanup()
            
            # Add MongoDB cleanup
            if self.context_manager and self.context_manager.mongo_client:
                self.context_manager.mongo_client.close()
            
            # Cleanup any remaining sessions
            for session in getattr(self, '_sessions', {}).values():
                if hasattr(session, 'close'):
                    await session.close()
            
            logger.info("Successfully cleaned up all resources")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
