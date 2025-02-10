from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import logging
import os
from typing import List, Dict, Optional

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

# Initialize the sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')
logger.info(f"Initialized SentenceTransformer model successfully, listening on {HOST}:{PORT}")

# Initialize FAISS index
dimension = 384  # Dimension of embeddings from all-MiniLM-L6-v2
index = faiss.IndexFlatL2(dimension)
logger.info("Initialized FAISS index successfully")

class VectorInput(BaseModel):
    text: str
    metadata: Optional[Dict] = None

class SearchQuery(BaseModel):
    query: str
    k: int = 5

@app.post("/vectors/add")
async def add_vector(input_data: VectorInput):
    try:
        # Generate embedding
        embedding = model.encode([input_data.text])[0]
        
        # Add to FAISS index
        index.add(np.array([embedding]).astype('float32'))
        
        return {"status": "success", "message": "Vector added successfully"}
    except Exception as e:
        logger.error(f"Error adding vector: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vectors/search")
async def search_vectors(query: SearchQuery):
    try:
        # Generate query embedding
        query_embedding = model.encode([query.query])[0]
        
        # Search in FAISS index
        D, I = index.search(np.array([query_embedding]).astype('float32'), query.k)
        
        return {
            "status": "success",
            "results": [
                {"distance": float(d), "index": int(i)} 
                for d, i in zip(D[0], I[0])
            ]
        }
    except Exception as e:
        logger.error(f"Error searching vectors: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Check the health of the service."""
    try:
        # Test model
        test_embedding = model.encode(["test"])[0]
        # Test index
        D, I = index.search(np.array([test_embedding]).astype('float32'), 1)
        
        return {
            "status": "healthy",
            "service": "vector_db",
            "dependencies": {
                "model": "healthy",
                "index": "healthy"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "vector_db",
            "dependencies": {
                "model": "unhealthy",
                "index": "unhealthy"
            }
        } 