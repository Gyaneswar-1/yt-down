FROM python:3.11-slim

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies:
# - ffmpeg: required by yt-dlp to merge audio/video and extract audio
# - nodejs: required by yt-dlp for JavaScript challenge solving
# - curl: useful for container health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source files
COPY . .

# Ensure necessary runtime directories exist
RUN mkdir -p downloads/videos downloads/playlists downloads/audio archives

# Default fallback port (Render automatically provides $PORT)
ENV PORT=8000
EXPOSE 8000

# Launch uvicorn, expanding $PORT via shell so Render and local Docker work seamlessly
CMD ["sh", "-c", "python3 -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
