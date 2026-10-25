#!/usr/bin/env python3
"""
YouTube Playlist Downloader with Pause & Resume Support
Powered by yt-dlp

Usage examples:
  # Download first 10 videos in 1080p and pause:
  python scripts/download_playlist.py --url "https://www.youtube.com/playlist?list=..." --resolution 1080p --pause-after 10

  # Resume downloading the remaining videos later:
  python scripts/download_playlist.py --url "https://www.youtube.com/playlist?list=..." --resolution 1080p --resume

  # Download specific range (e.g., videos 11 to 20):
  python scripts/download_playlist.py --url "https://www.youtube.com/playlist?list=..." --start-index 11 --end-index 20

  # Download playlist as MP3 audio (320kbps):
  python scripts/download_playlist.py --url "https://www.youtube.com/playlist?list=..." --audio-only --audio-quality 320
"""

import os
import sys
import argparse
import signal
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import PLAYLISTS_DIR, ARCHIVES_DIR, RESOLUTION_FORMATS, get_base_ydl_opts
from app.core.playlist import PlaylistManager
import yt_dlp

def main():
    parser = argparse.ArgumentParser(
        description="Download YouTube Playlists with full resolution options, pause/resume, and batch limits."
    )
    parser.add_argument("--url", "-u", required=True, help="YouTube Playlist URL")
    parser.add_argument(
        "--resolution", "-r", default="1080p",
        choices=["best", "4320p", "2160p", "1440p", "1080p", "720p", "480p", "360p"],
        help="Target video resolution (default: 1080p)"
    )
    parser.add_argument(
        "--pause-after", "-p", type=int, default=None,
        help="Download N videos and then pause (e.g., --pause-after 10)"
    )
    parser.add_argument("--start-index", type=int, default=None, help="Start from video index (1-based)")
    parser.add_argument("--end-index", type=int, default=None, help="End at video index (inclusive)")
    parser.add_argument("--audio-only", "-a", action="store_true", help="Download audio only")
    parser.add_argument("--audio-format", default="mp3", choices=["mp3", "m4a", "flac", "wav", "opus"], help="Audio format")
    parser.add_argument("--audio-quality", default="320", help="Audio quality in kbps (e.g., 320, 256, 192)")
    parser.add_argument("--container", default="mp4", choices=["mp4", "mkv", "webm"], help="Video container format")
    parser.add_argument("--subtitles", action="store_true", help="Embed subtitles if available")
    parser.add_argument("--output-dir", "-o", default=None, help="Custom output directory")
    parser.add_argument("--resume", action="store_true", help="Resume previous download session")

    args = parser.parse_args()

    print("=" * 65)
    print("🎬 YouTube Playlist Downloader (yt-dlp)")
    print("=" * 65)

    # 1. Fetch Playlist Info
    print(f"[*] Extracting playlist metadata from: {args.url}")
    try:
        playlist_summary = PlaylistManager.extract_playlist_info(args.url)
    except Exception as e:
        print(f"[!] Error fetching playlist: {e}")
        sys.exit(1)

    playlist_id = playlist_summary["playlist_id"]
    playlist_title = playlist_summary["title"]
    total_videos = playlist_summary["total_count"]
    completed_videos = playlist_summary["completed_count"]
    remaining_videos = playlist_summary["remaining_count"]
    archive_file = PlaylistManager.get_playlist_archive_file(playlist_id)

    print(f"[+] Playlist Title : {playlist_title}")
    print(f"[+] Total Videos   : {total_videos}")
    print(f"[+] Downloaded     : {completed_videos}")
    print(f"[+] Remaining      : {remaining_videos}")
    print(f"[+] Archive File   : {archive_file}")
    print("-" * 65)

    if remaining_videos == 0 and not args.start_index:
        print("[✔] All videos in this playlist are already downloaded!")
        return

    # Determine Output Directory
    if args.output_dir:
        out_dir = Path(args.output_dir)
    else:
        folder_name = PlaylistManager.sanitize_filename(playlist_title)
        out_dir = PLAYLISTS_DIR / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[+] Saving to: {out_dir}")

    # Build yt-dlp options
    ydl_opts = get_base_ydl_opts()
    ydl_opts["quiet"] = False
    ydl_opts["no_warnings"] = False
    ydl_opts["download_archive"] = str(archive_file)
    ydl_opts["outtmpl"] = str(out_dir / "%(playlist_index|00)s - %(title)s.%(ext)s")

    # Format setup
    if args.audio_only:
        print(f"[+] Audio Mode: Extracting as {args.audio_format.upper()} ({args.audio_quality} kbps)")
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
            "writethumbnail": True,
            "embedthumbnail": True,
            "addmetadata": True,
        })

    if args.subtitles:
        print("[+] Subtitles: Enabled (English/Auto)")
        ydl_opts.update({
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en.*", "all"],
            "embedsubtitles": True,
        })

    # Range / Pause limits
    if args.start_index:
        ydl_opts["playliststart"] = args.start_index
        print(f"[+] Starting from video index: {args.start_index}")
    if args.end_index:
        ydl_opts["playlistend"] = args.end_index
        print(f"[+] Ending at video index: {args.end_index}")

    if args.pause_after:
        ydl_opts["max_downloads"] = args.pause_after
        print(f"[+] ⏸️  Batch limit active: Will download {args.pause_after} videos and PAUSE.")

    # Graceful Ctrl+C handler
    interrupted = False
    def sigint_handler(sig, frame):
        nonlocal interrupted
        interrupted = True
        print("\n[!] Ctrl+C detected. Gracefully stopping download...")
        print("[!] Archive has been safely updated.")
        print(f"[!] To resume later, run:\n    python scripts/download_playlist.py --url \"{args.url}\" --resume")
        sys.exit(0)

    signal.signal(signal.SIGINT, sigint_handler)

    print("-" * 65)
    print("[*] Starting download...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([args.url])
        print("\n[✔] Batch finished completely!")
    except yt_dlp.utils.MaxDownloadsReached:
        print("\n" + "=" * 65)
        print(f"[⏸️] PAUSED: Successfully downloaded {args.pause_after} videos as requested!")
        print(f"[+] Your progress is saved in: {archive_file}")
        print(f"[+] To resume downloading the rest of the playlist later, simply run:")
        print(f"    python scripts/download_playlist.py --url \"{args.url}\" --resolution {args.resolution} --resume")
        print("=" * 65)
    except Exception as e:
        if "Maximum number of downloads reached" in str(e):
            print("\n" + "=" * 65)
            print(f"[⏸️] PAUSED: Downloaded requested batch count.")
            print(f"[+] To resume the remaining videos, run:")
            print(f"    python scripts/download_playlist.py --url \"{args.url}\" --resume")
            print("=" * 65)
        else:
            print(f"\n[!] Error during download: {e}")

if __name__ == "__main__":
    main()
