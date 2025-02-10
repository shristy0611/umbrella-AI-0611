# Vector Database Service

A microservice for storing and retrieving vector embeddings using FAISS and Sentence Transformers.

## Features

- Fast vector similarity search using FAISS
- Text-to-vector embedding using Sentence Transformers
- RESTful API endpoints for adding and searching vectors
- Containerized deployment with Docker
- Comprehensive test suite

## Setup

### Prerequisites

- Docker
- Python 3.9+ (for local development)

### Installation

1. Build the Docker image:
```bash
docker build -t vector-db-service .
```

2. Run the container:
```bash
docker run -d -p 8005:8005 --name vector-db vector-db-service
```

## API Endpoints

### Health Check
```
GET /health
```

### Add Vector
```
POST /vectors/add
{
    "text": "Your text here",
    "metadata": {
        "optional": "metadata"
    }
}
```

### Search Vectors
```
POST /vectors/search
{
    "query": "Your search query",
    "k": 5
}
```

## Development

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run tests:
```bash
pytest tests/
```

4. Start the development server:
```bash
uvicorn src.main:app --reload --port 8005
```

## Configuration

The service uses the following environment variables:
- `MODEL_NAME`: Sentence transformer model name (default: 'all-MiniLM-L6-v2')
- `PORT`: Service port (default: 8005)

## Testing

Run the test suite:
```bash
pytest tests/
```

## Monitoring

The service includes basic monitoring endpoints:
- Health check endpoint (`/health`)
- Prometheus metrics (coming soon) 