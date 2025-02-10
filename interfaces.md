# Agent Interfaces

This document defines the interfaces for each agent in the umbrellaAI system.

## PDF Extraction Agent
- **Input Format**: JSON
  ```json
  {
    "file_path": "string",
    "options": {
      "extract_text": "boolean",
      "extract_images": "boolean"
    }
  }
  ```
- **Output Format**: JSON
  ```json
  {
    "text": "string",
    "images": ["base64_encoded_image"]
  }
  ```
- **Communication Protocol**: REST API

## Sentiment Analysis Agent
- **Input Format**: JSON
  ```json
  {
    "text": "string"
  }
  ```
- **Output Format**: JSON
  ```json
  {
    "sentiment": "string",
    "score": "float"
  }
  ```
- **Communication Protocol**: REST API

## Recommendation Agent
- **Input Format**: JSON
  ```json
  {
    "user_id": "string",
    "history": ["item_id"]
  }
  ```
- **Output Format**: JSON
  ```json
  {
    "recommendations": ["item_id"]
  }
  ```
- **Communication Protocol**: RabbitMQ

## Chatbot Agent
- **Input Format**: JSON
  ```json
  {
    "message": "string",
    "context": "string"
  }
  ```
- **Output Format**: JSON
  ```json
  {
    "response": "string"
  }
  ```
- **Communication Protocol**: WebSocket

## RAG Scraper Agent
- **Input Format**: JSON
  ```json
  {
    "query": "string",
    "options": {
      "max_results": "integer"
    }
  }
  ```
- **Output Format**: JSON
  ```json
  {
    "results": ["string"]
  }
  ```
- **Communication Protocol**: REST API
