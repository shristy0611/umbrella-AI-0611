"""Sentiment Analysis Service Implementation."""
from typing import Dict, Any, List, Optional, Tuple
import logging

class SentimentAnalyzer:
    """Service for analyzing sentiment in text."""
    
    def __init__(self):
        """Initialize the sentiment analyzer service."""
        self.logger = logging.getLogger(__name__)
        self.max_text_length = 5000
        self.aspect_keywords = {
            "performance": ["speed", "fast", "slow", "performance", "lag"],
            "usability": ["easy", "difficult", "intuitive", "confusing", "user-friendly"],
            "reliability": ["stable", "crash", "reliable", "buggy", "consistent"],
            "features": ["feature", "functionality", "capability", "option"],
            "interface": ["interface", "ui", "design", "look", "appearance"]
        }
        self.positive_words = {
            "great", "excellent", "good", "amazing", "awesome",
            "love", "perfect", "fantastic", "wonderful", "best"
        }
        self.negative_words = {
            "bad", "poor", "terrible", "awful", "horrible",
            "hate", "worst", "unusable", "disappointing", "frustrating"
        }
    
    def _extract_aspects(
        self,
        text: str,
        custom_aspects: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Extract aspects and their sentiment from text."""
        sentences = text.lower().split('.')
        aspects = []
        
        # Use custom aspects if provided, otherwise use default aspect keywords
        aspect_dict = {}
        if custom_aspects:
            for aspect in custom_aspects:
                aspect_dict[aspect] = [aspect.lower()]
        else:
            aspect_dict = self.aspect_keywords

        for aspect, keywords in aspect_dict.items():
            relevant_sentences = []
            for sentence in sentences:
                if any(keyword in sentence for keyword in keywords):
                    relevant_sentences.append(sentence)
            
            if relevant_sentences:
                score, confidence = self._analyze_aspect_sentiment(relevant_sentences)
                aspects.append({
                    "aspect": aspect,
                    "sentiment": self._score_to_label(score),
                    "score": score,
                    "confidence": confidence,
                    "text": ". ".join(relevant_sentences)
                })

        return aspects

    def _analyze_aspect_sentiment(self, sentences: List[str]) -> Tuple[float, float]:
        """Analyze sentiment for specific sentences."""
        total_score = 0
        total_words = 0
        confidence = 0

        for sentence in sentences:
            words = sentence.split()
            sentence_score = 0
            relevant_words = 0

            for word in words:
                if word in self.positive_words:
                    sentence_score += 1
                    relevant_words += 1
                elif word in self.negative_words:
                    sentence_score -= 1
                    relevant_words += 1

            if relevant_words > 0:
                total_score += sentence_score
                total_words += relevant_words
                confidence += relevant_words / len(words)

        if total_words == 0:
            return 0.5, 0.0  # Neutral sentiment with zero confidence

        avg_score = (total_score / total_words + 1) / 2  # Normalize to [0,1]
        avg_confidence = confidence / len(sentences)

        return avg_score, avg_confidence

    def _score_to_label(self, score: float) -> str:
        """Convert sentiment score to label."""
        if score >= 0.8:
            return "very_positive"
        elif score >= 0.6:
            return "positive"
        elif score >= 0.4:
            return "neutral"
        elif score >= 0.2:
            return "negative"
        else:
            return "very_negative"

    async def analyze_text(
        self,
        text: str,
        aspects: Optional[List[str]] = None,
        include_confidence: bool = False
    ) -> Dict[str, Any]:
        """Analyze sentiment in text."""
        if not text:
            raise ValueError("Empty text")

        # Handle text truncation
        truncated = False
        if len(text) > self.max_text_length:
            text = text[:self.max_text_length]
            truncated = True

        # Extract aspects if requested
        aspect_results = self._extract_aspects(text, aspects)
        
        # Calculate overall sentiment
        sentences = text.lower().split('.')
        overall_score, confidence = self._analyze_aspect_sentiment(sentences)
        
        result = {
            "sentiment": self._score_to_label(overall_score),
            "score": overall_score,
            "sentiment_scores": {
                "positive": overall_score,
                "negative": 1 - overall_score
            }
        }

        # Add aspects if found
        if aspect_results:
            result["aspects"] = aspect_results

        # Add confidence if requested
        if include_confidence:
            result["confidence"] = confidence

        # Add truncation info
        if truncated:
            result["truncated"] = True
            result["original_length"] = len(text)

        return result

    async def analyze_batch(
        self,
        texts: List[str],
        aspects: Optional[List[str]] = None,
        include_confidence: bool = False
    ) -> List[Dict[str, Any]]:
        """Analyze sentiment for multiple texts."""
        results = []
        for text in texts:
            try:
                if isinstance(text, dict):
                    text_id = text.get("id")
                    content = text.get("text", "")
                else:
                    text_id = None
                    content = text

                result = await self.analyze_text(content, aspects, include_confidence)
                results.append({
                    "id": text_id,
                    "status": "success",
                    **result
                })
            except Exception as e:
                self.logger.error(f"Error analyzing text: {str(e)}")
                results.append({
                    "id": text_id,
                    "status": "error",
                    "error": str(e)
                })
        return results

    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming sentiment analysis request."""
        if "text" not in request_data:
            raise ValueError("Missing text")

        text = request_data["text"]
        aspects = request_data.get("aspects")
        include_confidence = request_data.get("include_confidence", False)
        include_aspects = request_data.get("options", {}).get("include_aspects", True)

        result = await self.analyze_text(text, aspects if include_aspects else None, include_confidence)
        
        # Always include aspects if include_aspects is True
        if include_aspects and "aspects" not in result:
            result["aspects"] = []
            
        return result 