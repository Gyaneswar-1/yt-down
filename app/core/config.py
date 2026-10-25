import os
import shutil
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
APP_DIR = BASE_DIR / "app"
STATIC_DIR = APP_DIR / "static"
DOWNLOADS_DIR = BASE_DIR / "downloads"
VIDEOS_DIR = DOWNLOADS_DIR / "videos"
PLAYLISTS_DIR = DOWNLOADS_DIR / "playlists"
AUDIO_DIR = DOWNLOADS_DIR / "audio"
ARCHIVES_DIR = BASE_DIR / "archives"

# Ensure directories exist
for directory in [DOWNLOADS_DIR, VIDEOS_DIR, PLAYLISTS_DIR, AUDIO_DIR, ARCHIVES_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Node.js binary resolution for yt-dlp JS challenges
def get_node_path() -> str | None:
    # 1. Standard PATH
    node_bin = shutil.which("node")
    if node_bin:
        return node_bin
    
    # 2. Check NVM common paths
    nvm_dir = Path.home() / ".nvm" / "versions" / "node"
    if nvm_dir.exists():
        versions = sorted(nvm_dir.glob("v*"), reverse=True)
        for v in versions:
            candidate = v / "bin" / "node"
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
    
    # 3. Common system locations
    for candidate in ["/usr/bin/node", "/usr/local/bin/node"]:
        if os.path.exists(candidate):
            return candidate
            
    return None

NODE_PATH = get_node_path()

# Resolution presets mapping
RESOLUTION_FORMATS = {
    "best": "bv*+ba/b",
    "4320p": "bv*[height<=4320]+ba/b[height<=4320]",
    "2160p": "bv*[height<=2160]+ba/b[height<=2160]",
    "1440p": "bv*[height<=1440]+ba/b[height<=1440]",
    "1080p": "bv*[height<=1080]+ba/b[height<=1080]",
    "720p": "bv*[height<=720]+ba/b[height<=720]",
    "480p": "bv*[height<=480]+ba/b[height<=480]",
    "360p": "bv*[height<=360]+ba/b[height<=360]",
    "240p": "bv*[height<=240]+ba/b[height<=240]",
    "144p": "bv*[height<=144]+ba/b[height<=144]",
}

def get_base_ydl_opts() -> dict:
    """Returns resilient base options for yt-dlp instance with anti-blocking & retry safeguards."""
    opts = {
        "quiet": True,
        "no_warnings": False,
        "remote_components": ["ejs:github"],
        "ignoreerrors": True,              # Tolerates 429/failures on subtitles or non-fatal chunks without aborting
        "retries": 10,
        "fragment_retries": 10,
        "skip_unavailable_fragments": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
    }
    
    # Impersonation support via curl-cffi to avoid 429 rate-limiting
    try:
        from yt_dlp.networking.impersonate import ImpersonateTarget
        opts["impersonate"] = ImpersonateTarget.from_str("chrome")
    except Exception:
        pass

    if NODE_PATH:
        opts["js_runtimes"] = {"node": {"path": NODE_PATH}}
        
    return opts
