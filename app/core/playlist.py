import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import yt_dlp

from app.core.config import ARCHIVES_DIR, PLAYLISTS_DIR, get_base_ydl_opts

class PlaylistManager:
    """
    Manages playlist downloading state, tracking completed videos,
    handling chunked downloads (e.g. pause after 10 videos), and resuming.
    """

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """Sanitizes strings for safe filenames and directory names."""
        clean = re.sub(r'[\\/*?:"<>|]', "", name)
        return clean.strip() or "playlist"

    @classmethod
    def get_playlist_archive_file(cls, playlist_id: str) -> Path:
        clean_id = cls.sanitize_filename(playlist_id)
        return ARCHIVES_DIR / f"{clean_id}_archive.txt"

    @classmethod
    def get_playlist_state_file(cls, playlist_id: str) -> Path:
        clean_id = cls.sanitize_filename(playlist_id)
        return ARCHIVES_DIR / f"{clean_id}_state.json"

    @classmethod
    def get_downloaded_ids_from_archive(cls, archive_path: Path) -> set:
        """Reads yt-dlp archive file and returns set of downloaded video IDs."""
        downloaded = set()
        if archive_path.exists():
            with open(archive_path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        # archive format: "youtube <video_id>" or "<extractor> <video_id>"
                        downloaded.add(parts[1])
                    elif parts:
                        downloaded.add(parts[0])
        return downloaded

    @classmethod
    def extract_playlist_info(cls, playlist_url: str) -> Dict[str, Any]:
        """Extracts playlist metadata and list of entries without downloading media."""
        ydl_opts = get_base_ydl_opts()
        ydl_opts.update({
            "extract_flat": True,
            "skip_download": True,
        })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            
        playlist_id = info.get("id") or "playlist"
        title = info.get("title") or "YouTube Playlist"
        uploader = info.get("uploader") or info.get("channel") or "Unknown"
        entries = info.get("entries") or []
        
        archive_path = cls.get_playlist_archive_file(playlist_id)
        downloaded_ids = cls.get_downloaded_ids_from_archive(archive_path)

        video_list = []
        for index, item in enumerate(entries, start=1):
            if not item:
                continue
            video_id = item.get("id")
            video_title = item.get("title") or f"Video {index}"
            duration = item.get("duration")
            url = item.get("url") or (f"https://www.youtube.com/watch?v={video_id}" if video_id else "")
            
            is_downloaded = video_id in downloaded_ids
            video_list.append({
                "index": index,
                "id": video_id,
                "title": video_title,
                "duration": duration,
                "url": url,
                "is_downloaded": is_downloaded,
                "thumbnail": item.get("thumbnails", [{}])[-1].get("url") if item.get("thumbnails") else None,
            })

        completed_count = sum(1 for v in video_list if v["is_downloaded"])
        
        summary = {
            "playlist_id": playlist_id,
            "title": title,
            "uploader": uploader,
            "url": playlist_url,
            "total_count": len(video_list),
            "completed_count": completed_count,
            "remaining_count": len(video_list) - completed_count,
            "archive_file": str(archive_path),
            "entries": video_list
        }
        
        # Save state
        cls.save_state(playlist_id, summary)
        return summary

    @classmethod
    def save_state(cls, playlist_id: str, state_data: Dict[str, Any]):
        state_file = cls.get_playlist_state_file(playlist_id)
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)

    @classmethod
    def load_state(cls, playlist_id: str) -> Optional[Dict[str, Any]]:
        state_file = cls.get_playlist_state_file(playlist_id)
        if state_file.exists():
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    @classmethod
    def list_saved_playlists(cls) -> List[Dict[str, Any]]:
        """Returns all saved playlist states."""
        playlists = []
        for file in ARCHIVES_DIR.glob("*_state.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Refresh completed count against archive file
                    archive_path = Path(data.get("archive_file", ""))
                    downloaded_ids = cls.get_downloaded_ids_from_archive(archive_path)
                    data["completed_count"] = len(downloaded_ids)
                    data["remaining_count"] = max(0, data.get("total_count", 0) - len(downloaded_ids))
                    playlists.append({
                        "playlist_id": data.get("playlist_id"),
                        "title": data.get("title"),
                        "uploader": data.get("uploader"),
                        "total_count": data.get("total_count"),
                        "completed_count": data.get("completed_count"),
                        "remaining_count": data.get("remaining_count"),
                        "url": data.get("url")
                    })
            except Exception:
                continue
        return playlists
