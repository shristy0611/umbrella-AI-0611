"""End-to-end pipeline test for UMBRELLA-AI."""

import pytest
import asyncio
import logging
import time
import base64
from typing import Dict, Any, AsyncGenerator
from pathlib import Path

from src.services.service_registry import ServiceRegistry
from src.orchestrator.orchestrator import Orchestrator
from src.services.pdf_extraction.service import PDFExtractionService
from src.services.sentiment_analysis.service import SentimentAnalysisService
from src.services.chatbot.service import ChatbotService
from src.services.rag_scraper.service import RAGScraperService
from src.services.recommendation.service import RecommendationService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
async def service_registry() -> AsyncGenerator[ServiceRegistry, None]:
    """Create and initialize service registry for testing."""
    registry = ServiceRegistry()
    
    # Initialize services
    pdf_service = PDFExtractionService()
    sentiment_service = SentimentAnalysisService()
    chatbot_service = ChatbotService()
    rag_service = RAGScraperService()
    recommendation_service = RecommendationService()
    
    # Register services with explicit names
    registry.register_service("pdf_extraction", pdf_service)
    registry.register_service("sentiment_analysis", sentiment_service)
    registry.register_service("chatbot", chatbot_service)
    registry.register_service("rag_scraper", rag_service)
    registry.register_service("recommendation", recommendation_service)
    
    await registry.initialize()
    yield registry
    await registry.cleanup()

@pytest.fixture(scope="module")
async def orchestrator() -> AsyncGenerator[Orchestrator, None]:
    """Create and initialize orchestrator for testing."""
    orchestrator = Orchestrator()
    await orchestrator.initialize()
    yield orchestrator
    await orchestrator.cleanup()

@pytest.fixture(scope="module")
def sample_pdf_data() -> str:
    """Load sample PDF data."""
    pdf_path = Path("test_data/sample.pdf")
    with open(pdf_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

@pytest.mark.asyncio
async def test_pipeline(service_registry: ServiceRegistry, orchestrator: Orchestrator, sample_pdf_data: str):
    """Test complete pipeline workflow.
    
    This test covers:
    1. Service health checks
    2. PDF extraction
    3. Sentiment analysis
    4. RAG processing
    5. Chatbot interaction
    6. Recommendation generation
    7. Error handling and recovery
    """
    try:
        # Step 1: Health Checks
        logger.info("Step 1: Performing health checks")
        registry_health = await service_registry.health_check()
        assert registry_health["status"] == "healthy", "Service registry not healthy"
        
        for name, service in service_registry.list_services().items():
            health = await service.health_check()
            assert health["status"] == "healthy", f"Service {name} not healthy"
        
        # Step 2: PDF Processing
        logger.info("Step 2: Processing PDF")
        pdf_service = service_registry.get_service("pdf_extraction")
        pdf_result = await pdf_service.process({
            "pdf_data": sample_pdf_data,
            "extract_text": True,
            "extract_tables": True
        })
        assert pdf_result["status"] == "success", "PDF extraction failed"
        
        # Step 3: Sentiment Analysis
        logger.info("Step 3: Analyzing sentiment")
        extracted_text = " ".join(page.get("text", "") for page in pdf_result["pages"])
        sentiment_service = service_registry.get_service("sentiment_analysis")
        sentiment_result = await sentiment_service.process({
            "text": extracted_text,
            "include_analysis": True
        })
        assert sentiment_result["status"] == "success", "Sentiment analysis failed"
        
        # Step 4: RAG Processing
        logger.info("Step 4: RAG processing")
        rag_service = service_registry.get_service("rag_scraper")
        rag_result = await rag_service.process({
            "query": "What are the main topics in this document?",
            "context": extracted_text
        })
        assert rag_result["status"] == "success", "RAG processing failed"
        
        # Step 5: Chatbot Interaction
        logger.info("Step 5: Testing chatbot")
        chatbot_service = service_registry.get_service("chatbot")
        chat_result = await chatbot_service.process({
            "messages": [{
                "role": "user",
                "content": "Summarize the main points of this document"
            }],
            "context": {
                "document": extracted_text,
                "sentiment": sentiment_result,
                "topics": rag_result
            }
        })
        assert chat_result["status"] == "success", "Chatbot interaction failed"
        
        # Step 6: Generate Recommendations
        logger.info("Step 6: Generating recommendations")
        recommendation_service = service_registry.get_service("recommendation")
        recommendation_result = await recommendation_service.process({
            "context": {
                "document": extracted_text,
                "topics": rag_result["content"],
                "sentiment": sentiment_result
            },
            "user_preferences": {
                "interests": ["AI", "Machine Learning"],
                "skill_level": "intermediate"
            }
        })
        assert recommendation_result["status"] == "success", "Recommendation generation failed"
        
        # Step 7: Test Error Recovery
        logger.info("Step 7: Testing error recovery")
        # Simulate a service failure and recovery
        pdf_service._initialized = False  # Simulate failure
        health_after_failure = await pdf_service.health_check()
        assert health_after_failure["status"] == "unhealthy", "Failed to detect unhealthy state"
        
        # Recover service
        await pdf_service.initialize()
        health_after_recovery = await pdf_service.health_check()
        assert health_after_recovery["status"] == "healthy", "Failed to recover service"
        
        # Final validation
        logger.info("Pipeline test completed successfully")
        return {
            "pdf_result": pdf_result,
            "sentiment_result": sentiment_result,
            "rag_result": rag_result,
            "chat_result": chat_result,
            "recommendation_result": recommendation_result
        }
        
    except Exception as e:
        logger.error(f"Pipeline test failed: {str(e)}")
        raise

if __name__ == "__main__":
    pytest.main(["-v", "pipeline_test.py"]) 