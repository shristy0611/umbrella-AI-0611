import requests
import json
import pika
import websockets
import asyncio

# PDF Extraction Agent Test
def test_pdf_extraction():
    url = "http://localhost:8000/pdf-extract"
    data = {
        "file_path": "sample.pdf",
        "options": {
            "extract_text": True,
            "extract_images": False
        }
    }
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        assert "text" in response.json()
        print("PDF Extraction Test Passed")
    except requests.exceptions.RequestException as e:
        print(f"PDF Extraction Test Failed: {e}")

# Sentiment Analysis Agent Test
def test_sentiment_analysis():
    url = "http://localhost:8000/sentiment"
    data = {
        "text": "I love this product!"
    }
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        assert "sentiment" in response.json()
        print("Sentiment Analysis Test Passed")
    except requests.exceptions.RequestException as e:
        print(f"Sentiment Analysis Test Failed: {e}")

# Recommendation Agent Test
def test_recommendation():
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='recommendation')

        data = {
            "user_id": "123",
            "history": ["item1", "item2"]
        }
        channel.basic_publish(exchange='', routing_key='recommendation', body=json.dumps(data))
        print("Recommendation Test Message Sent")
        connection.close()
    except Exception as e:
        print(f"Recommendation Test Failed: {e}")

# Chatbot Agent Test
async def test_chatbot():
    try:
        async with websockets.connect('ws://localhost:8000/chat') as websocket:
            data = {
                "message": "Hello",
                "context": "General"
            }
            await websocket.send(json.dumps(data))
            response = await websocket.recv()
            assert "response" in json.loads(response)
            print("Chatbot Test Passed")
    except Exception as e:
        print(f"Chatbot Test Failed: {e}")

# RAG Scraper Agent Test
def test_rag_scraper():
    url = "http://localhost:8000/rag-scrape"
    data = {
        "query": "AI",
        "options": {
            "max_results": 5
        }
    }
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        assert "results" in response.json()
        print("RAG Scraper Test Passed")
    except requests.exceptions.RequestException as e:
        print(f"RAG Scraper Test Failed: {e}")

if __name__ == "__main__":
    test_pdf_extraction()
    test_sentiment_analysis()
    test_recommendation()
    asyncio.run(test_chatbot())
    test_rag_scraper()
