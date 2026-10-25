#!/usr/bin/env bash
# Script to launch the Interactive CLI Downloader

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python3 "$SCRIPT_DIR/scripts/interactive_cli.py"
