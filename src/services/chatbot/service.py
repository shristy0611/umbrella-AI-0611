"""Chatbot service implementation."""

import uuid
from typing import Dict, Any, List
from datetime import datetime
import google.generativeai as genai
from dataclasses import dataclass, field
import logging
from fastapi import FastAPI
from src.shared.base_service import BaseService
from src.shared.api_config import api_config
from src.shared.gemini_config import gemini_config
from src.services.service_registry import ServiceRegistry

logger = logging.getLogger(__name__)

app = FastAPI()
router = app.router


@dataclass
class ChatSession:
    """Chat session information."""

    id: str
    created_at: datetime
    messages: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChatbotService(BaseService):
    """Service for handling chat interactions."""

    def __init__(self, use_mock: bool = False):
        """Initialize chatbot service.

        Args:
            use_mock: Whether to use mock responses for testing
        """
        super().__init__("chatbot")
        self.use_mock = use_mock
        self.sessions = {}
        self._initialized = False
        if self.use_mock:
            # Set up mock model for testing
            class MockResponse:
                def __init__(self, text):
                    self.text = text

            class MockModel:
                def __init__(self):
                    self.response = MockResponse(
                        "This is a mock response from the chatbot."
                    )

                def generate_content(self, prompt: str) -> MockResponse:
                    return self.response

            self.model = MockModel()
        else:
            self.model = None

    async def initialize(self) -> None:
        """Initialize the chatbot service."""
        if self._initialized:
            return

        try:
            # Initialize API configuration
            await api_config.initialize()

            # Configure Gemini model
            self.model = gemini_config.configure_model("CHATBOT")

            self._initialized = True
            logger.info("Chatbot service initialized successfully")

        except Exception as e:
            logger.error(f"Chatbot init failed: {str(e)}")
            self._initialized = False
            raise

    async def cleanup(self) -> None:
        """Clean up service resources."""
        self.model = None
        self.sessions.clear()
        self._initialized = False

    async def validate_request(self, request: Dict[str, Any]) -> bool:
        """Validate chat request.

        Args:
            request: Request to validate

        Returns:
            bool: True if request is valid
        """
        if "messages" not in request:
            return False
        if not isinstance(request["messages"], list):
            return False
        if not request["messages"]:
            return False
        return True

    async def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process chat request.

        Args:
            request: Chat request

        Returns:
            Dict[str, Any]: Chat response
        """
        try:
            # Get or create session
            session_id = request.get("session_id")
            if session_id:
                session = self._get_session(session_id)
            else:
                session = await self.create_session()
                session_id = session.id

            # Update session context
            if "context" in request:
                session.context.update(request["context"])

            # Process messages
            messages = request["messages"]
            response = await self._generate_response(messages, session)

            # Update session history
            session.messages.extend(messages)
            session.messages.append(
                {"role": "assistant", "content": response["content"]}
            )

            return {
                "status": "success",
                "session_id": session_id,
                "response": response["content"],
                "metadata": response["metadata"]
            }

        except Exception as e:
            logger.error(f"Chat processing failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "service": self.service_name,
                "timestamp": datetime.now().isoformat()
            }

    async def create_session(self) -> ChatSession:
        """Create a new chat session.

        Returns:
            ChatSession: Created session
        """
        session_id = str(uuid.uuid4())
        session = ChatSession(id=session_id, created_at=datetime.now())
        self.sessions[session_id] = session
        return session

    async def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get chat session history.

        Args:
            session_id: Session ID

        Returns:
            List[Dict[str, Any]]: Session messages

        Raises:
            ValueError: If session not found
        """
        session = self._get_session(session_id)
        return session.messages

    def _get_session(self, session_id: str) -> ChatSession:
        """Get chat session by ID.

        Args:
            session_id: Session ID

        Returns:
            ChatSession: Chat session

        Raises:
            ValueError: If session not found
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        return self.sessions[session_id]

    async def _generate_response(
        self, messages: List[Dict[str, Any]], session: ChatSession
    ) -> Dict[str, Any]:
        """Generate response for messages.

        Args:
            messages: Chat messages
            session: Chat session

        Returns:
            Dict[str, Any]: Generated response
        """
        try:
            # Build conversation history
            history = []

            # Add context if available
            if session.context:
                history.append(
                    {"role": "system", "content": self._format_context(session.context)}
                )

            # Add previous messages
            history.extend(session.messages)

            # Add new messages
            history.extend(messages)

            # Generate response
            prompt = self._create_chat_prompt(history)
            response = self.model.generate_content(prompt)

            # Extract and format response
            content = response.text.strip()

            return {
                "content": content,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "model": "gemini-pro",
                    "context_used": bool(session.context),
                },
            }
        except Exception as e:
            raise ValueError(f"Failed to generate response: {str(e)}")

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context for the chat.

        Args:
            context: Context information

        Returns:
            str: Formatted context
        """
        formatted = ["Use the following context to inform your responses:"]

        # Add documents if available
        if "document" in context:
            formatted.append("\nDocument content:")
            formatted.append(context["document"])

        # Add sentiment if available
        if "sentiment" in context:
            sentiment = context["sentiment"]
            formatted.append(
                f"\nSentiment analysis: {sentiment.get('sentiment_label', 'unknown')} (score: {sentiment.get('sentiment_score', 0.0)})"
            )

        # Add topics if available
        if "topics" in context:
            formatted.append("\nIdentified topics:")
            topics = context["topics"]
            if isinstance(topics, dict) and "content" in topics:
                for item in topics["content"]:
                    formatted.append(f"- {item.get('title', 'Unknown topic')}")

        return "\n".join(formatted)

    def _create_chat_prompt(self, history: List[Dict[str, Any]]) -> str:
        """Create chat prompt from history.

        Args:
            history: Chat history

        Returns:
            str: Chat prompt
        """
        prompt = []

        for message in history:
            role = message["role"]
            content = message["content"]

            if role == "system":
                prompt.append(f"System: {content}")
            elif role == "user":
                prompt.append(f"User: {content}")
            elif role == "assistant":
                prompt.append(f"Assistant: {content}")

        prompt.append("Assistant:")
        return "\n\n".join(prompt)

    async def process_request(self, request: Dict[str, Any]) -> str:
        """Process a chat request and return the response.

        Args:
            request: Chat request containing messages and optional context

        Returns:
            str: Generated response text

        Raises:
            ValueError: If request is invalid or processing fails
        """
        if not self._initialized:
            raise RuntimeError("ChatbotService not initialized")

        # Validate request
        if not await self.validate_request(request):
            raise ValueError("Invalid chat request format")

        # Process request
        response = await self.process(request)
        return response["response"]

    async def health_check(self) -> Dict[str, str]:
        """Check service health.
        
        Returns:
            Dict[str, str]: Health status
        """
        return {
            "status": "healthy" if self._initialized and self.model is not None else "unhealthy"
        }


@router.get("/health")
async def health_check():
    return {"status": "healthy"}
