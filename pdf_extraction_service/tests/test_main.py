import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
import io
from PIL import Image
from ..src.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_env():
    """Set up mock environment variables."""
    with patch.dict(os.environ, {
        "GEMINI_API_KEY_OCR": "test-key",
        "PDF_SERVICE_URL": "http://pdf_service:8001"
    }):
        yield

@pytest.fixture
def mock_pdf_image():
    """Create a mock PDF image for testing."""
    img = Image.new('RGB', (100, 100), color='white')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    return img_byte_arr.getvalue()

@pytest.fixture
def mock_gemini():
    """Mock Gemini API responses"""
    with patch('google.generativeai.GenerativeModel') as mock:
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = MagicMock(
            text=str({
                "text": "Sample extracted text",
                "insights": ["Key point 1", "Key point 2"],
                "structure": "Document structure details"
            })
        )
        mock.return_value = mock_instance
        yield mock

def test_health_check(mock_gemini):
    """Test health check endpoint when Gemini API is healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "pdf_extraction"
    assert "dependencies" in response.json()

def test_extract_pdf_success(mock_env, mock_pdf_image, mock_gemini):
    """Test successful PDF extraction with Gemini API."""
    with patch('pdf2image.convert_from_path') as mock_convert:
        # Mock PDF to image conversion
        mock_image = MagicMock()
        mock_image.save.side_effect = lambda f, format: f.write(mock_pdf_image)
        mock_convert.return_value = [mock_image]
        
        # Create test PDF file
        files = {"file": ("test.pdf", b"test pdf content", "application/pdf")}
        response = client.post("/extract", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert "Sample extracted text" in str(data["text"])
        assert data["pages"] == 1
        assert "insights" in data["analysis"]
        assert "structure" in data["analysis"]

def test_extract_pdf_invalid_file():
    """Test PDF extraction with invalid file type."""
    files = {"file": ("test.txt", b"test content", "text/plain")}
    response = client.post("/extract", files=files)
    assert response.status_code == 400
    assert "File must be a PDF" in response.json()["detail"]

def test_extract_pdf_gemini_error(mock_env, mock_pdf_image):
    """Test PDF extraction when Gemini API fails."""
    with patch('pdf2image.convert_from_path') as mock_convert, \
         patch('google.generativeai.GenerativeModel.generate_content') as mock_generate:
        
        # Mock PDF to image conversion
        mock_image = MagicMock()
        mock_image.save.side_effect = lambda f, format: f.write(mock_pdf_image)
        mock_convert.return_value = [mock_image]
        
        # Mock Gemini API error
        mock_generate.side_effect = Exception("Gemini API Error")
        
        # Create test PDF file
        files = {"file": ("test.pdf", b"test pdf content", "application/pdf")}
        response = client.post("/extract", files=files)
        
        assert response.status_code == 500
        assert "Error processing PDF file" in response.json()["detail"] 