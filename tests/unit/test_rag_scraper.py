import pytest
from unittest.mock import AsyncMock, patch
from rag_scraper_service.src.scraper import RAGScraper
import asyncio

@pytest.fixture
def rag_scraper():
    return RAGScraper()

@pytest.fixture
def mock_response():
    mock = AsyncMock()
    mock.status = 200
    mock.text = AsyncMock(return_value="""
        <html>
            <h1>Test Page</h1>
            <p>Test content</p>
            <a href="http://test.com/page1">Link 1</a>
            <a href="http://test.com/page2">Link 2</a>
        </html>
    """)
    return mock

@pytest.fixture
def sample_html():
    """Sample HTML content for testing."""
    return """
    <html>
        <h1>Test Page</h1>
        <p>This is a test paragraph.</p>
        <article>Article content here.</article>
    </html>
    """

@pytest.mark.asyncio
async def test_scrape_single_page(rag_scraper, mock_response):
    """Test scraping a single page."""
    url = "http://test.com"
    
    async def mock_get(*args, **kwargs):
        return mock_response
    
    with patch("aiohttp.ClientSession.get", side_effect=mock_get):
        result = await rag_scraper.scrape_page(url)
        
        assert isinstance(result, dict)
        assert "url" in result
        assert "content" in result
        assert "links" in result
        assert len(result["links"]) == 2

@pytest.mark.asyncio
async def test_scrape_with_custom_selectors(rag_scraper, mock_response):
    """Test scraping with custom CSS selectors."""
    url = "http://test.com"
    selectors = ["h1"]
    
    async def mock_get(*args, **kwargs):
        return mock_response
    
    with patch("aiohttp.ClientSession.get", side_effect=mock_get):
        result = await rag_scraper.scrape_page(url, selectors=selectors)
        
        assert "Test Page" in result["content"]
        assert "Test content" not in result["content"]

@pytest.mark.asyncio
async def test_scrape_with_max_depth(rag_scraper):
    """Test recursive scraping with max depth."""
    base_url = "http://test.com"
    mock_responses = {
        "http://test.com": AsyncMock(
            status=200,
            text=AsyncMock(return_value="""
                <html>
                    <a href="/page1">Link 1</a>
                    <a href="/page2">Link 2</a>
                    <p>Base content</p>
                </html>
            """)
        ),
        "http://test.com/page1": AsyncMock(
            status=200,
            text=AsyncMock(return_value="<html><p>Page 1 content</p></html>")
        ),
        "http://test.com/page2": AsyncMock(
            status=200,
            text=AsyncMock(return_value="<html><p>Page 2 content</p></html>")
        )
    }
    
    async def mock_get(url, **kwargs):
        if url in mock_responses:
            return mock_responses[url]
        return AsyncMock(status=404)
    
    with patch("aiohttp.ClientSession.get", side_effect=mock_get):
        result = await rag_scraper.scrape_recursive(base_url, max_depth=1)
        
        assert isinstance(result, list)
        assert len(result) == 3  # Base page + 2 linked pages

@pytest.mark.asyncio
async def test_handle_http_errors(rag_scraper):
    """Test handling of HTTP errors."""
    url = "http://test.com"
    mock_404 = AsyncMock()
    mock_404.status = 404
    
    async def mock_get(*args, **kwargs):
        return mock_404
    
    with patch("aiohttp.ClientSession.get", side_effect=mock_get):
        with pytest.raises(ValueError) as exc_info:
            await rag_scraper.scrape_page(url)
        assert "HTTP 404" in str(exc_info.value)

@pytest.mark.asyncio
async def test_handle_timeout(rag_scraper):
    """Test handling of request timeouts."""
    url = "http://test.com"
    
    async def mock_timeout(*args, **kwargs):
        raise asyncio.TimeoutError()
    
    with patch("aiohttp.ClientSession.get", side_effect=mock_timeout):
        with pytest.raises(TimeoutError):
            await rag_scraper.scrape_page(url)

@pytest.mark.asyncio
async def test_content_cleaning(rag_scraper, mock_response):
    """Test content cleaning and formatting."""
    url = "http://test.com"
    mock_response.text = AsyncMock(return_value="""
        <html>
            <p>  Multiple    spaces   </p>
            <p>Special@#$characters</p>
        </html>
    """)
    
    async def mock_get(*args, **kwargs):
        return mock_response
    
    with patch("aiohttp.ClientSession.get", side_effect=mock_get):
        result = await rag_scraper.scrape_page(url)
        
        assert "Multiple spaces" in result["content"]
        assert "Specialcharacters" in result["content"]

@pytest.mark.asyncio
async def test_process_request_with_valid_url(rag_scraper, mock_response):
    """Test processing a request with a valid URL."""
    request_data = {
        "urls": [
            {"id": "1", "url": "http://test.com"}
        ]
    }
    
    async def mock_get(*args, **kwargs):
        return mock_response
    
    with patch("aiohttp.ClientSession.get", side_effect=mock_get):
        result = await rag_scraper.process_batch_request(request_data)
        
        assert len(result) == 1
        assert result[0]["id"] == "1"
        assert result[0]["success"] is True
        assert "content" in result[0]

@pytest.mark.asyncio
async def test_process_request_with_missing_url(rag_scraper):
    """Test processing a request with a missing URL."""
    request_data = {
        "urls": [
            {"id": "1"}  # Missing URL
        ]
    }
    
    result = await rag_scraper.process_batch_request(request_data)
    
    assert len(result) == 1
    assert result[0]["id"] == "1"
    assert result[0]["success"] is False
    assert "error" in result[0]

@pytest.mark.asyncio
async def test_batch_scraping(rag_scraper, mock_response):
    """Test batch scraping of multiple URLs."""
    request_data = {
        "urls": [
            {"id": "1", "url": "http://test1.com"},
            {"id": "2", "url": "http://test2.com"}
        ],
        "options": {
            "max_depth": 0
        }
    }
    
    async def mock_get(*args, **kwargs):
        return mock_response
    
    with patch("aiohttp.ClientSession.get", side_effect=mock_get):
        result = await rag_scraper.process_batch_request(request_data)
        
        assert isinstance(result, list)
        assert len(result) == 2
        for item in result:
            assert "id" in item
            assert "content" in item
            assert item["success"] is True 