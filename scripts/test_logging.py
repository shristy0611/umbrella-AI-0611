#!/usr/bin/env python3
import asyncio
import httpx
import uuid
from typing import List, Dict

async def simulate_workflow(base_urls: Dict[str, str], correlation_id: str = None):
    """
    Simulate a workflow across multiple services with correlation ID tracking.
    
    Args:
        base_urls: Dictionary mapping service names to their base URLs
        correlation_id: Optional correlation ID to use (will generate if not provided)
    """
    # Generate correlation ID if not provided
    correlation_id = correlation_id or str(uuid.uuid4())
    headers = {"X-Correlation-ID": correlation_id}
    
    async with httpx.AsyncClient() as client:
        try:
            print(f"\nStarting workflow with correlation_id: {correlation_id}")
            
            # 1. Call orchestrator to decompose task
            print("\n1. Calling orchestrator service...")
            response = await client.post(
                f"{base_urls['orchestrator']}/decompose",
                headers=headers,
                json={
                    "task_type": "document_analysis",
                    "content": {"file": "test.pdf"}
                }
            )
            response.raise_for_status()
            task_decomposition = response.json()
            print(f"Task decomposed into {len(task_decomposition['tasks'])} subtasks")
            
            # 2. Call PDF extraction service
            print("\n2. Calling PDF extraction service...")
            response = await client.post(
                f"{base_urls['pdf_extraction']}/extract",
                headers=headers,
                json={"file": "test.pdf"}
            )
            response.raise_for_status()
            extracted_text = response.json()
            print("PDF text extracted successfully")
            
            # 3. Call sentiment analysis service
            print("\n3. Calling sentiment analysis service...")
            response = await client.post(
                f"{base_urls['sentiment']}/analyze",
                headers=headers,
                json={"text": extracted_text["text"]}
            )
            response.raise_for_status()
            sentiment_result = response.json()
            print(f"Sentiment analysis completed: {sentiment_result['sentiment']}")
            
            # 4. Store results in vector DB
            print("\n4. Storing results in vector DB...")
            response = await client.post(
                f"{base_urls['vector_db']}/store",
                headers=headers,
                json={
                    "text": extracted_text["text"],
                    "metadata": {
                        "sentiment": sentiment_result["sentiment"],
                        "source": "document_analysis"
                    }
                }
            )
            response.raise_for_status()
            print("Results stored successfully")
            
            print(f"\nWorkflow completed successfully. Check logs for correlation_id: {correlation_id}")
            
        except httpx.HTTPError as e:
            print(f"Error during workflow: {str(e)}")
            raise

async def main():
    # Service URLs (adjust as needed)
    base_urls = {
        "orchestrator": "http://localhost:8000",
        "pdf_extraction": "http://localhost:8001",
        "sentiment": "http://localhost:8002",
        "vector_db": "http://localhost:8003"
    }
    
    # Run workflow with a specific correlation ID
    await simulate_workflow(base_urls, "test-workflow-1")
    
    # Run another workflow with auto-generated correlation ID
    await simulate_workflow(base_urls)

if __name__ == "__main__":
    asyncio.run(main()) 