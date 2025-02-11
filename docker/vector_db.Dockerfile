# Extend base image
FROM umbrella-ai-base:latest

# Copy service code
COPY --chown=appuser:appuser src/services/vector_db /app/service
COPY --chown=appuser:appuser src/shared /app/shared

# Set service-specific environment variables
ENV SERVICE_NAME=vector_db \
    PORT=8005 \
    VECTOR_DB_PATH=/data/vector_db

# Create data directory
USER root
RUN mkdir -p /data/vector_db && chown -R appuser:appuser /data
USER appuser

# Download sentence transformer model during build
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('all-MiniLM-L6-v2')"

# Volume for persistent storage
VOLUME ["/data/vector_db"]

# Expose port
EXPOSE 8005

# Start service
CMD ["python", "-m", "uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8005"] 