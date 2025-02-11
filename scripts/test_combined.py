"""Test script for combined PDF extraction and sentiment analysis."""

import asyncio
import logging
import base64
from src.services.pdf_extraction.service import PDFExtractionService
from src.services.sentiment_analysis.service import SentimentAnalysisService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_combined_analysis():
    """Test combined PDF extraction and sentiment analysis."""
    try:
        logger.info("Starting combined PDF extraction and sentiment analysis test")

        # Initialize services
        pdf_service = PDFExtractionService()
        sentiment_service = SentimentAnalysisService()

        await pdf_service.initialize()
        await sentiment_service.initialize()
        logger.info("Services initialized successfully")

        # Read test PDF file
        with open("test_data/sample.pdf", "rb") as f:
            pdf_data = base64.b64encode(f.read()).decode()

        # Extract text from PDF
        pdf_request = {
            "pdf_data": pdf_data,
            "extract_text": True,
            "extract_tables": True,
            "extract_images": True
        }

        logger.info("Processing PDF extraction")
        pdf_result = await pdf_service.process(pdf_request)

        if pdf_result["status"] == "success":
            # Extract text from all pages
            all_text = ""
            for page in pdf_result["pages"]:
                if "text" in page:
                    all_text += page["text"] + "\n"

            logger.info("Extracted text from PDF:")
            logger.info(all_text)

            # Analyze sentiment of extracted text
            sentiment_request = {
                "text": all_text,
                "include_analysis": True
            }

            logger.info("Processing sentiment analysis")
            sentiment_result = await sentiment_service.process(sentiment_request)

            if sentiment_result["status"] == "success":
                logger.info("\nSentiment Analysis Results:")
                logger.info(f"Score: {sentiment_result.get('sentiment_score', 'N/A')}")
                logger.info(f"Label: {sentiment_result.get('sentiment_label', 'N/A')}")
                if "analysis" in sentiment_result:
                    logger.info(f"Analysis: {sentiment_result['analysis']}")
            else:
                logger.error(f"Sentiment analysis failed: {sentiment_result.get('error')}")
        else:
            logger.error(f"PDF extraction failed: {pdf_result.get('error')}")

        # Cleanup
        await pdf_service.cleanup()
        await sentiment_service.cleanup()
        logger.info("Test completed")

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(test_combined_analysis()) 