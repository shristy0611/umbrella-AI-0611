from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from textblob import TextBlob

app = FastAPI(title="Sentiment Analysis Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SentimentRequest(BaseModel):
    text: str
    metadata: Optional[Dict[str, Any]] = None

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "sentiment-analysis",
        "dependencies": {}
    }

@app.post("/analyze")
async def analyze_sentiment(request: SentimentRequest):
    """Analyze sentiment of the provided text."""
    try:
        # Use TextBlob for sentiment analysis
        blob = TextBlob(request.text)
        polarity = blob.sentiment.polarity
        
        # Map polarity to sentiment category
        sentiment = "neutral"
        if polarity > 0.1:
            sentiment = "positive"
        elif polarity < -0.1:
            sentiment = "negative"
        
        return {
            "sentiment": sentiment,
            "score": (polarity + 1) / 2,  # Convert from [-1,1] to [0,1]
            "metadata": {
                "text_length": len(request.text),
                "language": str(blob.detect_language()),
                **(request.metadata or {})
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 