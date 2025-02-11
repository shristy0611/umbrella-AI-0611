"""API Gateway service for UMBRELLA-AI."""

import os
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import json

app = FastAPI(title="UMBRELLA-AI API Gateway")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=json.loads(os.getenv("ALLOWED_ORIGINS", '["http://localhost:3000"]')),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Role of the message sender (user or assistant)")
    content: str = Field(..., description="Content of the message")


class ChatRequest(BaseModel):
    """Chat request model."""

    messages: List[Message] = Field(..., description="Chat messages")
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional context"
    )


class TaskRequest(BaseModel):
    """Task request model."""

    task_type: str = Field(..., description="Type of task to execute")
    content: Dict[str, Any] = Field(..., description="Task content")
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional context"
    )


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/v1/upload")
async def upload_file(file: UploadFile = File(...)) -> Dict[str, str]:
    """Upload a file for processing."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        # Store file and get file ID
        content = await file.read()
        file_id = f"file_{hash(content)}"  # Replace with proper storage in production

        return {"file_id": file_id, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/tasks")
async def create_task(
    task_request: TaskRequest, background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """Create a new task."""
    try:
        # Validate task type
        if task_request.task_type not in [
            "document_analysis",
            "sentiment_analysis",
            "chat",
        ]:
            raise HTTPException(status_code=400, detail="Invalid task type")

        # Submit task to orchestrator
        from src.orchestrator.orchestrator import orchestrator

        task_id = await orchestrator.submit_task(task_request.dict())

        # Add task to background processing
        background_tasks.add_task(orchestrator.process_task, task_id)

        return {"task_id": task_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get task status."""
    try:
        from src.orchestrator.orchestrator import orchestrator

        status = await orchestrator.get_task_status(task_id)
        return {
            "task_id": status.task_id,
            "status": status.status,
            "progress": status.progress,
            "error": status.error,
            "created_at": status.created_at.isoformat(),
            "updated_at": status.updated_at.isoformat(),
            "completed_at": (
                status.completed_at.isoformat() if status.completed_at else None
            ),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tasks/{task_id}/results")
async def get_task_results(task_id: str) -> Dict[str, Any]:
    """Get task results."""
    try:
        from src.orchestrator.orchestrator import orchestrator

        results = await orchestrator.get_task_results(task_id)
        return results
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/chat/messages")
async def chat(chat_request: ChatRequest) -> Dict[str, str]:
    """Chat endpoint."""
    try:
        from src.services.chatbot.service import chatbot_service

        # Convert Pydantic models to dictionaries
        messages = [
            {"role": msg.role, "content": msg.content} for msg in chat_request.messages
        ]
        request = {"messages": messages, "context": chat_request.context or {}}

        response = await chatbot_service.process(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
