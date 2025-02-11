"""
Messaging module for handling communication between services.
"""
import aio_pika
import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

class MessageBroker:
    """
    Handles asynchronous messaging between services using RabbitMQ.
    """
    
    def __init__(self, url: str = "amqp://guest:guest@localhost/"):
        self.url = url
        self.connection = None
        self.channel = None
        self.exchange = None
        self._handlers = {}
        
    async def connect(self):
        """Establish connection to RabbitMQ."""
        try:
            self.connection = await aio_pika.connect_robust(self.url)
            self.channel = await self.connection.channel()
            self.exchange = await self.channel.declare_exchange(
                "umbrella",
                aio_pika.ExchangeType.TOPIC
            )
            logger.info("Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise
            
    async def publish(self, routing_key: str, message: Dict[str, Any], correlation_id: Optional[str] = None):
        """Publish a message to the exchange."""
        if not self.exchange:
            raise RuntimeError("Not connected to RabbitMQ")
            
        try:
            message_body = json.dumps(message).encode()
            await self.exchange.publish(
                aio_pika.Message(
                    body=message_body,
                    correlation_id=correlation_id
                ),
                routing_key=routing_key
            )
            logger.debug(f"Published message to {routing_key}: {message}")
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}")
            raise
            
    async def subscribe(self, routing_key: str, callback: Callable):
        """Subscribe to messages with the given routing key."""
        if not self.channel:
            raise RuntimeError("Not connected to RabbitMQ")
            
        try:
            queue = await self.channel.declare_queue(exclusive=True)
            await queue.bind(self.exchange, routing_key)
            
            async def _handle_message(message: aio_pika.IncomingMessage):
                async with message.process():
                    try:
                        body = json.loads(message.body.decode())
                        await callback(body, message.correlation_id)
                    except Exception as e:
                        logger.error(f"Error processing message: {str(e)}")
                        
            await queue.consume(_handle_message)
            self._handlers[routing_key] = queue
            logger.info(f"Subscribed to {routing_key}")
        except Exception as e:
            logger.error(f"Failed to subscribe to {routing_key}: {str(e)}")
            raise
            
    async def close(self):
        """Close the connection to RabbitMQ."""
        try:
            if self.connection:
                await self.connection.close()
                logger.info("Closed RabbitMQ connection")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {str(e)}")
            raise 