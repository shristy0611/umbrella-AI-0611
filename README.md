# UMBRELLA-AI

UMBRELLA-AI is a multi-agent AI system for document analysis and interaction, powered by Google's Gemini API.

## Features

- PDF text extraction and analysis
- Sentiment analysis
- RAG-based document retrieval
- Interactive chat with context awareness
- Microservices architecture
- Docker containerization
- Secure API key management with AWS Secrets Manager

## Architecture

The system consists of several microservices:

- **PDF Extraction Service**: Extracts text and metadata from PDF documents
- **Sentiment Analysis Service**: Analyzes sentiment in text
- **RAG Scraper Service**: Retrieves relevant documents and context
- **Chatbot Service**: Handles interactive conversations
- **API Gateway**: Main entry point for client applications

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Google Gemini API key
- AWS account with Secrets Manager access (for production)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/umbrella-ai.git
cd umbrella-ai
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   - For development, copy `.env.example` to `.env` and fill in your API keys
   - For production, configure AWS Secrets Manager (see below)

## API Key Management

### Development Environment

In development, API keys are managed through environment variables. Copy `.env.example` to `.env` and configure:

```bash
# Gemini API Keys for Different Services
GEMINI_API_KEY_OCR=your_ocr_api_key_here
GEMINI_API_KEY_RECOMMENDATION=your_recommendation_api_key_here
GEMINI_API_KEY_SENTIMENT=your_sentiment_api_key_here
GEMINI_API_KEY_CHATBOT=your_chatbot_api_key_here

# Gemini API Keys for Orchestration
ORCHESTRATOR_API_KEY=your_orchestrator_api_key_here
TASK_DECOMPOSER_API_KEY=your_task_decomposer_api_key_here
RESULT_VERIFIER_API_KEY=your_result_verifier_api_key_here

# Default Gemini API Key
GEMINI_API_KEY=your_default_api_key_here
```

### Production Environment

In production, API keys are securely managed using AWS Secrets Manager:

1. Set up AWS credentials:
```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_REGION=your_aws_region
AWS_SECRET_NAME=umbrella/gemini/api-keys  # Default secret name
```

2. Create a secret in AWS Secrets Manager with the following structure:
```json
{
    "ocr_api_key": "your_ocr_api_key",
    "recommendation_api_key": "your_recommendation_api_key",
    "sentiment_api_key": "your_sentiment_api_key",
    "chatbot_api_key": "your_chatbot_api_key",
    "orchestrator_api_key": "your_orchestrator_api_key",
    "task_decomposer_api_key": "your_task_decomposer_api_key",
    "result_verifier_api_key": "your_result_verifier_api_key",
    "default_api_key": "your_default_api_key"
}
```

3. Configure AWS IAM roles with appropriate permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:PutSecretValue",
                "secretsmanager:RotateSecret"
            ],
            "Resource": "arn:aws:secretsmanager:*:*:secret:umbrella/gemini/*"
        }
    ]
}
```

### Key Rotation

API keys can be rotated automatically:

```python
from shared.gemini.config import gemini_config, ServiceType

# Rotate a specific service key
gemini_config.rotate_api_key(ServiceType.OCR)

# Keys are automatically rotated every 30 days in production
```

## Development

### Prerequisites
- Python 3.9+
- Docker and Docker Compose
- Gemini API key

### Setup
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and configure your environment variables
4. Run the application: `python app.py`

## Docker Deployment

### Local Development
1. Build the images: `docker-compose build`
2. Start the services: `docker-compose up -d`
3. Check logs: `docker-compose logs -f`

### Production
1. Configure production environment variables
2. Deploy using Docker Compose: `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d`

## Contributing
1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -am 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository.