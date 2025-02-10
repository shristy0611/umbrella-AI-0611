"""WebSocket client for real-time communication."""

import asyncio
import json
import logging
from typing import Dict, Any, Callable, Optional
import websockets
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class WebSocketClient:
    """Client for WebSocket-based real-time communication."""
    
    def __init__(self, service_name: str, url: str):
        """Initialize the WebSocket client.
        
        Args:
            service_name: Name of the service using this client
            url: WebSocket server URL
        """
        self.service_name = service_name
        self.url = url
        self.websocket = None
        self.message_handlers = {}
        self._running = False
        
    async def connect(self):
        """Connect to the WebSocket server."""
        try:
            self.websocket = await websockets.connect(self.url)
            self._running = True
            
            # Start message listener
            asyncio.create_task(self._message_listener())
            
            logger.info(
                f"Connected to WebSocket server",
                extra={
                    "service": self.service_name,
                    "url": self.url
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to connect to WebSocket server: {str(e)}",
                extra={
                    "service": self.service_name,
                    "url": self.url
                }
            )
            raise
    
    async def close(self):
        """Close the WebSocket connection."""
        self._running = False
        if self.websocket:
            await self.websocket.close()
            logger.info("Closed WebSocket connection")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def send_message(
        self,
        message: Dict[str, Any],
        correlation_id: str,
        message_type: str = "chat"
    ) -> None:
        """Send a message through WebSocket.
        
        Args:
            message: Message content
            correlation_id: Request correlation ID
            message_type: Type of message (default: "chat")
        """
        try:
            if not self.websocket:
                await self.connect()
            
            # Prepare message with metadata
            payload = {
                "type": message_type,
                "correlation_id": correlation_id,
                "service": self.service_name,
                "data": message
            }
            
            # Send message
            await self.websocket.send(json.dumps(payload))
            
            logger.info(
                f"Sent WebSocket message",
                extra={
                    "service": self.service_name,
                    "correlation_id": correlation_id,
                    "message_type": message_type
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to send WebSocket message: {str(e)}",
                extra={
                    "service": self.service_name,
                    "correlation_id": correlation_id,
                    "message_type": message_type
                }
            )
            raise
    
    async def register_handler(
        self,
        message_type: str,
        handler: Callable[[Dict[str, Any], str], None]
    ) -> asyncio.Future:
        """Register a handler for specific message types.
        
        Args:
            message_type: Type of messages to handle
            handler: Function to call when message is received
            
        Returns:
            asyncio.Future: Future that completes when handler is registered
        """
        self.message_handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")
        
        # Create and return a future for test assertions
        future = asyncio.Future()
        future.set_result(True)
        return future
    
    async def _message_listener(self):
        """Listen for incoming WebSocket messages."""
        while self._running:
            try:
                if not self.websocket:
                    await asyncio.sleep(1)
                    continue
                
                # Receive message
                message = await self.websocket.recv()
                data = json.loads(message)
                
                # Extract message details
                message_type = data.get("type", "unknown")
                correlation_id = data.get("correlation_id")
                
                # Find and call appropriate handler
                handler = self.message_handlers.get(message_type)
                if handler:
                    await handler(data.get("data", {}), correlation_id)
                    
                    logger.info(
                        f"Processed WebSocket message",
                        extra={
                            "service": self.service_name,
                            "correlation_id": correlation_id,
                            "message_type": message_type
                        }
                    )
                    
            except websockets.ConnectionClosed:
                logger.warning("WebSocket connection closed, attempting to reconnect...")
                await asyncio.sleep(1)
                await self.connect()
                
            except Exception as e:
                logger.error(
                    f"Error processing WebSocket message: {str(e)}",
                    extra={"service": self.service_name}
                )
                await asyncio.sleep(1) 