"""Sentiment analysis service implementation."""

import logging
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from src.shared.base_service import BaseService
from src.shared.api_config import api_config
from src.shared.gemini_config import gemini_config
from datetime import datetime
import asyncio
import time
from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()

class RateLimiter:
    """Simple rate limiter implementation."""
    
    def __init__(self, requests_per_minute: int = 30, batch_delay: float = 2.0):
        """Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
            batch_delay: Additional delay in seconds between batch requests
        """
        self.requests_per_minute = requests_per_minute
        self.requests = []
        self.batch_delay = batch_delay
        
    async def acquire(self, is_batch: bool = False):
        """Acquire a rate limit slot.
        
        Args:
            is_batch: Whether this is part of a batch request
        """
        now = time.time()
        
        # Remove requests older than 1 minute
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]
        
        if len(self.requests) >= self.requests_per_minute:
            # Wait until we can make another request
            wait_time = 60 - (now - self.requests[0])
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
        
        # Add additional delay for batch requests
        if is_batch:
            await asyncio.sleep(self.batch_delay)
        
        self.requests.append(now)

class SentimentService(BaseService):
    """Service for sentiment analysis using Gemini."""

    def __init__(self):
        """Initialize sentiment analysis service."""
        super().__init__("sentiment")
        self.model = None
        self.rate_limiter = RateLimiter(requests_per_minute=30, batch_delay=2.0)

    async def initialize(self) -> None:
        """Initialize the service and configure Gemini API."""
        try:
            # Initialize API configuration
            await api_config.initialize()

            # Configure Gemini model
            self.model = gemini_config.configure_model("SENTIMENT")

            self._initialized = True
            logger.info("Sentiment analysis service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize sentiment service: {str(e)}")
            raise

    async def validate_request(self, request: Dict[str, Any]) -> bool:
        """Validate sentiment analysis request.

        Args:
            request: Request to validate

        Returns:
            bool: True if request is valid
        """
        if "text" not in request and "texts" not in request:
            return False
        if "text" in request and not isinstance(request["text"], str):
            return False
        if "texts" in request and not isinstance(request["texts"], list):
            return False
        return True

    async def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a sentiment analysis request."""
        try:
            include_analysis = request.get("include_analysis", False)

            # Handle batch processing
            if "texts" in request:
                results = []
                for i, text in enumerate(request["texts"]):
                    try:
                        # Apply rate limiting with batch delay
                        await self.rate_limiter.acquire(is_batch=True)
                        result = await self._analyze_sentiment(text, include_analysis)
                        results.append(result)
                        logger.info(f"Processed batch item {i+1}/{len(request['texts'])}")
                    except Exception as e:
                        logger.error(f"Error processing batch item {i+1}: {str(e)}")
                        results.append({
                            "sentiment_score": 0.5,
                            "sentiment_label": "neutral",
                            "confidence": 0.0,
                            "error": str(e)
                        })

                return {
                    "status": "success",
                    "results": results,
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "service": self.service_name,
                        "batch_size": len(request["texts"]),
                        "successful_items": len([r for r in results if "error" not in r])
                    },
                }

            # Handle single text
            await self.rate_limiter.acquire(is_batch=False)
            text = request["text"]
            result = await self._analyze_sentiment(text, include_analysis)

            return {
                "status": "success",
                **result,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "service": self.service_name,
                },
            }

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {str(e)}")
            return {"status": "error", "error": str(e), "service": self.service_name}

    async def _analyze_sentiment(
        self, text: str, include_analysis: bool
    ) -> Dict[str, Any]:
        """Analyze sentiment of text.

        Args:
            text: Text to analyze
            include_analysis: Whether to include detailed analysis

        Returns:
            Dict[str, Any]: Sentiment analysis result
        """
        try:
            # Build prompt
            prompt = self._build_sentiment_prompt(text, include_analysis)

            # Generate response using synchronous call in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config=gemini_config.get_generation_config("SENTIMENT")
                )
            )

            # Parse response
            result = self._parse_sentiment_response(response.text)

            if include_analysis:
                # Apply rate limiting for analysis request
                await self.rate_limiter.acquire()
                analysis_prompt = self._build_analysis_prompt(text, result["sentiment_score"])
                analysis_response = await loop.run_in_executor(
                    None,
                    lambda: self.model.generate_content(
                        analysis_prompt,
                        generation_config=gemini_config.get_generation_config("SENTIMENT")
                    )
                )
                result["analysis"] = analysis_response.text.strip()

            return result

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {
                "sentiment_score": 0.5,
                "sentiment_label": "neutral",
                "confidence": 0.0
            }

    def _build_sentiment_prompt(self, text: str, include_analysis: bool) -> str:
        """Build sentiment analysis prompt.

        Args:
            text: Text to analyze
            include_analysis: Whether to include detailed analysis

        Returns:
            str: Analysis prompt
        """
        return f"""Analyze the sentiment of the following text and provide a sentiment score between -1.0 (extremely negative) and 1.0 (extremely positive).

Text: {text}

Provide the result in the following format:
Score: [sentiment score]
Label: [positive/negative/neutral]
Confidence: [confidence score between 0.0 and 1.0]

Important:
- The sentiment score should be between -1.0 and 1.0
- The label should be one of: positive, negative, neutral
- The confidence score should be between 0.0 and 1.0
- Be objective and consistent in your analysis"""

    def _build_analysis_prompt(self, text: str, sentiment_score: float) -> str:
        """Build detailed analysis prompt.

        Args:
            text: Text to analyze
            sentiment_score: Calculated sentiment score

        Returns:
            str: Analysis prompt
        """
        return f"""Given the text and its sentiment score, provide a brief analysis explaining the sentiment.

Text: {text}
Sentiment Score: {sentiment_score}

Explain:
- Key words/phrases that influenced the sentiment
- Any nuances or mixed sentiments
- The overall tone and emotional content

Keep the analysis concise but informative."""

    def _parse_sentiment_response(self, response_text: str) -> Dict[str, Any]:
        """Parse sentiment analysis response.

        Args:
            response_text: Raw response text

        Returns:
            Dict[str, Any]: Parsed sentiment result
        """
        try:
            result = {
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "confidence": 0.5
            }

            for line in response_text.split('\n'):
                line = line.strip()
                if not line:
                    continue

                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip().lower()

                    if key == 'score':
                        try:
                            score = float(value)
                            result["sentiment_score"] = max(-1.0, min(1.0, score))
                        except ValueError:
                            logger.warning(f"Failed to parse sentiment score: {value}")

                    elif key == 'label':
                        if value in ['positive', 'negative', 'neutral']:
                            result["sentiment_label"] = value

                    elif key == 'confidence':
                        try:
                            confidence = float(value)
                            result["confidence"] = max(0.0, min(1.0, confidence))
                        except ValueError:
                            logger.warning(f"Failed to parse confidence score: {value}")

            return result

        except Exception as e:
            logger.error(f"Error parsing sentiment response: {str(e)}")
            return {
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "confidence": 0.0
            }


@router.get("/health")
async def health_check():
    return {"status": "healthy"} 