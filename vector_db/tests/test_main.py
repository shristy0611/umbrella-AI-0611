import pytest
from fastapi.testclient import TestClient
from ..src.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "index_size" in response.json()
    assert response.json()["status"] == "healthy"

def test_add_vector():
    test_data = {
        "text": "This is a test document",
        "metadata": {"source": "test"}
    }
    response = client.post("/vectors/add", json=test_data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_search_vectors():
    # First add a vector
    test_data = {
        "text": "This is a sample document about machine learning",
        "metadata": {"source": "test"}
    }
    client.post("/vectors/add", json=test_data)
    
    # Then search for similar vectors
    search_query = {
        "query": "Tell me about machine learning",
        "k": 3
    }
    response = client.post("/vectors/search", json=search_query)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "results" in response.json()
    assert len(response.json()["results"]) <= search_query["k"]

def test_invalid_search_request():
    search_query = {
        "query": "",  # Empty query should fail
        "k": 3
    }
    response = client.post("/vectors/search", json=search_query)
    assert response.status_code == 422  # Validation error

def test_invalid_add_request():
    test_data = {
        "text": "",  # Empty text should fail
        "metadata": {"source": "test"}
    }
    response = client.post("/vectors/add", json=test_data)
    assert response.status_code == 422  # Validation error 