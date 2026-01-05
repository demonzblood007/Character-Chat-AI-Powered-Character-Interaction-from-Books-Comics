# Multi-stage Dockerfile for Character Chat API
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads and logs directories
RUN mkdir -p uploads logs && chmod 755 uploads logs

# Expose port
EXPOSE 8000

# Default command (can be overridden)
CMD ["python", "-m", "app.main"]

