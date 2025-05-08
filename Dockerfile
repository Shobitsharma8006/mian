# Use official Python base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create a working directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Qlik CLI (assuming qlik-cli is a Node.js package)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g @qlik/cli

# Copy application files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir flask requests

# Expose port
EXPOSE 9008

# Run the app
CMD ["python", "your_script_name.py"]
