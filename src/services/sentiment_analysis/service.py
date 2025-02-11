"""Sentiment analysis service for UMBRELLA-AI."""

import logging
import asyncio
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from src.shared.base_service import BaseService
from src.shared.api_config import api_config
from src.shared.gemini_config import gemini_config
from datetime import datetime
from fastapi import APIRouter
import json
import re

logger = logging.getLogger(__name__)

router = APIRouter()


class SentimentAnalysisService(BaseService):
    """Service for sentiment analysis using Gemini."""

    def __init__(self):
        """Initialize sentiment analysis service."""
        super().__init__("sentiment_analysis")
        self.model = None

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
            logger.error(f"Failed to initialize sentiment analysis service: {str(e)}")
            raise

    async def cleanup(self) -> None:
        """Clean up service resources."""
        self.model = None
        await super().cleanup()

    async def health_check(self) -> Dict[str, str]:
        """Check service health.
        
        Returns:
            Dict[str, str]: Health status
        """
        return {
            "status": "healthy" if self._initialized and self.model is not None else "unhealthy"
        }

    async def validate_request(self, request: Dict[str, Any]) -> bool:
        """Validate sentiment analysis request.

        Args:
            request: Request to validate

        Returns:
            bool: True if request is valid
        """
        if "text" not in request:
            return False
        if not isinstance(request["text"], str):
            return False
        return True

    async def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a sentiment analysis request.

        Args:
            request: Dictionary containing:
                - text: Text to analyze
                - include_analysis: Whether to include detailed analysis (default: False)

        Returns:
            Dict[str, Any]: Analysis results

        Raises:
            ValueError: If request is invalid or processing fails
        """
        try:
            # Get request parameters
            text = request["text"]
            include_analysis = request.get("include_analysis", False)

            # Analyze sentiment
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
                # Generate detailed analysis
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
            raise

    def _build_sentiment_prompt(self, text: str, include_analysis: bool) -> str:
        """Build sentiment analysis prompt.

        Args:
            text: Text to analyze
            include_analysis: Whether to include detailed analysis

        Returns:
            str: Generated prompt
        """
        prompt = f"""Analyze the sentiment of the following text and return a JSON object with:
1. sentiment_score: A float between -1.0 (very negative) and 1.0 (very positive)
2. sentiment_label: One of ["negative", "neutral", "positive"]

Text to analyze:
{text}

Format your response as valid JSON. Example:
{{
    "sentiment_score": 0.8,
    "sentiment_label": "positive"
}}"""

        return prompt

    def _build_analysis_prompt(self, text: str, sentiment_score: float) -> str:
        """Build detailed analysis prompt.

        Args:
            text: Text to analyze
            sentiment_score: Previously calculated sentiment score

        Returns:
            str: Generated prompt
        """
        return f"""Given the text and its sentiment score of {sentiment_score}, provide a detailed analysis explaining:
1. Key words/phrases that influenced the sentiment
2. Any nuances or mixed sentiments
3. Overall tone and emotional content

Text to analyze:
{text}

Provide your analysis in a clear, concise format."""

    def _parse_sentiment_response(self, response_text: str) -> Dict[str, Any]:
        """Parse sentiment analysis response.

        Args:
            response_text: Raw response text

        Returns:
            Dict[str, Any]: Parsed sentiment result
        """
        try:
            # Try to parse as JSON
            result = json.loads(response_text)
            
            # Validate required fields
            if "sentiment_score" not in result or "sentiment_label" not in result:
                raise ValueError("Missing required fields in response")

            # Ensure score is float between -1 and 1
            score = float(result["sentiment_score"])
            result["sentiment_score"] = max(-1.0, min(1.0, score))

            # Validate sentiment label
            valid_labels = ["negative", "neutral", "positive"]
            if result["sentiment_label"] not in valid_labels:
                result["sentiment_label"] = "neutral"

            return result

        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract values using regex
            score_match = re.search(r'sentiment_score"?\s*:\s*(-?\d+\.?\d*)', response_text)
            label_match = re.search(r'sentiment_label"?\s*:\s*"(\w+)"', response_text)

            if not score_match or not label_match:
                raise ValueError("Could not parse sentiment values from response")

            score = float(score_match.group(1))
            label = label_match.group(1)

            return {
                "sentiment_score": max(-1.0, min(1.0, score)),
                "sentiment_label": label if label in ["negative", "neutral", "positive"] else "neutral"
            }


@router.get("/health")
async def health_check():
    return {"status": "healthy"}
