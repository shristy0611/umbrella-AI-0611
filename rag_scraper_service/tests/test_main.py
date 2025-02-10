import pytest
from fastapi.testclient import TestClient
from ..src.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert "service" in response.json()
    assert "vector_db" in response.json()
    assert "playwright" in response.json()

def test_scrape_invalid_url():
    request_data = {
        "url": "not-a-valid-url",
        "max_depth": 1,
        "max_pages": 1
    }
    response = client.post("/scrape", json=request_data)
    assert response.status_code == 422  # Validation error for invalid URL

def test_scrape_with_selectors():
    request_data = {
        "url": "http://example.com",
        "max_depth": 1,
        "max_pages": 1,
        "selectors": ["h1", "p"],
        "exclude_patterns": ["*blog*", "*archive*"]
    }
    response = client.post("/scrape", json=request_data)
    assert response.status_code == 200
    assert "content" in response.json()
    assert "metadata" in response.json()
    assert "discovered_urls" in response.json()
    assert isinstance(response.json()["content"], dict)
    assert isinstance(response.json()["discovered_urls"], list) 