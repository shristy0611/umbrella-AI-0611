"""Recommendation service implementation."""

import logging
from typing import Dict, Any, List
import google.generativeai as genai
from src.shared.base_service import BaseService
from src.shared.api_config import api_config
from src.shared.gemini_config import gemini_config
from datetime import datetime
from fastapi import APIRouter
import asyncio
import re

logger = logging.getLogger(__name__)

router = APIRouter()


class RecommendationService(BaseService):
    """Service for generating content recommendations."""

    def __init__(self):
        """Initialize recommendation service."""
        super().__init__("recommendation")
        self.model = None

    async def initialize(self) -> None:
        """Initialize the service and configure Gemini API."""
        try:
            # Initialize API configuration
            await api_config.initialize()

            # Configure Gemini model
            self.model = gemini_config.configure_model("RECOMMENDATION")

            self._initialized = True
            logger.info("Recommendation service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize recommendation service: {str(e)}")
            raise

    async def cleanup(self) -> None:
        """Clean up service resources."""
        self.model = None
        await super().cleanup()

    async def validate_request(self, request: Dict[str, Any]) -> bool:
        """Validate recommendation request.

        Args:
            request: Request to validate

        Returns:
            bool: True if request is valid
        """
        if "context" not in request or "user_preferences" not in request:
            return False
        return True

    async def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a recommendation request.

        Args:
            request: Dictionary containing:
                - context: Current context (e.g., viewed content, history)
                - user_preferences: User preferences and interests
                - num_recommendations: Number of recommendations to generate (default: 5)
                - recommendation_type: Type of recommendations (content, topic, etc.)

        Returns:
            Dict[str, Any]: Recommendation results

        Raises:
            ValueError: If request is invalid or processing fails
        """
        try:
            # Get request parameters
            context = request["context"]
            preferences = request["user_preferences"]
            num_recommendations = request.get("num_recommendations", 5)
            rec_type = request.get("recommendation_type", "content")

            # Build prompt
            prompt = self._build_recommendation_prompt(
                context, preferences, num_recommendations, rec_type
            )

            # Get recommendations with retry
            recommendations = await api_config.execute_with_retry(
                self._generate_recommendations,
                prompt,
                generation_config=gemini_config.get_generation_config("RECOMMENDATION")
            )

            return {
                "status": "success",
                "recommendations": recommendations,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "service": self.service_name,
                    "type": rec_type,
                },
            }

        except Exception as e:
            logger.error(f"Recommendation generation failed: {str(e)}")
            return {"status": "error", "error": str(e), "service": self.service_name}

    async def _generate_recommendations(
        self, prompt: str, generation_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations using Gemini.

        Args:
            prompt: Recommendation prompt
            generation_config: Generation configuration

        Returns:
            List[Dict[str, Any]]: List of recommendations
        """
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
        )

        logger.info("Raw response from model:")
        logger.info(response.text)

        # Parse response into recommendations
        try:
            # First try to parse as direct JSON
            recommendations = self._parse_recommendations(response.text)
            if recommendations:
                return recommendations

            # If direct parsing fails, try to extract JSON from the response
            import re
            json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
            if json_match:
                recommendations = self._parse_recommendations(json_match.group(0))
                if recommendations:
                    return recommendations

            # If still no valid JSON, create structured recommendations from the text
            logger.warning("Could not parse JSON response, creating structured format")
            lines = response.text.split('\n')
            current_rec = {}
            recommendations = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    if current_rec and 'title' in current_rec:  # Only add if we have at least a title
                        logger.debug(f"Adding recommendation: {current_rec}")
                        recommendations.append(current_rec.copy())  # Use copy to avoid reference issues
                        current_rec = {}
                    continue
                
                # Try to extract key-value pairs
                if ':' in line:
                    key, value = [part.strip() for part in line.split(':', 1)]
                    key = key.lower()
                    
                    if key == 'title':
                        if current_rec and 'title' in current_rec:  # If we already have a recommendation
                            logger.debug(f"Adding recommendation: {current_rec}")
                            recommendations.append(current_rec.copy())
                            current_rec = {}
                        current_rec['title'] = value
                        logger.debug(f"Started new recommendation with title: {value}")
                    
                    elif key == 'relevance score' or key == 'relevance_score':
                        try:
                            # Clean the value and try to convert to float
                            cleaned_value = value.strip()
                            logger.info(f"Processing relevance score: {cleaned_value}")
                            
                            # Try direct conversion first
                            try:
                                score = float(cleaned_value)
                                current_rec['relevance_score'] = max(0.0, min(1.0, score))
                                logger.info(f"Successfully parsed relevance score: {current_rec['relevance_score']}")
                            except ValueError:
                                # Try to extract number using regex
                                score_match = re.search(r'(\d+\.?\d*|\.\d+)', cleaned_value)
                                if score_match:
                                    score = float(score_match.group(1))
                                    current_rec['relevance_score'] = max(0.0, min(1.0, score))
                                    logger.info(f"Successfully parsed relevance score using regex: {current_rec['relevance_score']}")
                                else:
                                    logger.warning(f"Could not extract numeric value from: {cleaned_value}")
                                    current_rec['relevance_score'] = 0.5
                        except Exception as e:
                            logger.error(f"Error processing relevance score: {str(e)}")
                            current_rec['relevance_score'] = 0.5
                    
                    elif key == 'tags':
                        try:
                            # Clean and split the tags
                            tags_str = value.strip('[]')
                            tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                            current_rec[key] = tags
                            logger.debug(f"Added tags: {tags}")
                        except Exception as e:
                            logger.error(f"Error parsing tags: {str(e)}")
                            current_rec[key] = []
                    
                    else:  # description, reasoning, or other fields
                        current_rec[key] = value
                        logger.debug(f"Added {key}: {value}")
            
            # Add the last recommendation if it exists and has a title
            if current_rec and 'title' in current_rec:
                logger.debug(f"Adding final recommendation: {current_rec}")
                recommendations.append(current_rec.copy())
            
            if not recommendations:
                logger.warning("No recommendations were parsed from the response")
                return [{
                    'title': 'Fallback Recommendation',
                    'description': 'Could not parse model response properly',
                    'relevance_score': 0.5,
                    'tags': [],
                    'reasoning': 'System fallback due to parsing error'
                }]

            logger.info(f"Successfully parsed {len(recommendations)} recommendations")
            return recommendations

        except Exception as e:
            logger.error(f"Failed to process recommendations: {str(e)}")
            return [{
                'title': 'Error Recommendation',
                'description': 'An error occurred while processing recommendations',
                'relevance_score': 0.0,
                'tags': [],
                'reasoning': f'Error: {str(e)}'
            }]

    def _build_recommendation_prompt(
        self,
        context: Dict[str, Any],
        preferences: Dict[str, Any],
        num_recommendations: int,
        rec_type: str,
    ) -> str:
        """Build recommendation prompt.

        Args:
            context: Current context
            preferences: User preferences
            num_recommendations: Number of recommendations
            rec_type: Type of recommendations

        Returns:
            str: Recommendation prompt
        """
        return f"""Based on the following context and preferences, generate {num_recommendations} {rec_type} recommendations.

Context:
{self._format_dict(context)}

User Preferences:
{self._format_dict(preferences)}

Please provide exactly {num_recommendations} recommendations. For each recommendation, use this exact format:

Title: [Title of the recommendation]
Description: [Brief but informative description]
Relevance Score: [A number between 0.0 and 1.0, e.g., 0.85]
Tags: [comma-separated list of relevant tags]
Reasoning: [Clear explanation of why this is recommended]

Important:
- The relevance score must be a decimal number between 0.0 and 1.0
- Higher relevance scores (closer to 1.0) indicate better matches
- Separate each recommendation with a blank line
- Use the exact format shown above"""

    def _format_dict(self, data: Dict[str, Any]) -> str:
        """Format dictionary for prompt.

        Args:
            data: Dictionary to format

        Returns:
            str: Formatted string
        """
        return "\n".join(f"- {k}: {v}" for k, v in data.items())

    def _parse_recommendations(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse recommendations from response.

        Args:
            response_text: Raw response from model

        Returns:
            List[Dict[str, Any]]: Structured recommendations
        """
        try:
            # The model should return JSON-formatted array
            import json
            return json.loads(response_text)
        except Exception as e:
            logger.error(f"Failed to parse recommendations: {str(e)}")
            # Return empty list if parsing fails
            return []


@router.get("/health")
async def health_check():
    return {"status": "healthy"} 