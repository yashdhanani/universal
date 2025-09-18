# Lightweight Python image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps: ffmpeg for merging, CA certs, curl for basic diagnostics
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ffmpeg ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the whole application
COPY . .

# Ensure common directories exist
RUN mkdir -p downloads logs cache

EXPOSE 8000

# Default command runs API (compose overrides for worker)
CMD ["uvicorn", "main_api:APP", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]