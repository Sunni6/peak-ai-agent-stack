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
        # Remove Redis check
        mongo_status = await MongoManager.is_connected()
        agent_status = agent is not None and hasattr(agent, 'is_initialized')
        
        if all([mongo_status, agent_status]):
            return {
                "status": "healthy",
                "service": "python-nlp",
                "mongo_connected": True,
                "agent_initialized": True,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "degraded",
                "service": "python-nlp",
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

@app.on_event("startup")
async def startup_event():
    global agent  # Remove redis_client from global
    
    try:
        # Initialize MongoDB first
        await MongoManager.initialize(settings.MONGO_URI, settings.MONGO_DB)
        logger.info("✅ MongoDB connection established")
        
        # Remove all Redis initialization code
        # redis_client = Redis(...)
        # await redis_client.ping()
        
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
        # Remove Redis cleanup
        # if redis_client:
        #     await redis_client.close()
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
