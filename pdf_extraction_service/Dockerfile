# Use Python 3.9 slim image as the base
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies and curl
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy requirements and install Python dependencies
COPY pdf_extraction_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY pdf_extraction_service/src/ src/

# Create and configure healthcheck script
RUN echo '#!/bin/bash\n\
response=$(curl -s -w "%{http_code}" http://0.0.0.0:8001/health -o /dev/null)\n\
if [ "$response" = "200" ]; then\n\
    exit 0\n\
else\n\
    echo "Health check failed with status: $response"\n\
    exit 1\n\
fi' > /healthcheck.sh \
    && chmod +x /healthcheck.sh \
    && chown appuser:appuser /healthcheck.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8001

# Command to run the service
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"] 