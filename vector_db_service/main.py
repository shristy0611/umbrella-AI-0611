from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import os
from datetime import datetime

app = FastAPI(title="Vector Database Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')
vector_dim = 384  # Dimension of the model's output

# Initialize FAISS index
index = faiss.IndexFlatL2(vector_dim)
texts = []
metadata_list = []

class VectorRequest(BaseModel):
    text: str
    metadata: Optional[Dict[str, Any]] = None

class SearchRequest(BaseModel):
    query: str
    k: int = 5
    filter: Optional[Dict[str, Any]] = None

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "vector-db",
        "dependencies": {}
    }

@app.post("/vectors/add")
async def add_vector(request: VectorRequest):
    """Add a vector to the database."""
    try:
        # Generate embedding
        embedding = model.encode([request.text])[0]
        
        # Add to FAISS index
        index.add(np.array([embedding], dtype=np.float32))
        
        # Store text and metadata
        texts.append(request.text)
        metadata_list.append(request.metadata or {})
        
        return {
            "status": "success",
            "vector_id": len(texts) - 1,
            "message": "Vector added successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vectors/search")
async def search_vectors(request: SearchRequest):
    """Search for similar vectors."""
    try:
        # Generate query embedding
        query_embedding = model.encode([request.query])[0]
        
        # Search in FAISS index
        D, I = index.search(np.array([query_embedding], dtype=np.float32), request.k)
        
        # Prepare results
        results = []
        for i, (distance, idx) in enumerate(zip(D[0], I[0])):
            if idx < len(texts):  # Valid index
                metadata = metadata_list[idx]
                if request.filter:
                    # Apply filters
                    if not all(metadata.get(k) == v for k, v in request.filter.items()):
                        continue
                results.append({
                    "distance": float(distance),
                    "index": int(idx),
                    "metadata": metadata
                })
        
        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005) 