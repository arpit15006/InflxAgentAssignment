"""
AutoStream API Server — FastAPI Backend
Serves the conversational AI agent via REST API.

Endpoints:
  POST /chat — Process user message through the agent
  GET  /health — Health check
"""

import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import process_message
from rag import initialize_rag

# ============================================================
# Logging Configuration
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-15s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("autostream.api")


# ============================================================
# Lifespan: Initialize FAISS on startup
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize FAISS vector store on server startup."""
    logger.info("=" * 60)
    logger.info("  AutoStream Agent Server Starting...")
    logger.info("=" * 60)
    initialize_rag()
    logger.info("FAISS RAG pipeline ready")
    logger.info("Server ready to accept requests")
    logger.info("=" * 60)
    yield
    logger.info("Server shutting down...")


# ============================================================
# FastAPI App
# ============================================================
app = FastAPI(
    title="AutoStream – Social-to-Lead AI Agent",
    description="Agentic AI workflow for converting conversations into qualified leads",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — Allow frontend
default_allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://inflix-agent-assignment-cz64.vercel.app",
]

allowed_origins_env = os.getenv("FRONTEND_ORIGINS", "").strip()
allowed_origins = (
    [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
    if allowed_origins_env
    else default_allowed_origins
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Request / Response Models
# ============================================================
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Session ID for multi-turn conversation tracking",
    )


class ChatResponse(BaseModel):
    response: str


# ============================================================
# Endpoints
# ============================================================
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a user message through the AutoStream AI agent.
    
    The agent will:
    1. Detect intent (greeting | pricing | high_intent)
    2. Route to appropriate handler
    3. Maintain context across 5-6 turns
    4. Execute lead capture tool when all fields are collected
    """
    try:
        logger.info(f"[API] Session: {request.session_id} | Message: {request.message[:80]}")
        
        response = process_message(
            message=request.message,
            session_id=request.session_id,
        )
        
        logger.info(f"[API] Response: {response[:80]}...")
        return ChatResponse(response=response)

    except Exception as e:
        logger.error(f"[API] Error processing message: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your message. Please try again.",
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "autostream-agent"}
