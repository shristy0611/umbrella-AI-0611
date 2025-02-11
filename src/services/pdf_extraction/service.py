"""PDF extraction service for UMBRELLA-AI."""

import base64
import logging
from typing import Dict, Any, List, Optional
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io
from src.shared.base_service import BaseService
from src.shared.api_config import api_config
from src.shared.gemini_config import gemini_config
from datetime import datetime
from fastapi import APIRouter
from functools import lru_cache
import asyncio
import os
import re

logger = logging.getLogger(__name__)

router = APIRouter()


class PDFExtractionService(BaseService):
    """Service for extracting text and information from PDFs using Gemini."""

    def __init__(self):
        """Initialize the PDF extraction service."""
        super().__init__("pdf_extraction")
        self.model = None
        self._page_limit = 50  # Maximum pages to process

    async def initialize(self) -> None:
        """Initialize the service and configure Gemini API."""
        try:
            # Initialize API configuration
            await api_config.initialize()

            # Configure Gemini model
            self.model = gemini_config.configure_model("OCR")

            self._initialized = True
            logger.info("PDF extraction service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize PDF extraction service: {str(e)}")
            raise

    async def cleanup(self) -> None:
        """Clean up service resources."""
        self.model = None
        await super().cleanup()

    async def health_check(self) -> Dict[str, str]:
        """Check service health.
        
        Returns:
            Dict[str, str]: Health status
        """
        return {
            "status": "healthy" if self._initialized and self.model is not None else "unhealthy"
        }

    async def validate_request(self, request: Dict[str, Any]) -> bool:
        """Validate extraction request.

        Args:
            request: Request to validate

        Returns:
            bool: True if request is valid
        """
        if "pdf_data" not in request:
            return False
        try:
            # Try to decode base64 data
            pdf_data = base64.b64decode(request["pdf_data"])
            # Verify it's a valid PDF
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            doc.close()
            return True
        except Exception as e:
            logger.error(f"Invalid PDF data: {str(e)}")
            return False

    async def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a PDF extraction request.

        Args:
            request: Dictionary containing:
                - pdf_data: PDF content in base64
                - extract_text: Whether to extract text (default: True)
                - extract_tables: Whether to extract tables (default: True)
                - extract_images: Whether to extract images (default: True)
                - page_numbers: Optional list of specific pages to process

        Returns:
            Dict[str, Any]: Extraction results

        Raises:
            ValueError: If request is invalid or processing fails
        """
        try:
            # Get PDF data
            pdf_data = base64.b64decode(request["pdf_data"])
            extract_text = request.get("extract_text", True)
            extract_tables = request.get("extract_tables", True)
            extract_images = request.get("extract_images", True)
            page_numbers = request.get("page_numbers", None)

            # Open PDF document
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            
            try:
                # Get metadata
                metadata = self._extract_metadata(doc)
                
                # Validate page numbers
                total_pages = len(doc)
                if page_numbers:
                    page_numbers = [p for p in page_numbers if 0 <= p < total_pages]
                else:
                    page_numbers = range(min(total_pages, self._page_limit))

                if not page_numbers:
                    raise ValueError("No valid pages to process")

                # Process pages
                results = []
                for page_num in page_numbers:
                    page_result = await self._process_page(
                        doc[page_num],
                        extract_text=extract_text,
                        extract_tables=extract_tables,
                        extract_images=extract_images
                    )
                    results.append({
                        "page_number": page_num + 1,
                        **page_result
                    })

                return {
                    "status": "success",
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "service": self.service_name,
                        **metadata
                    },
                    "pages": results
                }

            finally:
                doc.close()

        except Exception as e:
            logger.error(f"PDF extraction failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "service": self.service_name,
                "metadata": {
                    "timestamp": datetime.now().isoformat()
                }
            }

    def _extract_metadata(self, pdf_document: fitz.Document) -> Dict[str, Any]:
        """Extract PDF metadata.

        Args:
            pdf_document: PDF document

        Returns:
            Dict[str, Any]: Metadata
        """
        try:
            metadata = pdf_document.metadata if hasattr(pdf_document, 'metadata') else {}
            basic_metadata = {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "keywords": metadata.get("keywords", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "creation_date": metadata.get("creationDate", ""),
                "modification_date": metadata.get("modDate", ""),
                "page_count": len(pdf_document),
                "file_size": pdf_document.stream_length if hasattr(pdf_document, 'stream_length') else 0,
                "is_encrypted": pdf_document.is_encrypted if hasattr(pdf_document, 'is_encrypted') else False,
            }

            # Try to get format and version safely
            try:
                basic_metadata["format"] = "PDF"
                if hasattr(pdf_document, 'version'):
                    basic_metadata["version"] = f"{pdf_document.version / 10:.1f}"
                else:
                    basic_metadata["version"] = "Unknown"
            except Exception:
                basic_metadata["format"] = "PDF"
                basic_metadata["version"] = "Unknown"

            return basic_metadata

        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            return {
                "page_count": len(pdf_document),
                "error": str(e)
            }

    async def _process_page(
        self,
        page: fitz.Page,
        extract_text: bool = True,
        extract_tables: bool = True,
        extract_images: bool = True
    ) -> Dict[str, Any]:
        """Process a single PDF page.

        Args:
            page: PDF page
            extract_text: Whether to extract text
            extract_tables: Whether to extract tables
            extract_images: Whether to extract images

        Returns:
            Dict[str, Any]: Page extraction results
        """
        result = {}

        try:
            # Convert page to image
            zoom = 2  # Increase resolution
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))

            # Extract content using Gemini
            prompt = self._build_extraction_prompt(
                extract_text=extract_text,
                extract_tables=extract_tables,
                extract_images=extract_images
            )

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    [prompt, img],
                    generation_config={"temperature": 0.1, "top_p": 0.8, "top_k": 40},
                )
            )

            # Parse response
            content = self._parse_extraction_response(response.text)
            result.update(content)

            # Add page info
            result["page_info"] = {
                "width": page.rect.width,
                "height": page.rect.height,
                "rotation": page.rotation,
                "has_images": bool(page.get_images()),
                "has_links": bool(page.get_links()),
            }

        except Exception as e:
            logger.error(f"Error processing page: {str(e)}")
            result["error"] = str(e)

        return result

    def _build_extraction_prompt(
        self,
        extract_text: bool = True,
        extract_tables: bool = True,
        extract_images: bool = True
    ) -> str:
        """Build the extraction prompt for Gemini.

        Args:
            extract_text: Whether to extract text
            extract_tables: Whether to extract tables
            extract_images: Whether to extract images

        Returns:
            str: Extraction prompt
        """
        prompt = []
        
        if extract_text:
            prompt.append("Extract all text content from this PDF page, maintaining the original formatting and structure.")
        
        if extract_tables:
            prompt.append("""
If there are any tables:
1. Identify and extract them
2. Preserve their structure
3. Format them clearly with headers and data
4. Indicate the start and end of each table with [TABLE] and [/TABLE] tags
""")
        
        if extract_images:
            prompt.append("""
For any images or figures:
1. Describe their content
2. Note their position on the page
3. Explain any text or captions associated with them
4. Mark image descriptions with [IMAGE] and [/IMAGE] tags
""")
        
        prompt.append("""
Format the response as follows:
{
    "text": "extracted text content",
    "tables": [
        {
            "headers": ["column1", "column2", ...],
            "data": [
                ["row1col1", "row1col2", ...],
                ["row2col1", "row2col2", ...]
            ]
        }
    ],
    "images": [
        {
            "description": "image description",
            "position": "location on page",
            "caption": "associated caption"
        }
    ]
}
""")
        
        return "\n".join(prompt)

    def _parse_extraction_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the extraction response.

        Args:
            response_text: Raw response text

        Returns:
            Dict[str, Any]: Parsed content
        """
        try:
            # Try to parse as JSON first
            import json
            return json.loads(response_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract structured content
            result = {
                "text": "",
                "tables": [],
                "images": []
            }

            # Extract tables
            table_matches = re.finditer(r'\[TABLE\](.*?)\[/TABLE\]', response_text, re.DOTALL)
            for match in table_matches:
                table_text = match.group(1).strip()
                # Parse table structure
                table = self._parse_table_text(table_text)
                if table:
                    result["tables"].append(table)

            # Extract images
            image_matches = re.finditer(r'\[IMAGE\](.*?)\[/IMAGE\]', response_text, re.DOTALL)
            for match in image_matches:
                image_text = match.group(1).strip()
                # Parse image description
                image = self._parse_image_text(image_text)
                if image:
                    result["images"].append(image)

            # Extract remaining text (excluding tables and images)
            text = re.sub(r'\[TABLE\].*?\[/TABLE\]', '', response_text, flags=re.DOTALL)
            text = re.sub(r'\[IMAGE\].*?\[/IMAGE\]', '', text, flags=re.DOTALL)
            result["text"] = text.strip()

            return result

    def _parse_table_text(self, table_text: str) -> Optional[Dict[str, Any]]:
        """Parse table text into structured format.

        Args:
            table_text: Raw table text

        Returns:
            Optional[Dict[str, Any]]: Parsed table structure
        """
        try:
            lines = [line.strip() for line in table_text.split('\n') if line.strip()]
            if not lines:
                return None

            # First line is headers
            headers = [h.strip() for h in re.split(r'\s{2,}|\t', lines[0])]
            
            # Remaining lines are data
            data = []
            for line in lines[1:]:
                row = [cell.strip() for cell in re.split(r'\s{2,}|\t', line)]
                if len(row) == len(headers):  # Only add valid rows
                    data.append(row)

            return {
                "headers": headers,
                "data": data
            }
        except Exception as e:
            logger.error(f"Error parsing table: {str(e)}")
            return None

    def _parse_image_text(self, image_text: str) -> Optional[Dict[str, Any]]:
        """Parse image description text.

        Args:
            image_text: Raw image description text

        Returns:
            Optional[Dict[str, Any]]: Parsed image information
        """
        try:
            lines = [line.strip() for line in image_text.split('\n') if line.strip()]
            if not lines:
                return None

            result = {
                "description": "",
                "position": "",
                "caption": ""
            }

            for line in lines:
                if line.lower().startswith("position:"):
                    result["position"] = line.split(":", 1)[1].strip()
                elif line.lower().startswith("caption:"):
                    result["caption"] = line.split(":", 1)[1].strip()
                else:
                    if not result["description"]:
                        result["description"] = line

            return result
        except Exception as e:
            logger.error(f"Error parsing image description: {str(e)}")
            return None


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


@lru_cache(maxsize=100)
def process_pdf(file_id: str):
    """Process a PDF file with caching.

    Args:
        file_id: ID of the PDF file to process

    Returns:
        Dict[str, Any]: Processing results
    """
    try:
        # Initialize service if needed
        service = PDFExtractionService()

        # Process the PDF
        request = {"file_id": file_id}
        results = asyncio.run(service.process(request))

        return results

    except Exception as e:
        logger.error(f"Failed to process PDF {file_id}: {str(e)}")
        return {"status": "error", "error": str(e), "service": "pdf_extraction"}
