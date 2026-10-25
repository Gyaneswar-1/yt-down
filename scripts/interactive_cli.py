#!/usr/bin/env python3
"""
Interactive YouTube Downloader CLI
An easy step-by-step terminal wizard to download videos & playlists with all resolutions,
pause/resume, and batch limits.
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.playlist import PlaylistManager
from app.core.downloader import downloader_service
from app.core.config import PLAYLISTS_DIR, VIDEOS_DIR, AUDIO_DIR

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def banner():
    print("""
=================================================================
       🎥 YOUTUBE PRO DOWNLOADER (yt-dlp Interactive CLI)       
=================================================================
    """)

def prompt(text: str, default: str = "") -> str:
    val = input(f"{text} " + (f"[{default}]: " if default else ": ")).strip()
    return val if val else default

def interactive_single_video():
    print("\n--- 🎬 Download Single Video ---")
    url = prompt("Enter YouTube Video URL")
    if not url:
        print("[!] URL cannot be empty.")
        return

    print("\n[*] Inspecting video formats and resolutions...")
    try:
        info = downloader_service.extract_info(url)
        print(f"\n[+] Title   : {info.get('title')}")
        print(f"[+] Channel : {info.get('channel')}")
        print(f"[+] Length  : {info.get('duration_string') or info.get('duration')}s")
        print(f"[+] Available Resolutions: {', '.join(info.get('resolutions', []))}")
    except Exception as e:
        print(f"[!] Warning: Could not pre-fetch info ({e}). Proceeding anyway.")
        info = {}

    print("\nSelect Download Mode:")
    print(" 1. Video (Full HD 1080p - Recommended)")
    print(" 2. Video (Ultra HD 4K / 2160p)")
    print(" 3. Video (720p HD)")
    print(" 4. Video (Best Available)")
    print(" 5. Audio Only (MP3 320kbps High Quality)")
    print(" 6. Custom Resolution")

    choice = prompt("Choose an option (1-6)", "1")

    cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "download_video.py"), "--url", url]

    if choice == "1":
        cmd.extend(["--resolution", "1080p"])
    elif choice == "2":
        cmd.extend(["--resolution", "2160p"])
    elif choice == "3":
        cmd.extend(["--resolution", "720p"])
    elif choice == "4":
        cmd.extend(["--resolution", "best"])
    elif choice == "5":
        cmd.extend(["--audio-only", "--audio-format", "mp3", "--audio-quality", "320"])
    elif choice == "6":
        res = prompt("Enter resolution (e.g., 1440p, 480p, 360p)", "1080p")
        cmd.extend(["--resolution", res])

    sub = prompt("Embed subtitles if available? (y/n)", "n")
    if sub.lower().startswith("y"):
        cmd.append("--subtitles")

    print("\n" + "=" * 60)
    print("Executing download...")
    print("=" * 60)
    os.system(" ".join(f'"{c}"' if " " in c else c for c in cmd))

def interactive_playlist():
    print("\n--- 📑 Download Playlist with Pause & Resume ---")
    url = prompt("Enter YouTube Playlist URL")
    if not url:
        print("[!] URL cannot be empty.")
        return

    print("\n[*] Inspecting playlist metadata...")
    try:
        summary = PlaylistManager.extract_playlist_info(url)
        print(f"\n[+] Playlist Title : {summary['title']}")
        print(f"[+] Total Videos   : {summary['total_count']}")
        print(f"[+] Already Done   : {summary['completed_count']}")
        print(f"[+] Remaining      : {summary['remaining_count']}")
    except Exception as e:
        print(f"[!] Warning: Could not inspect playlist ({e}). Proceeding...")
        summary = {}

    print("\nPlaylist Download Options:")
    print(" 1. Download first N videos and PAUSE (e.g., download 10 videos and pause)")
    print(" 2. Download all remaining videos")
    print(" 3. Download specific range (e.g. from index 1 to 10)")
    print(" 4. Resume previous download session")

    mode = prompt("Select option (1-4)", "1")

    cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "download_playlist.py"), "--url", url]

    if mode == "1":
        pause_count = prompt("How many videos to download before pausing?", "10")
        cmd.extend(["--pause-after", pause_count])
    elif mode == "3":
        start_idx = prompt("Start from video index #", "1")
        end_idx = prompt("End at video index #", "10")
        cmd.extend(["--start-index", start_idx, "--end-index", end_idx])
    elif mode == "4":
        cmd.append("--resume")

    print("\nQuality / Format:")
    print(" 1. 1080p Full HD (Recommended)")
    print(" 2. 720p HD")
    print(" 3. Best Available")
    print(" 4. Audio Only (MP3 320kbps)")

    q_choice = prompt("Choose quality (1-4)", "1")
    if q_choice == "1":
        cmd.extend(["--resolution", "1080p"])
    elif q_choice == "2":
        cmd.extend(["--resolution", "720p"])
    elif q_choice == "3":
        cmd.extend(["--resolution", "best"])
    elif q_choice == "4":
        cmd.extend(["--audio-only", "--audio-format", "mp3", "--audio-quality", "320"])

    print("\n" + "=" * 60)
    print("Starting Playlist Downloader...")
    print("=" * 60)
    os.system(" ".join(f'"{c}"' if " " in c else c for c in cmd))

def list_downloaded():
    print("\n--- 📁 Downloaded Files ---")
    found = False
    for label, folder in [("Videos", VIDEOS_DIR), ("Audio", AUDIO_DIR), ("Playlists", PLAYLISTS_DIR)]:
        files = list(folder.rglob("*")) if folder.exists() else []
        media = [f for f in files if f.is_file() and not f.name.endswith(".part")]
        if media:
            found = True
            print(f"\n📂 {label} ({folder}):")
            for f in media:
                mb = f.stat().st_size / (1024 * 1024)
                print(f"  • {f.name} ({mb:.1f} MB)")
    if not found:
        print("  No downloads found yet.")
    prompt("\nPress Enter to return to menu")

def list_saved_playlists():
    print("\n--- 💾 Saved Playlist Sessions ---")
    playlists = PlaylistManager.list_saved_playlists()
    if not playlists:
        print("No saved playlist sessions found.")
        prompt("\nPress Enter to return to menu")
        return

    for idx, p in enumerate(playlists, 1):
        print(f"\n[{idx}] {p['title']}")
        print(f"    Progress: {p['completed_count']} / {p['total_count']} downloaded ({p['remaining_count']} remaining)")
        print(f"    URL: {p['url']}")

    sel = prompt("\nEnter playlist number to resume (or 0 to cancel)", "0")
    if sel.isdigit() and 1 <= int(sel) <= len(playlists):
        chosen = playlists[int(sel) - 1]
        print(f"\nResuming playlist: {chosen['title']}")
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "download_playlist.py"),
            "--url", chosen["url"],
            "--resolution", "1080p",
            "--resume"
        ]
        os.system(" ".join(f'"{c}"' if " " in c else c for c in cmd))

def main():
    while True:
        banner()
        print("Choose an action:")
        print(" 1. 🎬 Download Single Video (1080p, 4K, 720p, or MP3)")
        print(" 2. 📑 Download Playlist (with Pause after N videos & Resume)")
        print(" 3. 💾 View Saved Playlists & Resume")
        print(" 4. 📁 Browse Downloaded Files")
        print(" 5. ❌ Exit")

        choice = prompt("\nEnter your choice (1-5)", "1")

        if choice == "1":
            interactive_single_video()
        elif choice == "2":
            interactive_playlist()
        elif choice == "3":
            list_saved_playlists()
        elif choice == "4":
            list_downloaded()
        elif choice == "5":
            print("\nGoodbye!")
            break
        else:
            print("[!] Invalid option, please try again.")

        input("\nPress Enter to continue...")
        clear()

if __name__ == "__main__":
    main()
