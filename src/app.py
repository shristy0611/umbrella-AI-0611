"""Main FastAPI application module."""

import os
import uuid
import logging
import asyncio
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, BackgroundTasks, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager

# Import from shared modules
from shared.logging_config import logger, setup_logging
from shared.api_config import APIConfig

# Import local modules
from .orchestrator.orchestrator import Orchestrator
from .shared.service_registry import ServiceRegistry
from .task_decomposer import DynamicTaskDecomposer
from .services.chatbot.service import ChatbotService
from .services.pdf_extraction.service import PDFExtractionService
from .services.sentiment_analysis.service import SentimentAnalysisService
from .services.rag_scraper.service import RAGScraperService

# Setup logging for the app
setup_logging("api_gateway")

# Initialize FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    # Startup
    try:
        # Initialize API configuration
        api_config = APIConfig()
        await api_config.initialize()
        
        # Initialize services
        await service_registry.initialize()
        
        # Initialize orchestrator
        await orchestrator.initialize()
        
        logger.info("Application startup complete")
        yield
        
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise
    
    finally:
        # Cleanup
        try:
            await service_registry.cleanup()
            await orchestrator.cleanup()
            logger.info("Application shutdown complete")
        except Exception as e:
            logger.error(f"Shutdown error: {str(e)}")

app = FastAPI(
    title="UMBRELLA-AI",
    description="Multi-agent AI system for document analysis and interaction",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Initialize services
service_registry = ServiceRegistry()

# Create service instances
task_decomposer = DynamicTaskDecomposer(use_mock=True)
chatbot_service = ChatbotService(use_mock=True)
pdf_service = PDFExtractionService()
sentiment_service = SentimentAnalysisService()
rag_service = RAGScraperService()

# Register all services
service_registry.register_service("task_decomposer", task_decomposer)
service_registry.register_service("chatbot", chatbot_service)
service_registry.register_service("pdf_extraction", pdf_service)
service_registry.register_service("sentiment_analysis", sentiment_service)
service_registry.register_service("rag_scraper", rag_service)

# Initialize orchestrator and set service registry
orchestrator = Orchestrator()
orchestrator.service_registry = service_registry

# Models
class Task(BaseModel):
    task_type: str = Field(..., description="Type of task to execute")
    content: Dict[str, Any] = Field(..., description="Task content")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")

class Message(BaseModel):
    role: str = Field(..., description="Role of the message sender (user or assistant)")
    content: str = Field(..., description="Content of the message")

class ChatRequest(BaseModel):
    messages: List[Message] = Field(..., description="List of chat messages")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")

class ChatMessage(BaseModel):
    content: str = Field(..., description="Message content")
    session_id: str = Field(..., description="Chat session ID")

class ChatResponse(BaseModel):
    session_id: str
    response: str
    metadata: Dict[str, Any]

# Health check endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/chat/health")
async def chatbot_health():
    """Chatbot service health check endpoint."""
    return {"status": "healthy"}

@app.get("/pdf/health")
async def pdf_health():
    """PDF service health check endpoint."""
    return {"status": "healthy"}

@app.get("/sentiment/health")
async def sentiment_health():
    """Sentiment analysis service health check endpoint."""
    return {"status": "healthy"}

@app.get("/rag/health")
async def rag_health():
    """RAG scraper service health check endpoint."""
    return {"status": "healthy"}

# File upload endpoint
@app.post("/api/v1/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file for processing."""
    try:
        # Validate file type
        if not file.filename.endswith((".pdf", ".txt", ".doc", ".docx")):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only PDF, TXT, DOC, and DOCX files are supported."
            )
        
        # Read file content
        content = await file.read()
        
        # Store file (in-memory for now, replace with proper storage in production)
        file_id = f"file_{hash(content)}"
        
        return {"file_id": file_id, "filename": file.filename}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Task management endpoints
@app.post("/api/v1/tasks")
async def submit_task(task: Task, background_tasks: BackgroundTasks):
    """Submit a task for processing."""
    try:
        # Validate task type
        if task.task_type not in VALID_TASK_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid task type. Must be one of: {', '.join(VALID_TASK_TYPES)}"
            )
        
        task_id = await orchestrator.submit_task(task.model_dump())
        
        # Add task processing to background tasks
        background_tasks.add_task(orchestrator.process_task, task_id)
        
        return {"task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get task status."""
    try:
        status = await orchestrator.get_task_status(task_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tasks/{task_id}/results")
async def get_task_results(task_id: str):
    """Get task results."""
    try:
        results = await orchestrator.get_task_results(task_id)
        return results
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Chat endpoints
@app.post("/api/v1/chat/sessions")
async def create_chat_session():
    """Create a new chat session."""
    try:
        session = await chatbot_service.create_session()
        return {"session_id": session["session_id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/chat/messages")
async def chat_endpoint(chat_request: ChatRequest):
    correlation_id = str(uuid.uuid4())
    logger.info("Processing chat request", extra={"correlation_id": correlation_id})
    
    try:
        response = await chatbot_service.process_request(chat_request)
        logger.info("Chat request processed successfully", extra={"correlation_id": correlation_id})
        return {
            "session_id": str(uuid.uuid4()),
            "response": response,
            "metadata": {"correlation_id": correlation_id}
        }
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", extra={"correlation_id": correlation_id}, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/chat/sessions/{session_id}/history")
async def get_chat_history(session_id: str):
    """Get chat session history."""
    try:
        chatbot = service_registry.get_service("chatbot")
        history = await chatbot.get_session_history(session_id)
        return history
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Error handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail)}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors and return a detailed error response."""
    logging.error(f"Validation error for request {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

# Valid task types
VALID_TASK_TYPES = {"document_analysis", "sentiment_analysis", "rag_search", "chat"} 