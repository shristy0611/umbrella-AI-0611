import asyncio
import base64
import logging
from src.services.pdf_extraction.service import PDFExtractionService

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_pdf_extraction():
    """Test the PDF extraction service."""
    try:
        logger.info("Starting PDF extraction test")
        
        # Initialize service with real Gemini API
        logger.info("Initializing PDF extraction service")
        service = PDFExtractionService()
        await service.initialize()  # This will use the real API key
        logger.info("Service initialized successfully")
        
        # Read PDF file
        logger.info("Reading test PDF file")
        with open("test_data/sample.pdf", "rb") as f:
            pdf_data = f.read()
        logger.info("PDF file read successfully")
            
        # Create request
        request = {
            "pdf_data": base64.b64encode(pdf_data).decode(),
            "extract_tables": True,
            "extract_images": True
        }
        logger.info("Created extraction request")
        
        # Process request
        logger.info("Processing PDF extraction request")
        result = await service.process(request)
        
        print("Extraction Result:")
        print("-" * 50)
        print(result)
        logger.info("Test completed successfully")
        
    except Exception as e:
        logger.error(f"Error during test: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}")
    finally:
        await service.cleanup()

if __name__ == "__main__":
    asyncio.run(test_pdf_extraction()) 