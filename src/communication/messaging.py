"""Messaging module for inter-agent communication."""

import aio_pika
import json
import logging
import os
from typing import Any, Dict, Optional, Callable
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class MessageBroker:
    """Handles asynchronous messaging between services using RabbitMQ."""
    
    def __init__(self, service_name: str):
        """Initialize the message broker.
        
        Args:
            service_name: Name of the service using this broker
        """
        self.service_name = service_name
        self.connection = None
        self.channel = None
        self.exchange = None
        self.callback_queue = None
        self.dlx_exchange = None
        self.dlq_queue = None
        
        # Get RabbitMQ URL from environment
        self.rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
        
    async def connect(self):
        """Connect to RabbitMQ and set up exchanges and queues."""
        try:
            # Connect to RabbitMQ
            self.connection = await aio_pika.connect_robust(
                "amqp://guest:guest@rabbitmq:5672/"
            )
            
            # Create channel
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)
            
            # Declare main exchange
            self.exchange = await self.channel.declare_exchange(
                "umbrella_ai",
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            # Declare Dead Letter Exchange (DLX)
            self.dlx_exchange = await self.channel.declare_exchange(
                "umbrella_ai.dlx",
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            # Declare Dead Letter Queue (DLQ)
            self.dlq_queue = await self.channel.declare_queue(
                "umbrella_ai.dlq",
                durable=True,
                arguments={
                    "x-message-ttl": 1000 * 60 * 60 * 24  # 24 hours TTL
                }
            )
            await self.dlq_queue.bind(self.dlx_exchange, "#")
            
            logger.info(f"Connected to RabbitMQ as {self.service_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise
    
    async def close(self):
        """Close the RabbitMQ connection."""
        if self.connection:
            await self.connection.close()
            logger.info("Closed RabbitMQ connection")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def publish(
        self,
        routing_key: str,
        message: Dict[str, Any],
        correlation_id: str,
        priority: int = 0
    ) -> None:
        """Publish a message with priority support."""
        try:
            if not self.exchange:
                raise RuntimeError("Not connected to RabbitMQ")

            # Ensure priority is within valid range (0-9)
            priority = max(0, min(9, priority))

            # Create message with headers
            message_body = aio_pika.Message(
                body=json.dumps(message).encode(),
                content_type="application/json",
                correlation_id=correlation_id,
                priority=priority,
                headers={
                    "service": self.service_name,
                    "retry_count": 0
                }
            )
            
            # Publish message
            await self.exchange.publish(
                message_body,
                routing_key=routing_key
            )
            
            logger.info(
                f"Published message to {routing_key}",
                extra={
                    "service": self.service_name,
                    "routing_key": routing_key,
                    "correlation_id": correlation_id,
                    "priority": priority
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to publish message: {str(e)}",
                extra={
                    "service": self.service_name,
                    "routing_key": routing_key,
                    "correlation_id": correlation_id
                }
            )
            raise
    
    async def subscribe(
        self,
        routing_key: str,
        callback: Callable[[Dict[str, Any], Dict[str, Any]], None]
    ) -> aio_pika.Queue:
        """Subscribe to messages with DLQ support.
        
        Args:
            routing_key: Routing key to subscribe to
            callback: Callback function to handle messages
            
        Returns:
            aio_pika.Queue: The queue object for this subscription
            
        Raises:
            RuntimeError: If not connected to RabbitMQ
        """
        try:
            if not self.channel:
                raise RuntimeError("Not connected to RabbitMQ")

            # Declare queue with DLQ configuration
            queue = await self.channel.declare_queue(
                f"{self.service_name}.{routing_key}",
                durable=True,
                arguments={
                    "x-dead-letter-exchange": "umbrella_ai.dlx",
                    "x-dead-letter-routing-key": routing_key,
                    "x-max-priority": 9  # Enable priority queue (0-9)
                }
            )

            await queue.bind(self.exchange, routing_key)

            async def message_handler(message: aio_pika.IncomingMessage):
                async with message.process():
                    try:
                        body = json.loads(message.body.decode())
                        headers = message.headers or {}
                        retry_count = headers.get("retry_count", 0)

                        if retry_count >= 3:
                            # Move to DLQ after 3 retries
                            await self.dlx_exchange.publish(
                                aio_pika.Message(
                                    body=message.body,
                                    headers={
                                        **headers,
                                        "final_failure_reason": "max_retries_exceeded"
                                    }
                                ),
                                routing_key=routing_key
                            )
                            logger.warning(
                                f"Message moved to DLQ after {retry_count} retries",
                                extra={
                                    "service": self.service_name,
                                    "correlation_id": message.correlation_id
                                }
                            )
                            return

                        # Process message
                        await callback(body, {
                            "correlation_id": message.correlation_id,
                            "priority": message.priority,
                            **headers
                        })

                    except Exception as e:
                        # Increment retry count and reject message
                        headers["retry_count"] = retry_count + 1
                        await message.reject(requeue=True)
                        
                        logger.error(
                            f"Error processing message: {str(e)}",
                            extra={
                                "service": self.service_name,
                                "correlation_id": message.correlation_id,
                                "retry_count": retry_count + 1
                            }
                        )

            await queue.consume(message_handler)
            logger.info(f"Subscribed to {routing_key}")
            return queue

        except Exception as e:
            logger.error(f"Failed to subscribe: {str(e)}")
            raise 