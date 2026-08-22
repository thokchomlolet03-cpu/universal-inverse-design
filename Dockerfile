# ==============================================================================
# Universal Inverse Design Engine — Serverless Microservice Dockerfile
# Optimized for Google Cloud Run (Scale-to-Zero Free Tier Deployment)
# ==============================================================================

FROM python:3.11-slim as runtime

WORKDIR /app

# Set production environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    PYTHONPATH=/app/src

# Install essential system utilities and clean apt cache to minimize image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy build files and install Python dependencies
COPY pyproject.toml /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy application source code and data directories
COPY src/ /app/src/
COPY data/ /app/data/

# Expose standard Cloud Run port
EXPOSE 8080

# Configure health check for Cloud Run container probes
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start FastAPI server with Uvicorn
CMD ["uvicorn", "uid_engine.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
