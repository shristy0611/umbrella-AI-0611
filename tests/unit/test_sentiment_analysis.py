import pytest
from unittest.mock import Mock, patch
from sentiment_service.src.analyzer import SentimentAnalyzer
from shared.base_service import BaseService

@pytest.fixture
def sentiment_analyzer():
    return SentimentAnalyzer()

@pytest.fixture
def sample_texts():
    return {
        "positive": "I love this product! It's amazing and works perfectly.",
        "negative": "This is terrible. I hate how poorly it performs.",
        "neutral": "The product is as described. It does what it claims.",
        "mixed": "While the interface is great, the performance is lacking.",
        "empty": "",
        "very_long": "Great " * 1000  # Test with long text
    }

@pytest.mark.asyncio
async def test_analyze_positive_sentiment(sentiment_analyzer, sample_texts):
    """Test analysis of positive text."""
    result = await sentiment_analyzer.analyze_text(sample_texts["positive"])
    
    assert isinstance(result, dict)
    assert "sentiment" in result
    assert "score" in result
    assert result["sentiment"] in ["positive", "very_positive"]
    assert 0 <= result["score"] <= 1
    assert result["score"] > 0.5

@pytest.mark.asyncio
async def test_analyze_negative_sentiment(sentiment_analyzer, sample_texts):
    """Test analysis of negative text."""
    result = await sentiment_analyzer.analyze_text(sample_texts["negative"])
    
    assert isinstance(result, dict)
    assert "sentiment" in result
    assert "score" in result
    assert result["sentiment"] in ["negative", "very_negative"]
    assert 0 <= result["score"] <= 1
    assert result["score"] < 0.5

@pytest.mark.asyncio
async def test_analyze_neutral_sentiment(sentiment_analyzer, sample_texts):
    """Test analysis of neutral text."""
    result = await sentiment_analyzer.analyze_text(sample_texts["neutral"])
    
    assert isinstance(result, dict)
    assert "sentiment" in result
    assert "score" in result
    assert result["sentiment"] == "neutral"
    assert 0.4 <= result["score"] <= 0.6

@pytest.mark.asyncio
async def test_analyze_mixed_sentiment(sentiment_analyzer, sample_texts):
    """Test analysis of text with mixed sentiment."""
    result = await sentiment_analyzer.analyze_text(sample_texts["mixed"])
    
    assert isinstance(result, dict)
    assert "sentiment" in result
    assert "score" in result
    assert "aspects" in result
    assert len(result["aspects"]) > 0
    for aspect in result["aspects"]:
        assert "text" in aspect
        assert "sentiment" in aspect
        assert "score" in aspect

@pytest.mark.asyncio
async def test_analyze_empty_text(sentiment_analyzer, sample_texts):
    """Test handling of empty text."""
    with pytest.raises(ValueError) as exc_info:
        await sentiment_analyzer.analyze_text(sample_texts["empty"])
    assert "Empty text" in str(exc_info.value)

@pytest.mark.asyncio
async def test_analyze_very_long_text(sentiment_analyzer, sample_texts):
    """Test handling of very long text."""
    result = await sentiment_analyzer.analyze_text(sample_texts["very_long"])
    
    assert isinstance(result, dict)
    assert "sentiment" in result
    assert "score" in result
    assert "truncated" in result
    assert result["truncated"] is True

@pytest.mark.asyncio
async def test_batch_analysis(sentiment_analyzer, sample_texts):
    """Test batch sentiment analysis."""
    texts = [
        {"id": "1", "text": sample_texts["positive"]},
        {"id": "2", "text": sample_texts["negative"]},
        {"id": "3", "text": sample_texts["neutral"]}
    ]
    
    results = await sentiment_analyzer.analyze_batch(texts)
    
    assert isinstance(results, list)
    assert len(results) == 3
    for result in results:
        assert "id" in result
        assert "sentiment" in result
        assert "score" in result

@pytest.mark.asyncio
async def test_process_request_with_valid_text(sentiment_analyzer, sample_texts):
    """Test processing a valid request through the service interface."""
    request_data = {
        "text": sample_texts["positive"],
        "options": {
            "include_aspects": True
        }
    }
    
    result = await sentiment_analyzer.process_request(request_data)
    
    assert isinstance(result, dict)
    assert "sentiment" in result
    assert "score" in result
    assert "aspects" in result

@pytest.mark.asyncio
async def test_process_request_with_missing_text():
    """Test processing request with missing text."""
    analyzer = SentimentAnalyzer()
    request_data = {
        "options": {}
    }
    
    with pytest.raises(ValueError) as exc_info:
        await analyzer.process_request(request_data)
    assert "Missing text" in str(exc_info.value)

@pytest.mark.asyncio
async def test_analyze_with_custom_aspects(sentiment_analyzer):
    """Test sentiment analysis with custom aspect targeting."""
    text = "The screen is bright but the battery life is poor."
    aspects = ["screen", "battery"]
    
    result = await sentiment_analyzer.analyze_text(text, aspects=aspects)
    
    assert isinstance(result, dict)
    assert "aspects" in result
    assert len(result["aspects"]) == 2
    aspect_texts = [aspect["text"].lower() for aspect in result["aspects"]]
    assert all(aspect in " ".join(aspect_texts) for aspect in aspects)

@pytest.mark.asyncio
async def test_analyze_with_confidence_scores(sentiment_analyzer, sample_texts):
    """Test that confidence scores are provided and valid."""
    result = await sentiment_analyzer.analyze_text(
        sample_texts["positive"],
        include_confidence=True
    )
    
    assert isinstance(result, dict)
    assert "confidence" in result
    assert 0 <= result["confidence"] <= 1
    assert "sentiment_scores" in result
    assert all(0 <= score <= 1 for score in result["sentiment_scores"].values()) 