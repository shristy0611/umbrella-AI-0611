"""Setup file for UMBRELLA-AI package."""

from setuptools import setup, find_packages

setup(
    name="umbrella-ai",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "google-genai>=0.2.0",
        "langchain>=0.1.0",
        "pydantic>=2.5.0",
        "transformers>=4.36.0",
        "torch>=2.1.0",
        "sentence-transformers>=2.2.2",
        "playwright>=1.40.0",
        "beautifulsoup4>=4.12.0",
        "requests>=2.31.0",
        "aiohttp>=3.9.0",
        "PyPDF2>=3.0.0",
        "pdf2image>=1.16.3",
        "pytesseract>=0.3.10",
        "chromadb>=0.4.18",
        "pymongo>=4.6.0",
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "python-multipart==0.0.7",
        "httpx>=0.18.2",
        "boto3>=1.34.0",
        "python-dotenv>=1.0.0",
        "pytest>=6.2.5",
        "pytest-asyncio>=0.15.1",
        "pytest-cov>=2.12.1",
    ],
    python_requires=">=3.9",
    package_data={
        "": ["*.json", "*.yaml", "*.yml"]
    }
) 