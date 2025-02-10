import pytest
from fastapi.testclient import TestClient
from ..src.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "service" in response.json()
    assert response.json()["service"] == "sentiment_analysis"

def test_analyze_sentiment_empty_text():
    request_data = {
        "text": "",
        "metadata": {"source": "test"}
    }
    response = client.post("/analyze", json=request_data)
    assert response.status_code == 400
    assert "Text cannot be empty" in response.json()["detail"]

def test_analyze_sentiment_valid_text():
    request_data = {
        "text": "This is a great test! I'm very happy.",
        "metadata": {"source": "test"}
    }
    response = client.post("/analyze", json=request_data)
    assert response.status_code == 200
    assert "sentiment" in response.json()
    assert "score" in response.json()
    assert isinstance(response.json()["score"], float)
    assert response.json()["score"] >= 0 and response.json()["score"] <= 1 