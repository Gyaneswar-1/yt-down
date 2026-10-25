#!/usr/bin/env bash
# Script to launch the YouTube Downloader Web App

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if present
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Ensure output folders exist
mkdir -p downloads/videos downloads/playlists downloads/audio archives

PORT=${PORT:-8000}
HOST=${HOST:-"0.0.0.0"}

echo "=========================================================="
echo "🚀 Starting YouTube Pro Downloader Web Application"
echo "🌐 Web Interface: http://localhost:$PORT"
echo "📂 Downloads Dir: $SCRIPT_DIR/downloads"
echo "=========================================================="

python3 -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
