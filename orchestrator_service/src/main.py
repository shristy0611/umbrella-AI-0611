"""Main module for the orchestrator service."""

import asyncio
import logging
import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import uuid

from .task_decomposer import DynamicTaskDecomposer, TaskType
from .task_graph import TaskGraph
from ..src.communication.messaging import MessageBroker
from ..src.communication.service_client import ServiceClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Orchestrator Service")

# Initialize task decomposer
task_decomposer = DynamicTaskDecomposer()

# Initialize message broker
message_broker = None

# Initialize service clients
service_clients: Dict[str, ServiceClient] = {}

class TaskRequest(BaseModel):
    """Request model for task processing."""
    task_type: TaskType
    content: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None

class TaskResponse(BaseModel):
    """Response model for task processing."""
    status: str
    result: Dict[str, Any]
    metadata: Dict[str, Any]

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup."""
    global message_broker, service_clients
    
    # Initialize message broker
    message_broker = MessageBroker("orchestrator")
    await message_broker.connect()
    
    # Initialize service clients
    service_urls = {
        "pdf_extraction": os.getenv("PDF_SERVICE_URL", "http://pdf_extraction:8001"),
        "sentiment": os.getenv("SENTIMENT_SERVICE_URL", "http://sentiment:8002"),
        "chatbot": os.getenv("CHATBOT_SERVICE_URL", "http://chatbot:8003"),
        "scraper": os.getenv("SCRAPER_SERVICE_URL", "http://scraper:8004"),
        "vector_db": os.getenv("VECTOR_DB_URL", "http://vector_db:8005")
    }
    
    for service_name, url in service_urls.items():
        service_clients[service_name] = ServiceClient(url, service_name)

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown."""
    if message_broker:
        await message_broker.close()
    
    for client in service_clients.values():
        await client.close()

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ID to request."""
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response

@app.post("/process", response_model=TaskResponse)
async def process_task(request: Request, task_request: TaskRequest):
    """Process a task by coordinating with other services."""
    correlation_id = request.state.correlation_id
    
    try:
        # Decompose task into subtasks
        decomposition = await task_decomposer.decompose(
            task_request.task_type,
            task_request.content,
            task_request.context
        )
        
        # Create task graph
        graph = TaskGraph()
        for task_id, task in decomposition.tasks.items():
            graph.add_task(task_id, task)
        
        # Execute task graph
        result = await graph.execute(correlation_id)
        
        return TaskResponse(
            status="success",
            result=result,
            metadata={
                "correlation_id": correlation_id,
                "task_type": task_request.task_type,
                "subtasks": len(decomposition.tasks)
            }
        )
        
    except Exception as e:
        logger.error(
            f"Error processing task: {str(e)}",
            extra={"correlation_id": correlation_id}
        )
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check(request: Request):
    """Check health of the orchestrator and its dependencies."""
    correlation_id = request.state.correlation_id
    service_status = {}
    
    # Check service health concurrently
    async def check_service(name: str, client: ServiceClient):
        try:
            response = await client.request("GET", "/health", correlation_id)
            return name, response.get("status", "unknown")
        except Exception as e:
            logger.error(f"Health check failed for {name}: {str(e)}")
            return name, "unhealthy"
    
    # Create health check tasks
    tasks = [
        check_service(name, client)
        for name, client in service_clients.items()
    ]
    
    # Wait for all health checks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    for name, status in results:
        if isinstance(status, Exception):
            service_status[name] = "unhealthy"
        else:
            service_status[name] = status
    
    # Determine overall status
    overall_status = "healthy" if all(
        status == "healthy" for status in service_status.values()
    ) else "unhealthy"
    
    return {
        "status": overall_status,
        "service": "orchestrator",
        "dependencies": service_status,
        "correlation_id": correlation_id
    } 