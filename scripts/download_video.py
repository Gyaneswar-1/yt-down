#!/usr/bin/env python3
"""
Single YouTube Video Downloader with Full Resolution Support (1080p, 4K, 720p, etc.)
Powered by yt-dlp

Usage examples:
  # Download 1080p video with best audio merged into MP4:
  python scripts/download_video.py --url "https://www.youtube.com/watch?v=..." --resolution 1080p

  # Download 4K video:
  python scripts/download_video.py --url "https://www.youtube.com/watch?v=..." --resolution 2160p

  # Download audio only as 320kbps MP3:
  python scripts/download_video.py --url "https://www.youtube.com/watch?v=..." --audio-only --audio-quality 320

  # Inspect available resolutions and streams:
  python scripts/download_video.py --url "https://www.youtube.com/watch?v=..." --info
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import VIDEOS_DIR, AUDIO_DIR, RESOLUTION_FORMATS, get_base_ydl_opts
from app.core.downloader import downloader_service
import yt_dlp

def main():
    parser = argparse.ArgumentParser(
        description="Download YouTube videos with all resolution options (1080p, 4K, 720p) or high-quality audio."
    )
    parser.add_argument("--url", "-u", required=True, help="YouTube Video URL")
    parser.add_argument(
        "--resolution", "-r", default="1080p",
        choices=["best", "4320p", "2160p", "1440p", "1080p", "720p", "480p", "360p", "240p", "144p"],
        help="Target video resolution (default: 1080p)"
    )
    parser.add_argument("--container", "-c", default="mp4", choices=["mp4", "mkv", "webm"], help="Video container format")
    parser.add_argument("--audio-only", "-a", action="store_true", help="Download audio only")
    parser.add_argument("--audio-format", default="mp3", choices=["mp3", "m4a", "flac", "wav", "opus"], help="Audio codec")
    parser.add_argument("--audio-quality", default="320", help="Audio bitrate in kbps (320, 256, 192, 128)")
    parser.add_argument("--subtitles", "-s", action="store_true", help="Download & embed subtitles")
    parser.add_argument("--no-thumbnail", action="store_true", help="Do not embed video thumbnail")
    parser.add_argument("--output-dir", "-o", default=None, help="Custom output directory")
    parser.add_argument("--info", "-i", action="store_true", help="Only inspect video info and available resolutions")

    args = parser.parse_args()

    print("=" * 65)
    print("🎬 YouTube Video Downloader (yt-dlp)")
    print("=" * 65)

    if args.info:
        print(f"[*] Inspecting: {args.url} ...")
        try:
            info = downloader_service.extract_info(args.url)
            print(f"[+] Title        : {info.get('title')}")
            print(f"[+] Channel      : {info.get('channel')}")
            print(f"[+] Duration     : {info.get('duration_string') or info.get('duration')}s")
            print(f"[+] Views        : {info.get('view_count'):,}" if info.get('view_count') else "")
            print(f"[+] Resolutions  : {', '.join(info.get('resolutions', []))}")
            print(f"[+] Subtitles    : {', '.join(info.get('subtitles', [])[:10]) or 'None'}")
        except Exception as e:
            print(f"[!] Error inspecting video: {e}")
        return

    # Determine destination folder
    if args.output_dir:
        out_dir = Path(args.output_dir)
    elif args.audio_only:
        out_dir = AUDIO_DIR
    else:
        out_dir = VIDEOS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = get_base_ydl_opts()
    ydl_opts["quiet"] = False
    ydl_opts["no_warnings"] = False
    ydl_opts["outtmpl"] = str(out_dir / "%(title)s.%(ext)s")
    ydl_opts["addmetadata"] = True

    if args.audio_only:
        print(f"[+] Audio Mode: {args.audio_format.upper()} ({args.audio_quality} kbps)")
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": args.audio_format,
                    "preferredquality": str(args.audio_quality),
                }
            ],
        })
    else:
        fmt = RESOLUTION_FORMATS.get(args.resolution, f"bv*[height<={args.resolution.rstrip('p')}]+ba/b")
        print(f"[+] Video Mode: Resolution {args.resolution} ({args.container.upper()})")
        ydl_opts.update({
            "format": fmt,
            "merge_output_format": args.container,
        })
        if not args.no_thumbnail:
            ydl_opts.update({
                "writethumbnail": True,
                "embedthumbnail": True,
            })

    if args.subtitles:
        print("[+] Subtitles: Enabled (English/Auto)")
        ydl_opts.update({
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en.*", "all"],
            "embedsubtitles": True,
        })

    print(f"[+] Saving to: {out_dir}")
    print("-" * 65)
    print("[*] Downloading...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([args.url])
        print("\n[✔] Download finished successfully!")
        print(f"[✔] File saved in: {out_dir}")
    except Exception as e:
        print(f"\n[!] Download failed: {e}")

if __name__ == "__main__":
    main()
