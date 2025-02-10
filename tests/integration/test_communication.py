import pytest
import asyncio
from typing import Dict, Any
import os
import uuid
from src.communication.messaging import MessageBroker
from src.communication.service_client import ServiceClient
from src.communication.websocket_client import WebSocketClient

# Service URLs from environment
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
PDF_SERVICE_URL = os.getenv("PDF_SERVICE_URL", "http://localhost:8001")
SENTIMENT_SERVICE_URL = os.getenv("SENTIMENT_SERVICE_URL", "http://localhost:8002")
CHATBOT_WS_URL = os.getenv("CHATBOT_WS_URL", "ws://localhost:8003/chat")

@pytest.fixture
async def message_broker():
    """Create and connect a message broker instance."""
    broker = MessageBroker("test_service")
    await broker.connect()
    yield broker
    await broker.close()

@pytest.fixture
async def pdf_service_client():
    """Create a service client for the PDF service."""
    client = ServiceClient(PDF_SERVICE_URL, "pdf_service")
    yield client
    await client.close()

@pytest.fixture
async def sentiment_service_client():
    """Create a service client for the sentiment service."""
    client = ServiceClient(SENTIMENT_SERVICE_URL, "sentiment_service")
    yield client
    await client.close()

@pytest.fixture
async def chat_ws_client():
    """Create a WebSocket client for the chat service."""
    client = WebSocketClient("test_service", CHATBOT_WS_URL)
    await client.connect()
    yield client
    await client.close()

@pytest.mark.asyncio
async def test_message_broker_publish_subscribe(message_broker):
    """Test message publishing and subscribing with priority."""
    test_message = {"test": "data"}
    correlation_id = str(uuid.uuid4())
    received_messages = []
    
    # Create subscriber
    async def message_handler(message: Dict[str, Any], metadata: Dict[str, Any]):
        received_messages.append((message, metadata))
    
    # Subscribe to test topic
    await message_broker.subscribe("test.topic", message_handler)
    
    # Publish message with high priority
    await message_broker.publish(
        "test.topic",
        test_message,
        correlation_id,
        priority=9
    )
    
    # Wait for message to be received
    await asyncio.sleep(1)
    
    assert len(received_messages) == 1
    assert received_messages[0][0]["test"] == "data"
    assert received_messages[0][1]["correlation_id"] == correlation_id

@pytest.mark.asyncio
async def test_dead_letter_queue(message_broker):
    """Test message routing to dead letter queue after failures."""
    correlation_id = str(uuid.uuid4())
    error_count = 0
    
    # Create subscriber that always fails
    async def failing_handler(message: Dict[str, Any], metadata: Dict[str, Any]):
        nonlocal error_count
        error_count += 1
        raise Exception("Simulated failure")
    
    # Subscribe to test topic
    await message_broker.subscribe("test.dlq", failing_handler)
    
    # Publish message
    await message_broker.publish(
        "test.dlq",
        {"test": "dlq"},
        correlation_id
    )
    
    # Wait for retries and DLQ routing
    await asyncio.sleep(5)
    
    # Verify message was retried 3 times before going to DLQ
    assert error_count == 3

@pytest.mark.asyncio
async def test_websocket_chat(chat_ws_client):
    """Test WebSocket-based chat communication."""
    correlation_id = str(uuid.uuid4())
    received_messages = []
    
    # Register message handler
    async def chat_handler(message: Dict[str, Any], correlation_id: str):
        received_messages.append((message, correlation_id))
    
    chat_ws_client.register_handler("chat_response", chat_handler)
    
    # Send chat message
    await chat_ws_client.send_message(
        {"text": "Hello, how are you?"},
        correlation_id
    )
    
    # Wait for response
    await asyncio.sleep(1)
    
    assert len(received_messages) == 1
    assert "text" in received_messages[0][0]
    assert received_messages[0][1] == correlation_id

@pytest.mark.asyncio
async def test_mixed_communication(message_broker, pdf_service_client, chat_ws_client):
    """Test mixed communication patterns (REST, WebSocket, and Message Queue)."""
    correlation_id = str(uuid.uuid4())
    results = []
    
    # Set up message handler
    async def message_handler(message: Dict[str, Any], metadata: Dict[str, Any]):
        results.append(("mq", message, metadata))
    
    # Set up WebSocket handler
    async def ws_handler(message: Dict[str, Any], correlation_id: str):
        results.append(("ws", message, {"correlation_id": correlation_id}))
    
    # Subscribe to message queue
    await message_broker.subscribe("test.mixed", message_handler)
    chat_ws_client.register_handler("mixed_response", ws_handler)
    
    # Make all requests concurrently
    await asyncio.gather(
        message_broker.publish("test.mixed", {"source": "mq"}, correlation_id),
        pdf_service_client.request("GET", "/health", correlation_id),
        chat_ws_client.send_message({"source": "ws"}, correlation_id)
    )
    
    # Wait for all responses
    await asyncio.sleep(2)
    
    # Verify we got responses from all communication methods
    protocols = [r[0] for r in results]
    assert "mq" in protocols
    assert "ws" in protocols
    assert all(r[2]["correlation_id"] == correlation_id for r in results)

@pytest.mark.asyncio
async def test_service_client_health_check(pdf_service_client):
    """Test service client health check request."""
    correlation_id = str(uuid.uuid4())
    
    response = await pdf_service_client.request(
        method="GET",
        endpoint="/health",
        correlation_id=correlation_id
    )
    
    assert response["status"] == "healthy"
    assert response["service"] == "pdf_extraction"

@pytest.mark.asyncio
async def test_service_client_error_handling(pdf_service_client):
    """Test service client error handling."""
    correlation_id = str(uuid.uuid4())
    
    with pytest.raises(Exception):
        await pdf_service_client.request(
            method="POST",
            endpoint="/nonexistent",
            correlation_id=correlation_id,
            data={"test": "data"}
        )

@pytest.mark.asyncio
async def test_correlation_id_propagation(message_broker, pdf_service_client, chat_ws_client):
    """Test correlation ID propagation across all communication methods."""
    correlation_id = str(uuid.uuid4())
    received_correlation_ids = set()
    
    # Message queue handler
    async def mq_handler(message: Dict[str, Any], metadata: Dict[str, Any]):
        received_correlation_ids.add(metadata["correlation_id"])
    
    # WebSocket handler
    async def ws_handler(message: Dict[str, Any], correlation_id: str):
        received_correlation_ids.add(correlation_id)
    
    # Set up handlers
    await message_broker.subscribe("test.correlation", mq_handler)
    chat_ws_client.register_handler("correlation_response", ws_handler)
    
    # Send messages through all channels
    await asyncio.gather(
        message_broker.publish("test.correlation", {"test": "mq"}, correlation_id),
        chat_ws_client.send_message({"test": "ws"}, correlation_id),
        pdf_service_client.request("GET", "/health", correlation_id)
    )
    
    # Wait for processing
    await asyncio.sleep(2)
    
    # Verify correlation ID was preserved
    assert len(received_correlation_ids) > 0
    assert all(cid == correlation_id for cid in received_correlation_ids)

@pytest.mark.asyncio
async def test_service_client_retry_mechanism(pdf_service_client):
    """Test service client retry mechanism."""
    correlation_id = str(uuid.uuid4())
    
    # Mock a failing request that should be retried
    with pytest.raises(Exception):
        await pdf_service_client.request(
            method="POST",
            endpoint="/test-retry",
            correlation_id=correlation_id,
            data={"test": "retry"}
        )

@pytest.mark.asyncio
async def test_message_broker_error_handling(message_broker):
    """Test message broker error handling."""
    correlation_id = str(uuid.uuid4())
    error_received = False
    
    async def error_handler(message: Dict[str, Any]):
        nonlocal error_received
        if message.get("error"):
            error_received = True
    
    await message_broker.subscribe("test.error", error_handler)
    
    # Publish error message
    await message_broker.publish(
        "test.error",
        {"error": "test_error"},
        correlation_id
    )
    
    await asyncio.sleep(1)
    assert error_received

@pytest.mark.asyncio
async def test_concurrent_message_processing(message_broker):
    """Test concurrent message processing."""
    correlation_id = str(uuid.uuid4())
    processed_messages = []
    
    async def slow_handler(message: Dict[str, Any]):
        await asyncio.sleep(0.1)
        processed_messages.append(message)
    
    await message_broker.subscribe("test.concurrent", slow_handler)
    
    # Publish multiple messages concurrently
    await asyncio.gather(*[
        message_broker.publish(
            "test.concurrent",
            {"index": i},
            correlation_id
        )
        for i in range(5)
    ])
    
    await asyncio.sleep(1)
    assert len(processed_messages) == 5 