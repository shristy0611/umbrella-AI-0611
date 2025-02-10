# Gemini API Integration Examples

This document provides examples of how to use the Gemini API integration modules in the UMBRELLA-AI project.

## Configuration

```python
from shared.gemini import gemini_config

# Get a configured client
client = gemini_config.get_client('gemini-pro')

# Update configuration if needed
gemini_config.update_config(
    generation_config={
        'temperature': 0.9,
        'top_p': 0.8
    },
    safety_settings={
        'harassment': 'block_medium',
        'hate_speech': 'block_high'
    }
)
```

## Text Chat

```python
from shared.gemini import GeminiTextChat

async def chat_example():
    chat = GeminiTextChat()
    await chat.start_text_chat()
    
    # Send a message
    response = await chat.send_message("Tell me about artificial intelligence")
    print(response.text)
    
    # Get chat history
    history = chat.get_chat_history()
```

## Single Image Processing

```python
from shared.gemini import GeminiSingleImage
from PIL import Image

async def process_image_example():
    processor = GeminiSingleImage()
    
    # Process image from file
    response = await processor.process_single_image(
        "path/to/image.jpg",
        "What do you see in this image?"
    )
    print(response.text)
    
    # Process PIL Image
    image = Image.open("path/to/image.jpg")
    response = await processor.process_single_image(image, "Describe this image")
```

## Multiple Image Processing

```python
from shared.gemini import GeminiMultiImage

async def process_multiple_images_example():
    processor = GeminiMultiImage()
    
    # Process multiple images
    images = [
        "path/to/image1.jpg",
        "path/to/image2.jpg",
        "https://example.com/image3.jpg"  # URL also supported
    ]
    response = await processor.process_multiple_images(
        images,
        "Compare these images"
    )
    print(response.text)
```

## File Upload and Processing

```python
from shared.gemini import GeminiFileUpload

async def process_file_example():
    processor = GeminiFileUpload()
    
    # Process a file
    response = await processor.process_file(
        "path/to/document.pdf",
        "Summarize this document",
        mime_type="application/pdf"
    )
    print(response.text)
```

## Multi-turn Chat with Context

```python
from shared.gemini import GeminiMultiTurnChat

async def multi_turn_chat_example():
    chat = GeminiMultiTurnChat()
    
    # Start chat with context
    context = "You are an expert in machine learning"
    await chat.start_chat_session(context)
    
    # Send messages
    response1 = await chat.send_message("What is deep learning?")
    print(response1.text)
    
    response2 = await chat.send_message("How does it compare to traditional ML?")
    print(response2.text)
    
    # Update context if needed
    await chat.update_context("Now focus on neural networks")
```

## Error Handling and Retries

All API calls are automatically wrapped with retry logic:
- Maximum retries: 3 (configurable)
- Exponential backoff
- Detailed error logging

Example error handling:

```python
try:
    response = await processor.process_single_image(image, prompt)
except ValueError as e:
    print(f"Invalid input: {e}")
except RuntimeError as e:
    print(f"API error: {e}")
```

## Best Practices

1. Always use environment variables for API keys
2. Handle responses asynchronously
3. Implement proper error handling
4. Check response safety ratings
5. Validate inputs before making API calls
6. Use the retry mechanism for reliability

## Testing

Run the test suite:
```bash
pytest tests/test_gemini_interactions.py -v
```

For configuration tests:
```bash
pytest tests/test_gemini_config.py -v
``` 