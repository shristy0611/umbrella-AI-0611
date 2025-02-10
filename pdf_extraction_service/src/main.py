import logging
import os
from typing import Dict, Optional, List
from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel
import PyPDF2
import tempfile
import google.generativeai as genai
from pdf2image import convert_from_path
import base64
import io
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_OCR")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY_OCR environment variable not set")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro-vision')

# Initialize FastAPI app
app = FastAPI(
    title="PDF Extraction Service",
    description="Service for extracting text from PDF files using Gemini API",
    version="1.0.0"
)

class ExtractionResponse(BaseModel):
    text: str
    pages: int
    metadata: Optional[Dict] = None
    analysis: Optional[Dict] = None

async def process_page_with_gemini(image_bytes: bytes) -> Dict:
    """Process a single page image with Gemini Vision API."""
    try:
        # Convert image bytes to base64
        image_parts = [
            {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_bytes).decode('utf-8')
            }
        ]

        # Generate prompt for Gemini
        prompt = """Analyze this page and provide:
        1. The extracted text content
        2. Any key information or insights
        3. The document structure and layout
        Format the response as JSON with these keys: text, insights, structure"""

        # Get response from Gemini
        response = model.generate_content([prompt, image_parts[0]])
        
        # Parse the response
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            # Fallback if response is not valid JSON
            result = {
                "text": response.text,
                "insights": [],
                "structure": "Unknown"
            }
            
        return result
    except Exception as e:
        logger.error(f"Error processing page with Gemini: {str(e)}")
        raise

@app.post("/extract", response_model=ExtractionResponse)
async def extract_pdf(file: UploadFile):
    """Extract text and insights from a PDF file using Gemini Vision API."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    try:
        # Create a temporary file to store the uploaded PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()

            # Convert PDF to images
            images = convert_from_path(temp_file.name)
            
            # Process each page with Gemini
            all_text = []
            all_insights = []
            structure_info = []
            
            for i, image in enumerate(images):
                # Convert image to bytes
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                img_byte_arr = img_byte_arr.getvalue()
                
                # Process with Gemini
                result = await process_page_with_gemini(img_byte_arr)
                
                all_text.append(result.get("text", ""))
                if "insights" in result:
                    all_insights.extend(result["insights"])
                if "structure" in result:
                    structure_info.append(result["structure"])

            return ExtractionResponse(
                text="\n\n".join(all_text),
                pages=len(images),
                metadata={
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "page_count": len(images)
                },
                analysis={
                    "insights": all_insights,
                    "structure": structure_info
                }
            )

    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF file: {str(e)}")

    finally:
        # Clean up temporary files
        if 'temp_file' in locals():
            os.unlink(temp_file.name)

@app.get("/health")
async def health_check():
    """Check the health of the service."""
    dependencies = {
        "gemini_api": "unhealthy"
    }
    
    try:
        # Test Gemini API
        test_response = model.generate_content("Test connection")
        if test_response:
            dependencies["gemini_api"] = "healthy"
    except Exception as e:
        logger.error(f"Gemini API health check failed: {str(e)}")

    # Overall status is healthy only if all dependencies are healthy
    overall_status = "healthy" if all(status == "healthy" for status in dependencies.values()) else "unhealthy"
    
    return {
        "status": overall_status,
        "service": "pdf_extraction",
        "dependencies": dependencies
    } 