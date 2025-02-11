# Extend base image
FROM umbrella-ai-base:latest

# Install additional dependencies for PDF processing
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*
USER appuser

# Copy service code
COPY --chown=appuser:appuser src/services/pdf_extraction /app/service
COPY --chown=appuser:appuser src/shared /app/shared

# Set service-specific environment variables
ENV SERVICE_NAME=pdf_extraction \
    PORT=8001

# Expose port
EXPOSE 8001

# Start service
CMD ["python", "-m", "uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8001"] 