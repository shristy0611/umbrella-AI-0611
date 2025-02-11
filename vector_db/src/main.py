"""Vector database service for UMBRELLA-AI."""

import logging
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import os
from fastapi.responses import JSONResponse
from fastapi import Body
from huggingface_hub import HfApi, HfFolder, Repository, hf_hub_url
from huggingface_hub import hf_hub_download as cached_download  # Alias deprecated name

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8005"))

app = FastAPI(
    title="Vector Database Service",
    description="Service for storing and retrieving vector embeddings",
    version="1.0.0",
    root_path="",
    docs_url="/docs",
    redoc_url="/redoc"
)

class VectorData(BaseModel):
    """Vector data model."""
    text: str
    metadata: Dict[str, Any] = {}

class SearchQuery(BaseModel):
    """Search query model."""
    text: str
    k: int = 5

class VectorService:
    """Service for vector operations."""
    
    def __init__(self):
        """Initialize the vector service with SentenceTransformer model."""
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = faiss.IndexFlatL2(384)  # 384 is the dimension of the model's embeddings
        self.metadata = []
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initialized SentenceTransformer model successfully")
    
    async def encode_text(self, text: str) -> np.ndarray:
        """Encode text into a vector using the model."""
        try:
            vector = self.model.encode(text)
            return vector.astype(np.float32)
        except Exception as e:
            self.logger.error(f"Error encoding text: {str(e)}")
            raise

    async def add_vector(self, vector: np.ndarray, metadata: Dict[str, Any]) -> int:
        """Add a vector to the index."""
        try:
            vector = vector.reshape(1, -1)
            self.index.add(vector)
            vector_id = len(self.metadata)
            self.metadata.append(metadata)
            return vector_id
        except Exception as e:
            self.logger.error(f"Error adding vector: {str(e)}")
            raise

    async def search_vectors(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        try:
            query_vector = await self.encode_text(query)
            query_vector = query_vector.reshape(1, -1)
            
            distances, indices = self.index.search(query_vector, k)
            
            results = []
            for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(self.metadata):  # Ensure index is valid
                    results.append({
                        "id": int(idx),
                        "distance": float(dist),
                        "metadata": self.metadata[idx]
                    })
            return results
        except Exception as e:
            self.logger.error(f"Error searching vectors: {str(e)}")
            raise

service = VectorService()

@app.post("/vectors/add")
async def add_vector(vector_data: VectorData) -> Dict[str, Any]:
    """Add a vector to the index."""
    try:
        if not vector_data.text.strip():
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Text cannot be empty"}
            )

        if len(vector_data.text) > 10000:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Text too long (max 10000 characters)"}
            )

        vector = await service.encode_text(vector_data.text)
        vector_id = await service.add_vector(vector, vector_data.metadata)
        
        return {"status": "success", "message": "Vector added successfully", "vector_id": vector_id}

    except Exception as e:
        logger.error(f"Error adding vector: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.post("/vectors/search")
async def search_vectors(query: str = Body(...), limit: int = 10) -> Dict[str, Any]:
    """Search for similar vectors."""
    try:
        if not query.strip():
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Query cannot be empty"}
            )

        if len(query) > 10000:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Query too long (max 10000 characters)"}
            )

        results = await service.search_vectors(query, limit)
        return {
            "status": "success",
            "results": results
        }

    except Exception as e:
        logger.error(f"Error searching vectors: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    try:
        # Verify model and index are initialized
        if service.model and service.index:
            return {"status": "healthy"}
        return {"status": "degraded"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy"} 