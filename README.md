# YouTube Pro Downloader & Playlist Batch Manager

An advanced YouTube video and playlist downloader built with Python, [yt-dlp](https://github.com/yt-dlp/yt-dlp), FastAPI, and modern web UI technologies.

> **Full Documentation**: Please see the detailed explanation guide in [YTDLP_APP_GUIDE.md](file:///home/gyaneswar/Desktop/CodeFiles/Projects/ytdlp/YTDLP_APP_GUIDE.md).

---

## ⚡ Quick Start

### 1. Launch the Modern Web Application
```bash
./run_web.sh
```
Open **`http://localhost:8000`** in your browser.

### 2. Launch the Interactive CLI Wizard
```bash
./run_cli.sh
```

### 3. Use Standalone Terminal Scripts Directly

#### Download a Video at 1080p (Video + Audio merged):
```bash
python3 scripts/download_video.py --url "https://www.youtube.com/watch?v=..." --resolution 1080p
```

#### Download a Playlist and PAUSE after 10 videos:
```bash
python3 scripts/download_playlist.py --url "https://www.youtube.com/playlist?list=..." --resolution 1080p --pause-after 10
```

#### Resume the Playlist Later to Download the Remaining Videos:
```bash
python3 scripts/download_playlist.py --url "https://www.youtube.com/playlist?list=..." --resume
```

---

## 📂 Project Architecture

```
ytdlp/
├── app/
│   ├── main.py                  # FastAPI server with REST & SSE endpoints
│   ├── core/
│   │   ├── config.py            # Global configuration & format mappings
│   │   ├── downloader.py        # Core yt-dlp download service & background tasks
│   │   └── playlist.py          # Playlist state & archive manager
│   └── static/
│       ├── index.html           # Single-page web dashboard
│       ├── css/style.css        # Modern dark-mode styling
│       └── js/app.js            # Live updates, SSE listener & player modal
├── scripts/
│   ├── download_video.py        # CLI for single video downloads
│   ├── download_playlist.py     # CLI for playlist downloads with pause/resume
│   └── interactive_cli.py       # Interactive terminal wizard
├── downloads/
│   ├── videos/                  # Downloaded video files
│   ├── playlists/               # Downloaded playlist directories
│   └── audio/                   # Extracted MP3/M4A/FLAC files
├── archives/                    # Persistent download archives (.txt) and states (.json)
├── run_web.sh                   # Web app launcher
├── run_cli.sh                   # Interactive CLI launcher
├── requirements.txt             # Project dependencies
└── YTDLP_APP_GUIDE.md           # Comprehensive implementation guide
```
