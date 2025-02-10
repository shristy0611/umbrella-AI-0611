"""Module for multi-turn chat sessions with Gemini API."""

import os
import asyncio
from typing import List, Dict, Optional, Any
import google.generativeai as genai
from .utils import async_retry_with_backoff, logger

class GeminiMultiTurnChat:
    def __init__(self):
        """Initialize the Gemini multi-turn chat module."""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.chat = None
        self.context = ""
        self._logger = logger.getChild('multi_turn_chat')

    @async_retry_with_backoff()
    async def start_chat_session(self, context: Optional[str] = None) -> None:
        """Start a new multi-turn chat session with retry mechanism.
        
        Args:
            context: Optional context to initialize the chat session
            
        Raises:
            RuntimeError: If starting the chat session fails after retries
        """
        try:
            self.context = context or ""
            initial_history = []
            if self.context:
                self._logger.info(f"Initializing chat with context: {self.context[:50]}...")
                initial_history.append({
                    "role": "user",
                    "parts": [self.context]
                })
            self.chat = self.model.start_chat(history=initial_history)
            self._logger.info("Successfully started new chat session")
        except Exception as e:
            self._logger.error(f"Failed to start chat session: {str(e)}")
            raise RuntimeError(f"Failed to start chat session: {str(e)}")

    @async_retry_with_backoff()
    async def send_message(self, message: str) -> Any:
        """Send a message in the multi-turn chat session with retry mechanism.
        
        Args:
            message: The text message to send
            
        Returns:
            Any: The response from Gemini API
            
        Raises:
            RuntimeError: If chat session not started or if sending fails after retries
        """
        if not self.chat:
            self._logger.error("Chat session not started")
            raise RuntimeError("Chat session not started. Call start_chat_session() first.")
        
        try:
            self._logger.info(f"Sending message: {message[:50]}...")
            response = await self.chat.send_message_async(message)
            self._logger.info("Successfully received response")
            return response
        except Exception as e:
            self._logger.error(f"Failed to send message: {str(e)}")
            raise RuntimeError(f"Failed to send message: {str(e)}")

    def get_chat_history(self) -> List[Dict]:
        """Get the current chat history.
        
        Returns:
            List[Dict]: List of message exchanges
        """
        if not self.chat:
            return []
        return self.chat.history

    def get_context(self) -> str:
        """Get the current chat context.
        
        Returns:
            str: The chat context
        """
        return self.context

    @async_retry_with_backoff()
    async def update_context(self, new_context: str) -> None:
        """Update the chat context and restart the session with retry mechanism.
        
        Args:
            new_context: New context for the chat session
            
        Raises:
            RuntimeError: If updating context fails after retries
        """
        try:
            self._logger.info(f"Updating context: {new_context[:50]}...")
            self.context = new_context
            await self.start_chat_session(self.context)
            self._logger.info("Successfully updated context and restarted session")
        except Exception as e:
            self._logger.error(f"Failed to update context: {str(e)}")
            raise RuntimeError(f"Failed to update context: {str(e)}") 