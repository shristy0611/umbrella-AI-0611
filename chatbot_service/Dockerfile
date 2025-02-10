# Use Python 3.9 slim image as the base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with specific UID/GID
RUN groupadd -r appuser -g 1000 && \
    useradd -r -g appuser -u 1000 -s /sbin/nologin appuser

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create cache directory for conversation history with proper permissions
RUN mkdir -p /app/cache && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port for internal service communication only
EXPOSE 8003

# Command to run the service
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8003"] 