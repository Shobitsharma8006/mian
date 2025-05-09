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
    git \
    gnupg \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (optional, if needed for other purposes)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Download and install Qlik CLI
RUN curl -L https://github.com/qlik-oss/qlik-cli/releases/download/v2.26.0/qlik-Linux-x86_64.tar.gz -o qlik.tar.gz && \
    tar -xzf qlik.tar.gz && \
    mv qlik /usr/local/bin/qlik && \
    chmod +x /usr/local/bin/qlik && \
    rm qlik.tar.gz

# Copy application code
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port
EXPOSE 9008

# Run the application
CMD ["python", "app.py"]
