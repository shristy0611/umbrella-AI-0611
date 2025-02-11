# Extend base image
FROM umbrella-ai-base:latest

# Copy service code
COPY --chown=appuser:appuser src/services/chatbot /app/service
COPY --chown=appuser:appuser src/shared /app/shared

# Set service-specific environment variables
ENV SERVICE_NAME=chatbot \
    PORT=8004 \
    PYTHONPATH=/app

# Expose port
EXPOSE 8004

# Start service
CMD ["python", "-m", "uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8004"] 