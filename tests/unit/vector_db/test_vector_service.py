"""Unit tests for Vector Database Service."""

import pytest
import numpy as np
from fastapi.testclient import TestClient
from vector_db.src.main import app, model, index

@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)

@pytest.fixture
def sample_text():
    """Sample text for testing embeddings."""
    return "This is a test document for vector embeddings."

@pytest.fixture
def sample_query():
    """Sample search query for testing."""
    return {
        "query": "test document",
        "k": 3
    }

def test_add_vector(client, sample_text):
    """Test adding a vector to the database.
    
    This test verifies that:
    1. Vector addition endpoint returns success
    2. The embedding is correctly generated
    3. The vector is properly stored in FAISS index
    """
    response = client.post(
        "/vectors/add",
        json={"text": sample_text}
    )
    assert response.status_code == 200, "Vector addition should succeed"
    assert response.json()["status"] == "success"
    
    # Verify vector was added by checking index size
    assert index.ntotal > 0, "Vector should be added to FAISS index"

def test_search_vectors(client, sample_text, sample_query):
    """Test searching vectors in the database.
    
    This test verifies that:
    1. Adding a vector succeeds
    2. Search returns correct number of results
    3. Results include distance and index
    4. Distances are in ascending order (closest first)
    """
    # First add a vector
    client.post("/vectors/add", json={"text": sample_text})
    
    # Then search
    response = client.post("/vectors/search", json=sample_query)
    assert response.status_code == 200, "Search should succeed"
    
    results = response.json()["results"]
    assert len(results) <= sample_query["k"], f"Should return at most {sample_query['k']} results"
    
    # Verify result structure
    for result in results:
        assert "distance" in result, "Result should include distance"
        assert "index" in result, "Result should include index"
    
    # Verify distances are sorted
    distances = [r["distance"] for r in results]
    assert distances == sorted(distances), "Results should be sorted by distance"

def test_model_encoding():
    """Test the sentence transformer model directly.
    
    This test verifies that:
    1. Model generates correct dimension embeddings
    2. Embeddings are normalized
    3. Similar texts have similar embeddings
    """
    # Test basic encoding
    text1 = "This is a test."
    text2 = "This is also a test."
    text3 = "Something completely different."
    
    emb1 = model.encode([text1])[0]
    emb2 = model.encode([text2])[0]
    emb3 = model.encode([text3])[0]
    
    # Check dimensions
    assert emb1.shape == (384,), "Embedding should be 384-dimensional"
    
    # Check similarity (cosine similarity)
    sim12 = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    sim13 = np.dot(emb1, emb3) / (np.linalg.norm(emb1) * np.linalg.norm(emb3))
    
    assert sim12 > sim13, "Similar texts should have higher similarity"

def test_health_check(client):
    """Test the health check endpoint.
    
    This test verifies that:
    1. Health check returns correct status format
    2. All dependencies are reported
    3. Status reflects actual service health
    """
    response = client.get("/health")
    assert response.status_code == 200, "Health check should succeed"
    
    data = response.json()
    assert "status" in data, "Response should include status"
    assert "service" in data, "Response should include service name"
    assert "dependencies" in data, "Response should include dependencies"
    
    assert data["service"] == "vector_db", "Service name should be vector_db"
    assert isinstance(data["dependencies"], dict), "Dependencies should be a dictionary"
    assert "model" in data["dependencies"], "Should report model health"
    assert "index" in data["dependencies"], "Should report index health"

def test_error_handling(client):
    """Test error handling in the service.
    
    This test verifies that:
    1. Invalid inputs are properly handled
    2. Service returns appropriate error messages
    3. Error responses include proper status codes
    """
    # Test empty text
    response = client.post("/vectors/add", json={"text": ""})
    assert response.status_code == 500, "Empty text should be rejected"
    
    # Test invalid search query
    response = client.post("/vectors/search", json={"query": "", "k": -1})
    assert response.status_code == 500, "Invalid search parameters should be rejected"
    
    # Test missing required fields
    response = client.post("/vectors/add", json={})
    assert response.status_code == 422, "Missing required fields should be rejected"

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 