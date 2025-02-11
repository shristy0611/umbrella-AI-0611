"""Test script for RAG scraper service."""

import asyncio
import logging
from src.services.rag_scraper.service import RAGScraperService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_rag_scraper():
    """Test the RAG scraper service."""
    try:
        logger.info("Starting RAG scraper test")

        # Initialize service
        service = RAGScraperService()
        await service.initialize()
        logger.info("RAG scraper service initialized")

        # Test request with sample URLs
        request = {
            "query": "What are the latest developments in artificial intelligence and machine learning?",
            "urls": [
                "https://www.wikipedia.org/wiki/Artificial_intelligence",
                "https://www.wikipedia.org/wiki/Machine_learning"
            ],
            "max_results": 3,
            "include_snippets": True
        }

        logger.info("Processing RAG scraper request")
        result = await service.process(request)

        # Log results
        if result["status"] == "success":
            logger.info("Successfully generated content:")
            for i, item in enumerate(result["content"], 1):
                logger.info(f"\nResult {i}:")
                logger.info(f"Title: {item.get('title')}")
                logger.info(f"Description: {item.get('description')}")
                logger.info(f"Source: {item.get('source', 'Not specified')}")
                if item.get('relevance_score') is not None:
                    logger.info(f"Relevance Score: {item['relevance_score']:.2f}")
                logger.info(f"Tags: {', '.join(item.get('tags', []))}")
        else:
            logger.error(f"Failed to generate content: {result.get('error')}")

        # Test request without URLs (should use default content generation)
        request_no_urls = {
            "query": "Explain the concept of neural networks in simple terms",
            "max_results": 2
        }

        logger.info("\nTesting content generation without URLs")
        result_no_urls = await service.process(request_no_urls)

        if result_no_urls["status"] == "success":
            logger.info("Successfully generated content without URLs:")
            for i, item in enumerate(result_no_urls["content"], 1):
                logger.info(f"\nResult {i}:")
                logger.info(f"Title: {item.get('title')}")
                logger.info(f"Description: {item.get('description')}")
                if item.get('relevance_score') is not None:
                    logger.info(f"Relevance Score: {item['relevance_score']:.2f}")
                logger.info(f"Tags: {', '.join(item.get('tags', []))}")
        else:
            logger.error(f"Failed to generate content: {result_no_urls.get('error')}")

        # Cleanup
        await service.cleanup()
        logger.info("Test completed")

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(test_rag_scraper()) 