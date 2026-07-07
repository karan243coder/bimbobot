FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    python3-libtorrent \
    libtorrent-rasterbar2.0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot files
COPY . .

# Create download directory
RUN mkdir -p downloads

# Koyeb health check ke liye port
EXPOSE 8080

# Run the bot
CMD ["python", "-m", "bot"]
