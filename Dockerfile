# GlueSync CLI Docker Image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY gluesync_cli.py .
COPY config.json .

# Create directories for configs and data
RUN mkdir -p /app/config /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV GLUESYNC_CONFIG_PATH=/app/config/config.json
ENV GLUESYNC_ENV_PATH=/app/config/.env

# Create entrypoint script
RUN echo '#!/bin/bash\n\
if [ ! -f "$GLUESYNC_ENV_PATH" ]; then\n\
    echo "Warning: .env file not found at $GLUESYNC_ENV_PATH"\n\
    echo "Please mount your .env file to /app/config/.env"\n\
fi\n\
exec python /app/gluesync_cli.py "$@"' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Default command
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["--help"]
