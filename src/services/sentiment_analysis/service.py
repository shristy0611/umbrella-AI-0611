"""Sentiment analysis service implementation."""

import os
from typing import Dict, Any, List
import google.generativeai as genai
import logging
from datetime import datetime

from src.shared.base_service import BaseService
from src.shared.api_config import api_config

logger = logging.getLogger(__name__)

class SentimentAnalysisService(BaseService):
    """Service for analyzing sentiment in text."""
    
    def __init__(self):
        """Initialize sentiment analysis service."""
        super().__init__("sentiment_analysis")
        self.model = None
    
    async def initialize(self) -> None:
        """Initialize the service and configure Gemini API."""
        try:
            # Initialize API configuration
            await api_config.initialize()
            
            # Get API key for sentiment analysis service
            api_key = await api_config.get_api_key("SENTIMENT")
            
            # Configure Gemini
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            
            await super().initialize()
            logger.info("Sentiment analysis service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize sentiment analysis service: {str(e)}")
            raise
    
    async def cleanup(self) -> None:
        """Clean up service resources."""
        self.model = None
        await super().cleanup()
    
    async def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process sentiment analysis request.
        
        Args:
            request: Dictionary containing:
                - text: Text to analyze
                - granularity: Analysis granularity (document, paragraph, sentence)
                - aspects: Optional list of aspects to analyze
                
        Returns:
            Dict[str, Any]: Analysis results
            
        Raises:
            ValueError: If request is invalid or processing fails
        """
        try:
            # Get parameters
            text = request["text"]
            granularity = request.get("granularity", "document")
            aspects = request.get("aspects", [])
            
            results = {
                "sentiment": {},
                "aspects": {}
            }
            
            # Analyze overall sentiment with retry
            if granularity == "document":
                results["sentiment"] = await api_config.execute_with_retry(
                    self._analyze_sentiment,
                    text
                )
            elif granularity == "paragraph":
                paragraphs = text.split("\n\n")
                results["sentiment"] = [
                    await api_config.execute_with_retry(
                        self._analyze_sentiment,
                        p
                    )
                    for p in paragraphs if p.strip()
                ]
            elif granularity == "sentence":
                sentences = text.split(".")
                results["sentiment"] = [
                    await api_config.execute_with_retry(
                        self._analyze_sentiment,
                        s
                    )
                    for s in sentences if s.strip()
                ]
            else:
                raise ValueError(f"Invalid granularity: {granularity}")
            
            # Analyze aspect-specific sentiment
            if aspects:
                for aspect in aspects:
                    results["aspects"][aspect] = await api_config.execute_with_retry(
                        self._analyze_aspect,
                        text,
                        aspect
                    )
            
            return {
                "status": "success",
                "results": results,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "service": self.service_name,
                    "granularity": granularity
                }
            }
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "service": self.service_name
            }
    
    async def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict[str, Any]: Sentiment analysis
        """
        prompt = self._create_sentiment_prompt(text)
        response = await self.model.generate_content(prompt)
        
        try:
            # Parse structured response
            analysis = response.text.strip()
            if not analysis:
                raise ValueError("Empty response from model")
            
            # Extract sentiment score and label
            if "positive" in analysis.lower():
                score = 0.8
                label = "positive"
            elif "negative" in analysis.lower():
                score = 0.2
                label = "negative"
            else:
                score = 0.5
                label = "neutral"
            
            # Extract confidence and key phrases
            confidence = 0.9  # TODO: Implement proper confidence scoring
            key_phrases = self._extract_key_phrases(analysis)
            
            return {
                "score": score,
                "label": label,
                "confidence": confidence,
                "key_phrases": key_phrases,
                "analysis": analysis
            }
            
        except Exception as e:
            raise ValueError(f"Failed to parse sentiment analysis: {str(e)}")
    
    async def _analyze_aspect(self, text: str, aspect: str) -> Dict[str, Any]:
        """Analyze sentiment for specific aspect.
        
        Args:
            text: Text to analyze
            aspect: Aspect to analyze
            
        Returns:
            Dict[str, Any]: Aspect sentiment analysis
        """
        prompt = self._create_aspect_prompt(text, aspect)
        response = await self.model.generate_content(prompt)
        
        try:
            analysis = response.text.strip()
            if not analysis:
                raise ValueError("Empty response from model")
            
            # Extract sentiment for aspect
            if "positive" in analysis.lower():
                score = 0.8
                label = "positive"
            elif "negative" in analysis.lower():
                score = 0.2
                label = "negative"
            else:
                score = 0.5
                label = "neutral"
            
            return {
                "score": score,
                "label": label,
                "analysis": analysis
            }
            
        except Exception as e:
            raise ValueError(f"Failed to parse aspect analysis: {str(e)}")
    
    def _create_sentiment_prompt(self, text: str) -> str:
        """Create prompt for sentiment analysis.
        
        Args:
            text: Text to analyze
            
        Returns:
            str: Analysis prompt
        """
        return f"""Analyze the sentiment of the following text. Consider the overall tone, emotion, and key phrases that indicate sentiment. Provide a detailed analysis:

Text: {text}

Please provide:
1. Overall sentiment (positive, negative, or neutral)
2. Key phrases that indicate sentiment
3. Brief explanation of the analysis"""
    
    def _create_aspect_prompt(self, text: str, aspect: str) -> str:
        """Create prompt for aspect-specific analysis.
        
        Args:
            text: Text to analyze
            aspect: Aspect to analyze
            
        Returns:
            str: Analysis prompt
        """
        return f"""Analyze the sentiment specifically related to the aspect "{aspect}" in the following text:

Text: {text}

Please provide:
1. Sentiment towards {aspect} (positive, negative, or neutral)
2. Brief explanation of why"""
    
    def _extract_key_phrases(self, analysis: str) -> List[str]:
        """Extract key phrases from analysis.
        
        Args:
            analysis: Analysis text
            
        Returns:
            List[str]: Key phrases
        """
        # TODO: Implement more sophisticated key phrase extraction
        phrases = []
        lines = analysis.split("\n")
        for line in lines:
            if "key phrase" in line.lower() or ":" in line:
                phrase = line.split(":")[-1].strip()
                if phrase:
                    phrases.append(phrase)
        return phrases[:5]  # Return top 5 phrases 