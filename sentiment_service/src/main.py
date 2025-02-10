import logging
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import pipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Sentiment Analysis Service",
    description="Service for analyzing sentiment in text",
    version="1.0.0"
)

# Initialize sentiment analysis pipeline
try:
    sentiment_analyzer = pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english",
        device=-1  # Use CPU
    )
except Exception as e:
    logger.error(f"Error loading sentiment model: {str(e)}")
    sentiment_analyzer = None

class SentimentRequest(BaseModel):
    text: str
    metadata: Optional[Dict] = None

class SentimentResponse(BaseModel):
    sentiment: str
    score: float
    metadata: Optional[Dict] = None

@app.post("/analyze", response_model=SentimentResponse)
async def analyze_sentiment(request: SentimentRequest):
    """Analyze sentiment in the provided text."""
    if not sentiment_analyzer:
        raise HTTPException(status_code=503, detail="Sentiment analyzer not available")

    try:
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")

        # Perform sentiment analysis
        result = sentiment_analyzer(request.text)[0]
        
        metadata = {"text_length": len(request.text)}
        if request.metadata:
            metadata.update(request.metadata)
        
        return SentimentResponse(
            sentiment=result["label"],
            score=float(result["score"]),
            metadata=metadata
        )

    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        raise HTTPException(status_code=500, detail="Error analyzing sentiment")

@app.get("/health")
async def health_check():
    """Check the health of the service."""
    status = "healthy" if sentiment_analyzer else "unhealthy"
    return {
        "status": status,
        "service": "sentiment_analysis",
        "dependencies": {
            "model": status
        }
    } 