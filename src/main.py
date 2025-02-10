import logging
import os
import uuid
from typing import Dict, List, Optional, Set
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import json
import asyncio
from .task_decomposer import DynamicTaskDecomposer, TaskDecomposition

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Umbrella AI Orchestrator",
    description="Orchestrates requests between different microservices",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
PDF_SERVICE_URL = os.getenv("PDF_SERVICE_URL", "http://localhost:8001")
SENTIMENT_SERVICE_URL = os.getenv("SENTIMENT_SERVICE_URL", "http://localhost:8002")
CHATBOT_SERVICE_URL = os.getenv("CHATBOT_SERVICE_URL", "http://localhost:8003")
SCRAPER_SERVICE_URL = os.getenv("SCRAPER_SERVICE_URL", "http://localhost:8004")
VECTOR_DB_URL = os.getenv("VECTOR_DB_URL", "http://localhost:8005")

SERVICE_URLS = {
    "pdf_extraction": PDF_SERVICE_URL,
    "sentiment": SENTIMENT_SERVICE_URL,
    "chatbot": CHATBOT_SERVICE_URL,
    "rag_scraper": SCRAPER_SERVICE_URL,
    "vector_db": VECTOR_DB_URL
}

class TaskRequest(BaseModel):
    task_type: str
    content: Dict
    context: Optional[Dict] = None

class TaskResponse(BaseModel):
    status: str
    result: Dict
    metadata: Optional[Dict] = None

# Initialize the task decomposer
task_decomposer = DynamicTaskDecomposer()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def call_service(service: str, action: str, data: Dict, correlation_id: str) -> Dict:
    """Call a service with retry logic."""
    if service not in SERVICE_URLS:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service}")
    
    url = f"{SERVICE_URLS[service]}/{action}"
    headers = {
        "X-Correlation-ID": correlation_id,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=data,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"HTTP error calling {service}/{action}: {str(e)}")
        raise HTTPException(status_code=response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Error calling {service}/{action}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ID to all requests for tracing."""
    correlation_id = request.headers.get("X-Correlation-ID", f"umbrella-{uuid.uuid4()}")
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response

@app.post("/process")
async def process_task(request: Request, task_request: TaskRequest):
    """Process a task by decomposing it and executing the subtasks."""
    correlation_id = request.state.correlation_id
    logger.info(f"[{correlation_id}] Processing task: {task_request.task_type}")
    
    try:
        # Validate task type
        if task_request.task_type not in ["document_analysis", "web_research", "chat_with_context"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid task type: {task_request.task_type}"
            )
            
        # Decompose task into subtasks
        decomposer = DynamicTaskDecomposer()
        decomposition = await decomposer.decompose(
            task_request.task_type,
            task_request.content,
            task_request.context
        )
        
        # Create and execute task graph
        graph = TaskGraph()
        for task_id, subtask in decomposition.tasks.items():
            graph.add_task(task_id, subtask)
            
        results = await graph.execute(correlation_id)
        
        return {
            "status": "success",
            "correlation_id": correlation_id,
            "results": results
        }
        
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
        
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
        
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Task processing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@app.get("/health")
async def health_check():
    """Check health of the orchestrator and its dependent services."""
    services = {
        name: {"status": "unknown", "url": url}
        for name, url in SERVICE_URLS.items()
    }
    
    # Check each service
    for service_name, service_info in services.items():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{service_info['url']}/health", timeout=2.0)
                services[service_name]["status"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            services[service_name]["status"] = "unhealthy"
            logger.error(f"Health check failed for {service_name}: {str(e)}")
    
    overall_status = "healthy" if all(s["status"] == "healthy" for s in services.values()) else "degraded"
    
    return {
        "status": overall_status,
        "services": services
    }

def add_correlation_id(correlation_id: str):
    """Add correlation ID to all log messages within this context."""
    def _log_with_correlation_id(msg, *args, **kwargs):
        extra = kwargs.pop("extra", {})
        extra["correlation_id"] = correlation_id
        return logging.getLogger(__name__).info(msg, *args, extra=extra, **kwargs)
    
    logger.info = _log_with_correlation_id 