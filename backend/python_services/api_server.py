import os
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from fastapi.security import APIKeyHeader, HTTPBearer
from pydantic_settings import BaseSettings
from pydantic import BaseModel, ValidationError, Field
from dotenv import load_dotenv
from redis.asyncio import Redis
import httpx
import socket
import sys
import pytz
from motor.motor_asyncio import AsyncIOMotorClient
import uuid
from typing import Optional, Dict, Any
import asyncio
from enum import Enum, auto
import jwt

# Import required components
from core.llm.llm_service import LLMService
from core.agent.agent import RinAgent
from core.agent.handlers import RinMessageHandler 
from core.db.mongo_manager import MongoManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(Path(__file__).parents[3] / 'backend' / '.env')

class Settings(BaseSettings):
    PYTHON_SERVICE_API_KEY: str
    PYTHON_SERVICE_SECRET: str
    PYTHON_SERVICE_URL: str = "http://localhost:8000" 
    REDIS_URL: str
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str = None
    MONGO_URI: str
    MONGO_DB: str
    
    class Config:
        env_file = Path(__file__).parents[3] / 'backend' / '.env'
        env_prefix = ""
        case_sensitive = True
        extra = "ignore"

settings = Settings()

app = FastAPI()
api_key_header = APIKeyHeader(name="X-API-Key")
security = HTTPBearer()
agent = None

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_api_key(api_key: str = Depends(api_key_header)) -> bool:
    if api_key != settings.PYTHON_SERVICE_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True

@app.get("/health")
async def health_check():
    try:
        # Check all critical services
        redis_status = await redis_client.ping() if redis_client else False
        mongo_status = await MongoManager.is_connected()
        agent_status = agent is not None and hasattr(agent, 'is_initialized')
        
        if all([redis_status, mongo_status, agent_status]):
            return {
                "status": "healthy",
                "service": "python-nlp",
                "redis_connected": True,
                "mongo_connected": True,
                "agent_initialized": True,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "degraded",
                "service": "python-nlp",
                "redis_connected": bool(redis_status),
                "mongo_connected": bool(mongo_status),
                "agent_initialized": bool(agent_status),
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "python-nlp",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Add at top level
redis_client: Redis = None

@app.on_event("startup")
async def startup_event():
    global redis_client, agent
    
    try:
        # Initialize MongoDB first
        await MongoManager.initialize(settings.MONGO_URI, settings.MONGO_DB)
        logger.info("✅ MongoDB connection established")
        
        # Initialize Redis with similar config to Node.js
        redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
            retry_on_timeout=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            # Match Node.js retry strategy
            retry_on_error=[TimeoutError, ConnectionError],
            max_connections=10,
            health_check_interval=2000
        )

        # Test connection with retries (similar to Node.js)
        retry_count = 0
        max_retries = 5
        while retry_count < max_retries:
            try:
                await redis_client.ping()
                logger.info("✅ Redis connection established")
                break
            except Exception as e:
                retry_count += 1
                delay = min(retry_count * 50, 2000)  # Match Node.js retry delay
                if retry_count >= max_retries:
                    logger.error("❌ Redis retry limit exceeded")
                    raise
                logger.warning(f"Retrying Redis connection in {delay}ms...")
                await asyncio.sleep(delay / 1000)  # Convert ms to seconds
        
        # Initialize Rin agent with proper database
        agent = RinAgent(mongo_uri=settings.MONGO_URI)
        await agent.initialize()
        logger.info("✅ Rin agent initialized")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    try:
        if 'redis_client' in globals() and redis_client:
            await redis_client.close()
        await MongoManager.close()
        logger.info("Services shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    body = await request.body()
    logger.info(f"Received request body: {body.decode()}")
    response = await call_next(request)
    return response

@app.post("/api/session/init")
async def initialize_session(token: str = Depends(security)):
    try:
        # Use the correct method from RinAgent
        session_id = str(uuid.uuid4())  # Generate a session ID
        welcome_message = await agent.start_new_session(session_id)
        
        return {
            "session_id": session_id,
            "welcome_message": welcome_message
        }
    except Exception as e:
        logger.error(f"Session initialization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    try:
        body = await request.json()
        session_id = body.get("session_id")
        message = body.get("message")
        
        if not session_id or not message:
            raise HTTPException(status_code=400, detail="Missing session_id or message")
            
        # Use get_response instead of chat
        response = await agent.get_response(
            session_id=session_id,
            message=message
        )
        
        return {
            "status": "success",
            "response": response
        }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/{session_id}")
async def get_history(
    session_id: str,
    token: str = Depends(security)
):
    try:
        history = await agent.context_manager.get_session_history(session_id)
        return {
            "status": "success",
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
