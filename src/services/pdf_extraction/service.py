"""PDF extraction service for UMBRELLA-AI."""

import os
import base64
import logging
from typing import Dict, Any, List, Optional
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io
import json
from src.shared.base_service import BaseService
from src.shared.api_config import api_config
from datetime import datetime
from fastapi import APIRouter
from functools import lru_cache
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()

class PDFExtractionService(BaseService):
    """Service for extracting text and information from PDFs using Gemini."""
    
    def __init__(self):
        """Initialize the PDF extraction service."""
        super().__init__("pdf_extraction")
        self.model = None
        
    async def initialize(self) -> None:
        """Initialize the service and configure Gemini API."""
        try:
            # Initialize API configuration
            await api_config.initialize()
            
            # Get API key for OCR service
            api_key = await api_config.get_api_key("OCR")
            
            # Configure Gemini
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            
            self._initialized = True
            logger.info("PDF extraction service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize PDF extraction service: {str(e)}")
            raise
        
    async def cleanup(self) -> None:
        """Clean up service resources."""
        self.model = None
        await super().cleanup()
        
    async def validate_request(self, request: Dict[str, Any]) -> bool:
        """Validate extraction request.
        
        Args:
            request: Request to validate
            
        Returns:
            bool: True if request is valid
        """
        if "file_id" not in request and "pdf_data" not in request:
            return False
        return True
    
    async def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a PDF extraction request.
        
        Args:
            request: Dictionary containing:
                - pdf_data: PDF content in base64 or file path
                - extract_text: Whether to extract text
                - extract_tables: Whether to extract tables
                - extract_images: Whether to extract images
                
        Returns:
            Dict[str, Any]: Extraction results
            
        Raises:
            ValueError: If request is invalid or processing fails
        """
        try:
            # Get PDF data
            pdf_data = await self._get_pdf_data(request.get("file_id"))
            
            # Extract text using Gemini with retry
            text = await api_config.execute_with_retry(
                self._extract_text_with_gemini,
                pdf_data,
                request.get("extract_tables", True),
                request.get("extract_images", True)
            )
            
            return {
                "status": "success",
                "text": text,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "service": self.service_name
                }
            }
            
        except Exception as e:
            logger.error(f"PDF extraction failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "service": self.service_name
            }
    
    async def _get_pdf_data(self, file_id: str) -> bytes:
        """Get PDF data from storage.
        
        Args:
            file_id: File ID
            
        Returns:
            bytes: PDF data
            
        Raises:
            ValueError: If file not found
        """
        # TODO: Implement storage service integration
        raise NotImplementedError("Storage service not implemented")
    
    def _extract_metadata(self, pdf_document: fitz.Document) -> Dict[str, Any]:
        """Extract PDF metadata.
        
        Args:
            pdf_document: PDF document
            
        Returns:
            Dict[str, Any]: Metadata
        """
        metadata = pdf_document.metadata
        return {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "keywords": metadata.get("keywords", ""),
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "creation_date": metadata.get("creationDate", ""),
            "modification_date": metadata.get("modDate", ""),
            "page_count": len(pdf_document)
        }
    
    async def _process_page(
        self,
        page: fitz.Page,
        extract_tables: bool = True,
        extract_images: bool = True
    ) -> Dict[str, Any]:
        """Process a PDF page.
        
        Args:
            page: PDF page
            extract_tables: Whether to extract tables
            extract_images: Whether to extract images
            
        Returns:
            Dict[str, Any]: Page extraction results
        """
        results = {
            "number": page.number + 1,
            "text": page.get_text(),
            "tables": [],
            "images": []
        }
        
        # Extract tables if requested
        if extract_tables:
            results["tables"] = await self._extract_tables(page)
        
        # Extract images if requested
        if extract_images:
            results["images"] = await self._extract_images(page)
        
        return results
    
    async def _extract_tables(self, page: fitz.Page) -> List[List[List[str]]]:
        """Extract tables from a page.
        
        Args:
            page: PDF page
            
        Returns:
            List[List[List[str]]]: Extracted tables
        """
        tables = []
        
        # Find table-like structures
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block.get("type") == 1:  # Table block
                table = []
                for line in block["lines"]:
                    row = []
                    for span in line["spans"]:
                        row.append(span["text"])
                    table.append(row)
                tables.append(table)
        
        return tables
    
    async def _extract_images(self, page: fitz.Page) -> List[Dict[str, Any]]:
        """Extract images from a page.
        
        Args:
            page: PDF page
            
        Returns:
            List[Dict[str, Any]]: Extracted images
        """
        images = []
        
        # Get image list
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = page.parent.extract_image(xref)
            
            if base_image:
                image_data = base_image["image"]
                image_ext = base_image["ext"]
                
                # Convert to base64
                image_b64 = base64.b64encode(image_data).decode()
                
                images.append({
                    "index": img_index,
                    "format": image_ext,
                    "data": image_b64,
                    "width": base_image.get("width"),
                    "height": base_image.get("height")
                })
        
        return images
    
    async def _analyze_image_content(self, image_data: bytes) -> str:
        """Analyze image content using Gemini.
        
        Args:
            image_data: Raw image data
            
        Returns:
            str: Image content description
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Create prompt
            prompt = "Describe the content of this image in detail."
            
            # Generate content
            response = await self.model.generate_content([prompt, image])
            
            return response.text.strip()
            
        except Exception as e:
            return f"Failed to analyze image: {str(e)}"
        
    async def _extract_text_with_gemini(
        self,
        pdf_data: bytes,
        extract_tables: bool = True,
        extract_images: bool = True
    ) -> str:
        """Extract text from PDF using Gemini.
        
        Args:
            pdf_data: Raw PDF data
            extract_tables: Whether to extract tables
            extract_images: Whether to extract image content
            
        Returns:
            str: Extracted text
        """
        # Convert PDF to image for Gemini
        images = self._pdf_to_images(pdf_data)
        
        # Process each page with Gemini
        results = []
        for image in images:
            prompt = self._build_extraction_prompt(
                extract_tables=extract_tables,
                extract_images=extract_images
            )
            
            response = await self.model.generate_content(
                [prompt, image],
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "top_k": 40
                }
            )
            
            results.append(response.text)
            
        return "\n\n".join(results)
        
    def _pdf_to_images(self, pdf_data: bytes) -> List[Any]:
        """Convert PDF pages to images.
        
        Args:
            pdf_data: Raw PDF data
            
        Returns:
            List[Any]: List of images
        """
        # TODO: Implement PDF to image conversion
        # For now, return dummy image
        return [pdf_data]
        
    def _build_extraction_prompt(
        self,
        extract_tables: bool = True,
        extract_images: bool = True
    ) -> str:
        """Build the extraction prompt for Gemini.
        
        Args:
            extract_tables: Whether to extract tables
            extract_images: Whether to extract image content
            
        Returns:
            str: Extraction prompt
        """
        prompt = "Extract all text content from this PDF page."
        
        if extract_tables:
            prompt += " Include any tables and their contents."
            
        if extract_images:
            prompt += " Describe any images or figures."
            
        prompt += " Maintain the original formatting and structure."
        
        return prompt 

@router.get('/health')
async def health_check():
    return {'status': 'healthy'}

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
        return {
            "status": "error",
            "error": str(e),
            "service": "pdf_extraction"
        }