"""Service for handling chat interactions with AI."""

import logging
from typing import Dict, List, Optional, Any, AsyncGenerator

class Chatbot:
    """Chatbot service for generating responses."""

    def __init__(self):
        """Initialize the chatbot service."""
        self.logger = logging.getLogger(__name__)
        self.sessions: Dict[str, List[Dict[str, str]]] = {}
        self.max_message_length = 1000

    def _filter_context(self, context: List[Dict[str, Any]], threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Filter context based on relevance threshold."""
        if not context:
            return []
        return [
            item for item in context 
            if item.get("metadata", {}).get("relevance", 0) >= threshold
        ]

    def _format_response(self, response: str, format_options: Optional[Dict[str, Any]] = None) -> str:
        """Format the response according to options."""
        if not format_options:
            return response

        if format_options.get("style") == "bullet_points":
            # Split on periods and create bullet points
            sentences = [s.strip() for s in response.split(".") if s.strip()]
            return "\n".join(f"• {sentence}" for sentence in sentences)

        return response

    async def _generate_response(
        self,
        message: str,
        context: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Generate a response using context and conversation history."""
        # Use context if available
        if context:
            relevant_text = " ".join(item["text"] for item in context)
            return f"Based on the context: {relevant_text}"

        # Use conversation history if available
        if conversation_history:
            for msg in reversed(conversation_history):
                if msg["role"] == "assistant" and "AI" in msg["content"]:
                    return f"Based on our previous discussion about {msg['content']}, here's more information about those features..."

        return f"Response to: {message}"

    async def generate_response(
        self,
        message: str,
        context: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        format_options: Optional[Dict[str, Any]] = None,
        relevance_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """Generate a response to the user's message."""
        if not message.strip():
            raise ValueError("Empty message")

        original_length = len(message)
        if original_length > self.max_message_length:
            message = message[:self.max_message_length]
            metadata = {
                "truncated": True,
                "original_length": original_length,
                "truncated_length": self.max_message_length,
                "truncated_input": True
            }
        else:
            metadata = {
                "truncated": False,
                "original_length": original_length
            }

        try:
            # Filter context if provided
            filtered_context = self._filter_context(context or [], relevance_threshold)
            
            # Generate response
            response = await self._generate_response(
                message,
                filtered_context,
                conversation_history
            )

            # Format response if needed
            formatted_response = self._format_response(response, format_options)

            # Update session if provided
            if session_id:
                if session_id not in self.sessions:
                    self.sessions[session_id] = []
                self.sessions[session_id].extend([
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": formatted_response}
                ])

            # Update metadata
            metadata.update({
                "session_id": session_id,
                "sources_used": [
                    {
                        "source": item.get("metadata", {}).get("source"),
                        "relevance": item.get("metadata", {}).get("relevance", 0)
                    }
                    for item in filtered_context
                    if item.get("metadata", {}).get("source")
                ],
                "sources": [
                    {
                        "text": item["text"],
                        "metadata": item.get("metadata", {})
                    }
                    for item in filtered_context
                ]
            })

            return {
                "response": formatted_response,
                "metadata": metadata
            }
        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}")
            raise

    async def generate_response_stream(
        self,
        message: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate response as a stream of words."""
        result = await self.generate_response(message, **kwargs)
        response = result["response"]
        
        # Yield words one by one
        for word in response.split():
            yield word + " "

    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming chat request."""
        if "message" not in request_data:
            raise ValueError("Missing message")

        message = request_data["message"]
        context = request_data.get("context")
        conversation_history = request_data.get("conversation_history")
        user_preferences = request_data.get("user_preferences")
        session_id = request_data.get("session_id")
        format_options = request_data.get("format_options")
        relevance_threshold = request_data.get("relevance_threshold", 0.7)

        return await self.generate_response(
            message=message,
            context=context,
            conversation_history=conversation_history,
            user_preferences=user_preferences,
            session_id=session_id,
            format_options=format_options,
            relevance_threshold=relevance_threshold
        ) 