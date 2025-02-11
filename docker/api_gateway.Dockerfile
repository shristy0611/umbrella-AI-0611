# Use base image
FROM umbrella-ai-base:latest

# Copy service code
COPY --chown=appuser:appuser src/services/api_gateway /app/service
COPY --chown=appuser:appuser src/shared /app/shared

# Set environment variables
ENV PORT=8000

# Expose port
EXPOSE ${PORT}

# Set working directory
WORKDIR /app/service

# Run the service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 