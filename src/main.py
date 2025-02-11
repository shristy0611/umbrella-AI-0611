"""Main application module for UMBRELLA-AI."""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from shared.service_registry import ServiceRegistry
from shared.logging_config import setup_logging
from shared.middleware import setup_middleware
from .services import (
    PDFExtractionService,
    SentimentAnalysisService,
    ChatbotService,
    RAGScraperService,
    VectorDBService,
    OrchestratorService,
)

# Configure logging
setup_logging("umbrella_ai", os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="UMBRELLA-AI",
    description="Multi-agent system for document analysis and interaction",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
setup_middleware(app, "umbrella_ai")

# Initialize service registry
registry = ServiceRegistry()


# Register services
def init_services():
    """Initialize and register all services."""
    try:
        # Initialize services
        pdf_service = PDFExtractionService()
        sentiment_service = SentimentAnalysisService()
        chatbot_service = ChatbotService()
        rag_service = RAGScraperService()
        vector_service = VectorDBService()
        orchestrator_service = OrchestratorService()

        # Register services
        registry.register("pdf_extraction", pdf_service)
        registry.register("sentiment_analysis", sentiment_service)
        registry.register("chatbot", chatbot_service)
        registry.register("rag_scraper", rag_service)
        registry.register("vector_db", vector_service)
        registry.register("orchestrator", orchestrator_service)

        logger.info("All services initialized and registered successfully")
    except Exception as e:
        logger.error(f"Error initializing services: {str(e)}")
        raise


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    init_services()


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down UMBRELLA-AI")


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Check the health of all services."""
    services = {
        "pdf_extraction": "http://localhost:8001/health",
        "sentiment": "http://localhost:8002/health",
        "chatbot": "http://localhost:8003/health",
        "rag_scraper": "http://localhost:8004/health",
        "vector_db": "http://localhost:8005/health",
        "orchestrator": "http://localhost:8006/health",
    }

    service_statuses = {}
    overall_status = "healthy"

    async with httpx.AsyncClient() as client:
        for service_name, url in services.items():
            try:
                response = await client.get(url, timeout=5.0)
                if response.status_code == 200:
                    service_statuses[service_name] = "healthy"
                else:
                    service_statuses[service_name] = "degraded"
                    overall_status = "degraded"
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {str(e)}")
                service_statuses[service_name] = "unhealthy"
                overall_status = "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "services": service_statuses,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("API_DEBUG", "false").lower() == "true",
    )
