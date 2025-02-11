"""Tests for the PDF extraction service."""

import base64
import pytest
import pytest_asyncio
import os
from src.services.pdf_extraction.service import PDFExtractionService

@pytest_asyncio.fixture
async def pdf_service():
    """Create and initialize a PDF extraction service."""
    service = PDFExtractionService()
    await service.initialize()
    return service

@pytest.fixture
def sample_pdf_data():
    """Load sample PDF data."""
    pdf_path = os.path.join("test_data", "sample.pdf")
    with open(pdf_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

@pytest.mark.asyncio
async def test_service_initialization():
    """Test that the service initializes correctly."""
    service = PDFExtractionService()
    await service.initialize()
    assert service._initialized
    assert service.model is not None

@pytest.mark.asyncio
async def test_validate_request(pdf_service, sample_pdf_data):
    """Test request validation."""
    # Valid request
    valid_request = {"pdf_data": sample_pdf_data}
    assert await pdf_service.validate_request(valid_request)

    # Invalid request - missing pdf_data
    invalid_request = {}
    assert not await pdf_service.validate_request(invalid_request)

    # Invalid request - invalid base64
    invalid_request = {"pdf_data": "invalid_base64"}
    assert not await pdf_service.validate_request(invalid_request)

@pytest.mark.asyncio
async def test_process_single_page(pdf_service, sample_pdf_data):
    """Test processing a single page PDF."""
    request = {
        "pdf_data": sample_pdf_data,
        "extract_text": True,
        "extract_tables": True,
        "extract_images": True
    }
    
    result = await pdf_service.process(request)
    
    # Check basic structure
    assert result["status"] == "success"
    assert "metadata" in result
    assert "pages" in result
    
    # Check metadata
    metadata = result["metadata"]
    assert "timestamp" in metadata
    assert metadata["service"] == "pdf_extraction"
    assert "page_count" in metadata
    
    # Check pages
    pages = result["pages"]
    assert len(pages) > 0
    
    # Check first page
    first_page = pages[0]
    assert "page_number" in first_page
    assert "text" in first_page
    assert "tables" in first_page
    assert "images" in first_page
    assert "page_info" in first_page
    
    # Verify page info
    page_info = first_page["page_info"]
    assert "width" in page_info
    assert "height" in page_info
    assert "rotation" in page_info
    assert "has_images" in page_info
    assert "has_links" in page_info

@pytest.mark.asyncio
async def test_process_with_page_selection(pdf_service, sample_pdf_data):
    """Test processing specific pages."""
    request = {
        "pdf_data": sample_pdf_data,
        "page_numbers": [0]  # Only process first page
    }
    
    result = await pdf_service.process(request)
    assert result["status"] == "success"
    assert len(result["pages"]) == 1
    assert result["pages"][0]["page_number"] == 1

@pytest.mark.asyncio
async def test_table_extraction(pdf_service, sample_pdf_data):
    """Test table extraction functionality."""
    request = {
        "pdf_data": sample_pdf_data,
        "extract_text": False,
        "extract_tables": True,
        "extract_images": False
    }
    
    result = await pdf_service.process(request)
    assert result["status"] == "success"
    
    # Check if any tables were found
    for page in result["pages"]:
        assert "tables" in page
        if page["tables"]:  # If tables were found
            table = page["tables"][0]
            assert "headers" in table
            assert "data" in table
            assert isinstance(table["headers"], list)
            assert isinstance(table["data"], list)

@pytest.mark.asyncio
async def test_error_handling(pdf_service):
    """Test error handling with invalid input."""
    # Test with invalid PDF data
    request = {
        "pdf_data": base64.b64encode(b"invalid pdf content").decode()
    }
    
    result = await pdf_service.process(request)
    assert result["status"] == "error"
    assert "error" in result
    assert "metadata" in result
    assert "timestamp" in result["metadata"]

@pytest.mark.asyncio
async def test_metadata_extraction(pdf_service, sample_pdf_data):
    """Test PDF metadata extraction."""
    request = {"pdf_data": sample_pdf_data}
    result = await pdf_service.process(request)
    
    metadata = result["metadata"]
    required_fields = [
        "title", "author", "subject", "keywords",
        "creator", "producer", "page_count", "file_size",
        "is_encrypted", "format", "version"
    ]
    
    for field in required_fields:
        assert field in metadata
        
    # Basic validations
    assert isinstance(metadata["page_count"], int)
    assert isinstance(metadata["file_size"], int)
    assert isinstance(metadata["is_encrypted"], bool)
    assert metadata["format"] == "PDF"
    assert metadata["version"] in ["Unknown", "1.4"]  # Our test PDF is 1.4, but allow Unknown 