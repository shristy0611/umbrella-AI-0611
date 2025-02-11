# Extend base image
FROM umbrella-ai-base:latest

# Copy service code
COPY --chown=appuser:appuser src/services/sentiment_analysis /app/service
COPY --chown=appuser:appuser src/shared /app/shared

# Set service-specific environment variables
ENV SERVICE_NAME=sentiment_analysis \
    PORT=8002 \
    PYTHONPATH=/app

# Expose port
EXPOSE 8002

# Start service
CMD ["python", "-m", "uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8002"]