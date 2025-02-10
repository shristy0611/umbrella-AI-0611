from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import google.generativeai as genai
import os
from datetime import datetime

app = FastAPI(title="Chatbot Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for chat history (replace with Redis in production)
chat_history = {}

class ChatRequest(BaseModel):
    session_id: str
    message: str
    context: Optional[Dict[str, Any]] = None

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "chatbot",
        "dependencies": {}
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    """Process a chat message and return a response."""
    try:
        # Initialize chat history for new sessions
        if request.session_id not in chat_history:
            chat_history[request.session_id] = []
        
        # Add user message to history
        chat_history[request.session_id].append({
            "role": "user",
            "content": request.message,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Generate response (mock for now)
        response = f"I understand you said: {request.message}"
        
        # Add assistant response to history
        chat_history[request.session_id].append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "response": response,
            "confidence": 0.95,
            "metadata": {
                "session_id": request.session_id,
                "history_length": len(chat_history[request.session_id]),
                "relevant_contexts": 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """Get chat history for a session."""
    if session_id not in chat_history:
        return {"history": []}
    return {"history": chat_history[session_id]}

@app.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """Clear chat history for a session."""
    if session_id in chat_history:
        chat_history.pop(session_id)
    return {
        "status": "success",
        "message": "Chat history cleared"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003) 