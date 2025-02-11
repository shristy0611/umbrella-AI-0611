"""Test script for recommendation service."""

import asyncio
import logging
from src.services.recommendation.service import RecommendationService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_recommendation_service():
    """Test the recommendation service."""
    try:
        logger.info("Starting recommendation service test")

        # Initialize service
        service = RecommendationService()
        await service.initialize()
        logger.info("Recommendation service initialized")

        # Test request
        request = {
            "context": {
                "recently_viewed": ["Machine Learning basics", "Python programming"],
                "interests": ["AI", "Programming", "Data Science"],
                "skill_level": "intermediate"
            },
            "user_preferences": {
                "preferred_topics": ["Deep Learning", "Natural Language Processing"],
                "learning_style": "hands-on",
                "time_availability": "2-3 hours per week"
            },
            "num_recommendations": 3,
            "recommendation_type": "learning_path"
        }

        logger.info("Processing recommendation request")
        result = await service.process(request)

        # Log results
        if result["status"] == "success":
            logger.info("Successfully generated recommendations:")
            for i, rec in enumerate(result["recommendations"], 1):
                logger.info(f"\nRecommendation {i}:")
                logger.info(f"Title: {rec.get('title')}")
                logger.info(f"Description: {rec.get('description')}")
                relevance_score = rec.get('relevance_score')
                if relevance_score is not None:
                    logger.info(f"Relevance Score: {relevance_score:.2f}")
                else:
                    logger.warning("Relevance Score: Not available")
                logger.info(f"Tags: {', '.join(rec.get('tags', []))}")
                logger.info(f"Reasoning: {rec.get('reasoning')}")
        else:
            logger.error(f"Failed to generate recommendations: {result.get('error')}")

        # Cleanup
        await service.cleanup()
        logger.info("Test completed")

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(test_recommendation_service()) 