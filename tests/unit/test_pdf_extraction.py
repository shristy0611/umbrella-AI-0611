import pytest
from pathlib import Path
import base64
from unittest.mock import Mock, patch
from pdf_extraction_service.src.pdf_extractor import PDFExtractor
from shared.base_service import BaseService

# Test data directory
TEST_DATA_DIR = Path(__file__).parent.parent / "data"

@pytest.fixture
def pdf_extractor():
    return PDFExtractor()

@pytest.fixture
def sample_pdf_path():
    return TEST_DATA_DIR / "sample.pdf"

@pytest.fixture
def sample_pdf_bytes(sample_pdf_path):
    with open(sample_pdf_path, "rb") as f:
        return f.read()

@pytest.fixture
def sample_pdf_base64(sample_pdf_bytes):
    return base64.b64encode(sample_pdf_bytes).decode()

def test_extract_text_from_pdf_bytes(pdf_extractor, sample_pdf_bytes):
    """Test extracting text from PDF bytes."""
    result = pdf_extractor.extract_text(sample_pdf_bytes)
    
    assert isinstance(result, dict)
    assert "text" in result
    assert isinstance(result["text"], str)
    assert len(result["text"]) > 0
    assert "metadata" in result
    assert isinstance(result["metadata"], dict)
    assert "page_count" in result["metadata"]
    assert result["metadata"]["page_count"] > 0

def test_extract_text_from_base64(pdf_extractor, sample_pdf_base64):
    """Test extracting text from base64-encoded PDF."""
    result = pdf_extractor.extract_text_from_base64(sample_pdf_base64)
    
    assert isinstance(result, dict)
    assert "text" in result
    assert isinstance(result["text"], str)
    assert len(result["text"]) > 0

def test_extract_text_with_invalid_pdf():
    """Test handling of invalid PDF data."""
    extractor = PDFExtractor()
    invalid_bytes = b"not a pdf"
    
    with pytest.raises(ValueError) as exc_info:
        extractor.extract_text(invalid_bytes)
    assert "Invalid PDF" in str(exc_info.value)

def test_extract_text_with_empty_pdf():
    """Test handling of empty PDF."""
    extractor = PDFExtractor()
    empty_pdf = b"%PDF-1.4\n%EOF"
    
    result = extractor.extract_text(empty_pdf)
    assert result["text"] == ""
    assert result["metadata"]["page_count"] == 0

@pytest.mark.asyncio
async def test_process_request_with_valid_pdf(pdf_extractor, sample_pdf_base64):
    """Test processing a valid PDF request through the service interface."""
    request_data = {
        "file": sample_pdf_base64,
        "options": {
            "include_metadata": True
        }
    }
    
    result = await pdf_extractor.process_request(request_data)
    
    assert isinstance(result, dict)
    assert "text" in result
    assert "metadata" in result
    assert len(result["text"]) > 0
    assert result["metadata"]["page_count"] > 0

@pytest.mark.asyncio
async def test_process_request_with_invalid_base64():
    """Test processing request with invalid base64 data."""
    extractor = PDFExtractor()
    request_data = {
        "file": "invalid base64",
        "options": {}
    }
    
    with pytest.raises(ValueError) as exc_info:
        await extractor.process_request(request_data)
    assert "Invalid base64" in str(exc_info.value)

@pytest.mark.asyncio
async def test_process_request_with_missing_file():
    """Test processing request with missing file data."""
    extractor = PDFExtractor()
    request_data = {
        "options": {}
    }
    
    with pytest.raises(ValueError) as exc_info:
        await extractor.process_request(request_data)
    assert "Missing file" in str(exc_info.value)

def test_extract_text_with_ocr(pdf_extractor, sample_pdf_bytes):
    """Test text extraction with OCR enabled."""
    result = pdf_extractor.extract_text(sample_pdf_bytes, use_ocr=True)
    
    assert isinstance(result, dict)
    assert "text" in result
    assert len(result["text"]) > 0
    assert "ocr_applied" in result["metadata"]
    assert isinstance(result["metadata"]["ocr_applied"], bool)

def test_extract_text_with_password_protected_pdf():
    """Test handling of password-protected PDFs."""
    extractor = PDFExtractor()
    
    # Create a real encrypted PDF
    encrypted_pdf = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<</Type/Catalog/Pages 2 0 R/Encrypt 3 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Kids[]/Count 0>>\nendobj\n3 0 obj\n<</Filter/Standard/V 2/Length 128/R 3/P -3904/O<1234567890ABCDEF1234567890ABCDEF>/U<1234567890ABCDEF1234567890ABCDEF>>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000015 00000 n\n0000000074 00000 n\n0000000120 00000 n\ntrailer\n<</Root 1 0 R/Encrypt 3 0 R/ID[<1234567890ABCDEF1234567890ABCDEF><1234567890ABCDEF1234567890ABCDEF>]/Size 4>>\nstartxref\n231\n%%EOF'
    
    with pytest.raises(ValueError) as exc_info:
        extractor.extract_text(encrypted_pdf, password="wrong")
    assert "password" in str(exc_info.value).lower()

@pytest.mark.asyncio
async def test_batch_processing(pdf_extractor, sample_pdf_base64):
    """Test batch processing of multiple PDFs."""
    request_data = {
        "files": [
            {"id": "1", "content": sample_pdf_base64},
            {"id": "2", "content": sample_pdf_base64}
        ],
        "options": {
            "include_metadata": True
        }
    }
    
    result = await pdf_extractor.process_batch_request(request_data)
    
    assert isinstance(result, list)
    assert len(result) == 2
    for item in result:
        assert "id" in item
        assert "text" in item
        assert "metadata" in item
        assert len(item["text"]) > 0 