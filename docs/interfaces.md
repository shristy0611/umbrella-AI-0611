# UMBRELLA-AI Service Interfaces

This document defines the interfaces for all microservices in the UMBRELLA-AI system.

## Common Patterns

### HTTP Headers
All services accept and respond with the following headers:
```
X-Correlation-ID: string  # Request tracing ID
Content-Type: application/json
Accept: application/json
```

### Error Response Format
All services use consistent error responses:
```json
{
    "detail": "Error message",
    "status_code": number,
    "correlation_id": "uuid-string"
}
```

### Health Check Endpoint
All services implement a health check endpoint:
```
GET /health

Response 200:
{
    "status": "healthy" | "unhealthy",
    "service": string,
    "dependencies"?: {
        [key: string]: "healthy" | "unhealthy"
    }
}
```

## PDF Extraction Service (Port 8001)

### Extract Text from PDF
```
POST /extract
Content-Type: multipart/form-data

Request:
- file: PDF file upload

Response 200:
{
    "text": string,
    "pages": number,
    "metadata": {
        "filename": string,
        "content_type": string,
        ...
    }
}
```

## Sentiment Analysis Service (Port 8002)

### Analyze Sentiment
```
POST /analyze

Request:
{
    "text": string,
    "metadata"?: {
        "source": string,
        "context": string,
        ...
    }
}

Response 200:
{
    "sentiment": "positive" | "negative" | "neutral",
    "score": number,  // 0 to 1
    "metadata"?: object
}
```

## Chatbot Service (Port 8003)

### Chat
```
POST /chat

Request:
{
    "session_id": string,
    "message": string,
    "context"?: {
        "previous_messages": array,
        "metadata": object
    }
}

Response 200:
{
    "response": string,
    "confidence": number,
    "metadata": {
        "session_id": string,
        "history_length": number,
        "relevant_contexts": number
    }
}
```

### Get Chat History
```
GET /history/{session_id}

Response 200:
{
    "history": [
        {
            "role": "user" | "assistant",
            "content": string,
            "timestamp": string
        }
    ]
}
```

### Clear Chat History
```
DELETE /history/{session_id}

Response 200:
{
    "status": "success",
    "message": string
}
```

## RAG Scraper Service (Port 8004)

### Scrape Website
```
POST /scrape

Request:
{
    "url": string,
    "max_depth": number,
    "max_pages": number,
    "selectors"?: string[],
    "exclude_patterns"?: string[]
}

Response 200:
{
    "content": {
        [url: string]: string
    },
    "metadata": {
        "pages_scraped": number,
        "total_discovered_urls": number
    },
    "discovered_urls": string[]
}
```

## Vector Database Service (Port 8005)

### Add Vector
```
POST /vectors/add

Request:
{
    "text": string,
    "metadata"?: {
        "source": string,
        "type": string,
        "timestamp": string,
        ...
    }
}

Response 200:
{
    "status": "success",
    "vector_id": string,
    "message": string
}
```

### Search Vectors
```
POST /vectors/search

Request:
{
    "query": string,
    "k": number,
    "filter"?: {
        [key: string]: any
    }
}

Response 200:
{
    "status": "success",
    "results": [
        {
            "distance": number,
            "index": number,
            "metadata"?: object
        }
    ]
}
```

## Orchestrator Service (Port 8000)

### Process Task
```
POST /process

Request:
{
    "task_type": string,
    "data": object,
    "context"?: object
}

Response 200:
{
    "status": "success",
    "result": object,
    "metadata": {
        "correlation_id": string,
        "service": string,
        ...
    }
}
```

## Message Queue Integration

Services communicate asynchronously through RabbitMQ using the following exchanges and queues:

### Task Queue
- Exchange: `umbrella_ai`
- Queue: `tasks`
- Routing Key: `task.process`

### Message Format
```json
{
    "task_id": string,
    "service": string,
    "action": string,
    "data": object,
    "correlation_id": string,
    "timestamp": string
}
```

## Security

1. All services run as non-root users
2. Internal services are not exposed externally
3. API keys and sensitive data are managed through environment variables
4. Network isolation is enforced through Docker network configuration 