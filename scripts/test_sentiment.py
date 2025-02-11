"""Test script for sentiment analysis service."""

import asyncio
import logging
from src.services.sentiment.service import SentimentService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_sentiment():
    """Test the sentiment analysis service."""
    try:
        logger.info("Starting sentiment analysis test")

        # Initialize service
        service = SentimentService()
        await service.initialize()
        logger.info("Sentiment analysis service initialized")

        # Test cases with different types of text
        test_cases = [
            "I absolutely love this product! It's amazing and works perfectly.",
            "This is terrible. I'm very disappointed with the quality.",
            "The product is okay. It works as expected but could be better.",
            "While there are some issues, overall it's a decent solution.",
            "I can't believe how bad this is. Complete waste of money!"
        ]

        logger.info("Processing sentiment analysis requests")
        
        for text in test_cases:
            request = {
                "text": text,
                "include_analysis": True
            }
            
            result = await service.process(request)
            
            if result["status"] == "success":
                logger.info("\nAnalysis Result:")
                logger.info(f"Text: {text}")
                logger.info(f"Sentiment Score: {result['sentiment_score']:.2f}")
                logger.info(f"Sentiment Label: {result['sentiment_label']}")
                if "analysis" in result:
                    logger.info(f"Detailed Analysis: {result['analysis']}")
            else:
                logger.error(f"Failed to analyze text: {result.get('error')}")

        # Test batch processing
        batch_request = {
            "texts": test_cases,
            "include_analysis": True
        }
        
        logger.info("\nTesting batch processing")
        batch_result = await service.process(batch_request)
        
        if batch_result["status"] == "success":
            logger.info("Successfully processed batch:")
            for i, result in enumerate(batch_result["results"]):
                logger.info(f"\nBatch Result {i+1}:")
                logger.info(f"Text: {test_cases[i]}")
                logger.info(f"Sentiment Score: {result['sentiment_score']:.2f}")
                logger.info(f"Sentiment Label: {result['sentiment_label']}")
        else:
            logger.error(f"Failed to process batch: {batch_result.get('error')}")

        # Cleanup
        await service.cleanup()
        logger.info("Test completed")

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_sentiment()) 