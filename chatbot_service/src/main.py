import logging
import os
from typing import Dict, Optional, List, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_CHAT")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY_CHAT environment variable not set")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Initialize FastAPI app
app = FastAPI(
    title="Chatbot Service",
    description="Service for handling multi-turn chat conversations using Gemini API",
    version="1.0.0"
)

# Store active chat sessions
chat_sessions: Dict[str, genai.ChatSession] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str
    context: Optional[List[Dict[str, Any]]] = None
    user_preferences: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    metadata: Dict[str, Any]

def create_system_prompt(user_preferences: Optional[Dict[str, Any]] = None) -> str:
    """Create a system prompt based on user preferences."""
    base_prompt = """You are a helpful AI assistant. Your responses should be:
    1. Clear and concise
    2. Accurate and well-researched
    3. Professional yet conversational
    4. Based on the provided context when available"""
    
    if user_preferences:
        if user_preferences.get("response_style") == "detailed":
            base_prompt += "\nProvide detailed explanations with examples."
        elif user_preferences.get("response_style") == "concise":
            base_prompt += "\nKeep responses brief and to the point."
            
        if user_preferences.get("expertise_level"):
            base_prompt += f"\nAdjust explanations for {user_preferences['expertise_level']} level understanding."
    
    return base_prompt

def format_context(context: List[Dict[str, Any]]) -> str:
    """Format context information for the chat."""
    if not context:
        return ""
        
    formatted_context = "Here's some relevant context for your response:\n\n"
    for item in context:
        if "content" in item:
            formatted_context += f"- {item['content']}\n"
        if "source" in item:
            formatted_context += f"  Source: {item['source']}\n"
    return formatted_context

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle a chat request using Gemini API."""
    try:
        # Get or create chat session
        if request.session_id not in chat_sessions:
            chat = model.start_chat(history=[])
            system_prompt = create_system_prompt(request.user_preferences)
            chat.send_message(system_prompt)
            chat_sessions[request.session_id] = chat
        else:
            chat = chat_sessions[request.session_id]
        
        # Format message with context
        message = request.message
        if request.context:
            context_text = format_context(request.context)
            message = f"{context_text}\n\nUser message: {message}"
        
        # Send message to Gemini
        response = await chat.send_message_async(message)
        
        # Extract and process response
        response_text = response.text
        
        return ChatResponse(
            response=response_text,
            session_id=request.session_id,
            metadata={
                "model": "gemini-pro",
                "context_used": bool(request.context),
                "preferences_applied": bool(request.user_preferences)
            }
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat processing error: {str(e)}")

@app.delete("/chat/{session_id}")
async def end_session(session_id: str):
    """End a chat session and clean up resources."""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
        return {"status": "success", "message": f"Session {session_id} ended"}
    raise HTTPException(status_code=404, detail="Session not found")

@app.get("/health")
async def health_check():
    """Check the health of the service."""
    try:
        # Test Gemini API
        test_response = model.generate_content("Test connection")
        api_status = "healthy" if test_response else "unhealthy"
    except Exception as e:
        api_status = "unhealthy"
        logger.error(f"Gemini API health check failed: {str(e)}")

    overall_status = "healthy" if api_status == "healthy" else "unhealthy"
    return {
        "status": overall_status,
        "service": "chatbot",
        "dependencies": {
            "gemini_api": api_status
        }
    } 