# Use a stable Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=9008

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    git \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Qlik CLI
RUN curl -L https://github.com/qlik-oss/qlik-cli/releases/download/v0.27.0/qlik-linux-amd64.zip -o qlik.zip && \
    unzip qlik.zip -d /usr/local/bin && \
    chmod +x /usr/local/bin/qlik && \
    rm qlik.zip

# Copy application code
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port
EXPOSE 9008

# Run the application
CMD ["python", "app.py"]
