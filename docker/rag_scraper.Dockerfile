# Extend base image
FROM umbrella-ai-base:latest

# Copy service code
COPY --chown=appuser:appuser src/services/rag_scraper /app/service
COPY --chown=appuser:appuser src/shared /app/shared

# Install additional dependencies
RUN pip install --no-cache-dir \
    beautifulsoup4==4.12.2 \
    httpx==0.26.0

# Set service-specific environment variables
ENV SERVICE_NAME=rag_scraper \
    PORT=8003 \
    PYTHONPATH=/app

# Expose port
EXPOSE 8003

# Start service
CMD ["python", "-m", "uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8003"] 