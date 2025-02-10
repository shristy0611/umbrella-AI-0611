# 🌂 UMBRELLA-AI

## Overview

UMBRELLA-AI is a sophisticated multi-agent AI system designed to provide enterprise-grade AI capabilities at an affordable cost for small and medium-sized businesses. The system leverages Google's Gemini API and modern microservices architecture to deliver automated document analysis, sentiment analysis, recommendations, and intelligent chatbot capabilities.

## 🚀 Key Features

- **Document Analysis**: Automated PDF parsing and data extraction
- **Sentiment Analysis**: Advanced text sentiment understanding
- **Smart Recommendations**: AI-powered product and action suggestions
- **Interactive Chatbot**: Context-aware conversational interface
- **Web Intelligence**: RAG-based web scraping and information synthesis

## 🏗️ Architecture

### Core Components

1. **Orchestrator Service**
   - Central coordinator for all AI agents
   - Task decomposition and distribution
   - Request routing and response aggregation

2. **Specialized AI Agents**
   - **PDF Extraction Agent**: Document parsing and structured data extraction
   - **Sentiment Analysis Agent**: Text sentiment and emotion analysis
   - **Recommendation Agent**: Intelligent suggestion system
   - **Chatbot Agent**: Natural language interaction handler
   - **RAG Scraper Agent**: Web data collection and processing

3. **Infrastructure**
   - Docker containerization for each service
   - AWS cloud deployment
   - Secure API management
   - Vector database for efficient data storage

## 🛠️ Development Setup

### Prerequisites

- Python 3.8+
- Docker and Docker Compose
- AWS Account (for deployment)
- Gemini API access

### Environment Setup

1. **Clone the Repository**
   ```bash
   git clone [repository-url]
   cd umbrella-ai
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   - Copy `.env.example` to `.env`
   ```bash
   cp .env.example .env
   ```
   - Configure the following environment variables in `.env`:
     - **Gemini API Keys** (Required for AI Services)
       - `GEMINI_API_KEY_OCR`: For document processing
       - `GEMINI_API_KEY_RECOMMENDATION`: For recommendation engine
       - `GEMINI_API_KEY_SENTIMENT`: For sentiment analysis
       - `GEMINI_API_KEY_CHATBOT`: For chatbot service
       - `ORCHESTRATOR_API_KEY`: For task orchestration
       - `TASK_DECOMPOSER_API_KEY`: For task decomposition
       - `RESULT_VERIFIER_API_KEY`: For result verification
     - **Database Configuration**
       - `MONGODB_URI`: MongoDB connection string
       - `VECTOR_DB_PATH`: Path to vector database storage
     - **AWS Configuration** (Required for Production)
       - `AWS_ACCESS_KEY_ID`: AWS access key
       - `AWS_SECRET_ACCESS_KEY`: AWS secret key
       - `AWS_REGION`: AWS region for deployment
     - **API Configuration**
       - `API_HOST`: API host address
       - `API_PORT`: API port number
       - `API_DEBUG`: Debug mode flag
     - **Security**
       - `JWT_SECRET_KEY`: Secret key for JWT tokens
       - `JWT_ALGORITHM`: JWT encryption algorithm
       - `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time

   > ⚠️ **Important**: Never commit the `.env` file to version control. It contains sensitive credentials and should be kept secure.

5. **Verify Environment Setup**
   ```bash
   python tests/unit/test_env.py
   ```

6. **Start Development Services**
   ```bash
   docker-compose up -d
   ```

## 📁 Project Structure

```
umbrella_ai/
├── src/                    # Source code
│   ├── orchestrator/       # Main orchestration service
│   ├── pdf_extraction/     # PDF processing agent
│   ├── sentiment/          # Sentiment analysis agent
│   ├── recommendation/     # Recommendation agent
│   ├── chatbot/           # Chatbot service
│   └── rag_scraper/       # Web scraping agent
├── docs/                   # Documentation
│   ├── architecture/      # System design docs
│   └── api/               # API specifications
├── tests/                 # Test suites
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── docker/                # Docker configurations
```

## 🧪 Testing

```bash
# Run unit tests
pytest tests/unit

# Run integration tests
pytest tests/integration

# Run end-to-end tests
pytest tests/e2e
```

## 📚 Documentation

- Detailed documentation is available in the `docs/` directory
- API specifications and examples in `docs/api/`
- Architecture diagrams in `docs/architecture/`

## 🔒 Security Notes

- All sensitive credentials should be stored in `.env` (not committed to Git)
- API keys should be managed through secure key rotation
- Follow the principle of least privilege for service accounts

## 🤝 Contributing

1. Create a feature branch from `dev`
2. Make your changes
3. Write/update tests
4. Submit a pull request to `dev`

## 📄 License

[License details to be added]

---

For more information or support, please refer to the documentation in the `docs/` directory. 