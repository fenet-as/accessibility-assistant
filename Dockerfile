# ALX Digital Bridge Accessibility Assistant - Production Container
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY assistant/ /app/assistant/
COPY savanna-static/ /app/savanna-static/
COPY docs/ /app/docs/
COPY .env.example /app/.env.example

# Expose default HTTP port
EXPOSE 8000

# Health check to ensure zero-downtime container orchestration
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Start FastAPI / Uvicorn server
CMD ["python", "-m", "uvicorn", "assistant.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
