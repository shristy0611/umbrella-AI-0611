"""Module for handling text chat sessions with Gemini API."""

import os
import asyncio
from typing import List, Optional, Dict, Any
import google.generativeai as genai
from .utils import async_retry_with_backoff, logger

class GeminiTextChat:
    def __init__(self):
        """Initialize the Gemini text chat module."""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.chat = None
        self._logger = logger.getChild('text_chat')

    @async_retry_with_backoff()
    async def start_text_chat(self) -> None:
        """Start a new text chat session with retry mechanism."""
        try:
            self.chat = self.model.start_chat(history=[])
            self._logger.info("Successfully started new chat session")
        except Exception as e:
            self._logger.error(f"Failed to start chat session: {str(e)}")
            raise RuntimeError(f"Failed to start chat session: {str(e)}")

    @async_retry_with_backoff()
    async def send_message(self, message: str) -> Any:
        """Send a message to the chat session and get response with retry mechanism.
        
        Args:
            message: The text message to send.
            
        Returns:
            Any: The response from Gemini API.
            
        Raises:
            RuntimeError: If chat session not started or if sending fails after retries.
        """
        if not self.chat:
            self._logger.error("Chat session not started")
            raise RuntimeError("Chat session not started. Call start_text_chat() first.")
        
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
            List[Dict]: List of message exchanges.
        """
        if not self.chat:
            return []
        return self.chat.history 