"""End-to-end tests for complete user scenarios."""

import pytest
import asyncio
import os
from fastapi.testclient import TestClient
from PIL import Image
import json
from datetime import datetime

# Import main application
from orchestrator_service.src.main import app as orchestrator_app
from pdf_extraction_service.src.main import app as pdf_app
from sentiment_service.src.main import app as sentiment_app
from vector_db.src.main import app as vector_db_app
from rag_scraper_service.src.main import app as scraper_app
from chatbot_service.src.main import app as chatbot_app

@pytest.fixture
def sample_pdf():
    """Load sample PDF for testing."""
    pdf_path = os.path.join("tests", "data", "documents", "sample.pdf")
    if not os.path.exists(pdf_path):
        pytest.skip("Sample PDF not found")
    return pdf_path

@pytest.fixture
def clients():
    """Create test clients for all services."""
    return {
        "orchestrator": TestClient(orchestrator_app),
        "pdf": TestClient(pdf_app),
        "sentiment": TestClient(sentiment_app),
        "vector_db": TestClient(vector_db_app),
        "scraper": TestClient(scraper_app),
        "chatbot": TestClient(chatbot_app)
    }

@pytest.mark.e2e
def test_document_analysis_scenario(clients, sample_pdf):
    """Test complete document analysis scenario.
    
    This test simulates a user:
    1. Uploading a PDF invoice
    2. Getting text extraction
    3. Receiving sentiment analysis
    4. Getting relevant recommendations
    5. Interacting with the chatbot about results
    """
    # Step 1: Submit document for analysis
    with open(sample_pdf, "rb") as f:
        response = clients["orchestrator"].post(
            "/process",
            json={
                "task_type": "document_analysis",
                "content": {
                    "file": f.read().decode(),
                    "analysis_type": "full",
                    "include_sentiment": True
                }
            }
        )
    
    assert response.status_code == 200, "Document submission should succeed"
    task_id = response.json()["task_id"]
    
    # Step 2: Wait for processing to complete
    max_retries = 10
    status = "processing"
    results = None
    
    for _ in range(max_retries):
        status_response = clients["orchestrator"].get(f"/task/{task_id}/status")
        status = status_response.json()["status"]
        if status == "completed":
            results = clients["orchestrator"].get(f"/task/{task_id}/results").json()
            break
        elif status == "failed":
            pytest.fail("Task processing failed")
        asyncio.sleep(1)
    
    assert results is not None, "Should receive analysis results"
    assert "extracted_text" in results, "Should include extracted text"
    assert "sentiment" in results, "Should include sentiment analysis"
    
    # Step 3: Verify text extraction quality
    assert len(results["extracted_text"]) > 0, "Should extract meaningful text"
    assert "key_points" in results, "Should identify key points"
    
    # Step 4: Verify sentiment analysis
    sentiment = results["sentiment"]
    assert "score" in sentiment, "Should include sentiment score"
    assert "label" in sentiment, "Should include sentiment label"
    
    # Step 5: Chat about results
    chat_response = clients["chatbot"].post(
        "/chat",
        json={
            "message": "Summarize the document analysis results",
            "context": results,
            "session_id": f"test_session_{task_id}"
        }
    )
    
    assert chat_response.status_code == 200, "Chat should succeed"
    assert "response" in chat_response.json(), "Should receive chat response"

@pytest.mark.e2e
def test_web_research_scenario(clients):
    """Test complete web research scenario.
    
    This test simulates a user:
    1. Requesting web research on a topic
    2. Getting scraped content
    3. Receiving analysis and insights
    4. Storing results in vector DB
    5. Querying related information
    """
    # Step 1: Submit research request
    response = clients["orchestrator"].post(
        "/process",
        json={
            "task_type": "web_research",
            "content": {
                "query": "artificial intelligence latest developments",
                "max_depth": 2,
                "max_pages": 5
            }
        }
    )
    
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    
    # Step 2: Wait for research completion
    max_retries = 15
    results = None
    
    for _ in range(max_retries):
        status_response = clients["orchestrator"].get(f"/task/{task_id}/status")
        status = status_response.json()["status"]
        if status == "completed":
            results = clients["orchestrator"].get(f"/task/{task_id}/results").json()
            break
        elif status == "failed":
            pytest.fail("Research task failed")
        asyncio.sleep(2)
    
    assert results is not None, "Should receive research results"
    assert "scraped_content" in results, "Should include scraped content"
    assert "insights" in results, "Should include research insights"
    
    # Step 3: Verify content is stored in vector DB
    vector_id = results.get("vector_id")
    assert vector_id, "Content should be stored in vector DB"
    
    # Step 4: Search related information
    search_response = clients["vector_db"].post(
        "/vectors/search",
        json={
            "query": "AI applications",
            "k": 3
        }
    )
    
    assert search_response.status_code == 200, "Vector search should succeed"
    assert len(search_response.json()["results"]) > 0, "Should find related content"

@pytest.mark.e2e
def test_interactive_analysis_scenario(clients, sample_pdf):
    """Test interactive analysis scenario.
    
    This test simulates a user:
    1. Starting with document analysis
    2. Asking follow-up questions
    3. Requesting additional research
    4. Getting comprehensive insights
    """
    # Step 1: Initial document analysis
    with open(sample_pdf, "rb") as f:
        doc_response = clients["orchestrator"].post(
            "/process",
            json={
                "task_type": "document_analysis",
                "content": {
                    "file": f.read().decode(),
                    "analysis_type": "basic"
                }
            }
        )
    
    task_id = doc_response.json()["task_id"]
    
    # Wait for initial analysis
    results = None
    for _ in range(10):
        status = clients["orchestrator"].get(f"/task/{task_id}/status").json()
        if status["status"] == "completed":
            results = clients["orchestrator"].get(f"/task/{task_id}/results").json()
            break
        asyncio.sleep(1)
    
    assert results is not None, "Should complete initial analysis"
    
    # Step 2: Start chat session
    chat_response = clients["chatbot"].post(
        "/chat",
        json={
            "message": "What are the main points in this document?",
            "session_id": f"test_session_{task_id}",
            "context": results
        }
    )
    
    assert chat_response.status_code == 200, "Should get chat response"
    session_id = chat_response.json()["session_id"]
    
    # Step 3: Request additional research
    research_response = clients["orchestrator"].post(
        "/process",
        json={
            "task_type": "web_research",
            "content": {
                "query": "Related to: " + results["extracted_text"][:100],
                "max_pages": 3
            },
            "context": {
                "original_task_id": task_id
            }
        }
    )
    
    assert research_response.status_code == 200, "Should initiate research"
    
    # Step 4: Get comprehensive insights
    final_response = clients["chatbot"].post(
        "/chat",
        json={
            "message": "Provide a comprehensive analysis combining the document and research",
            "session_id": session_id,
            "context": {
                "document_results": results,
                "research_task_id": research_response.json()["task_id"]
            }
        }
    )
    
    assert final_response.status_code == 200, "Should get final analysis"
    assert len(final_response.json()["response"]) > 0, "Should receive meaningful insights"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--capture=no"]) 