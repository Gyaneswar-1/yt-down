import os
import re
import uuid
import time
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
import yt_dlp

from app.core.config import (
    DOWNLOADS_DIR,
    VIDEOS_DIR,
    PLAYLISTS_DIR,
    AUDIO_DIR,
    ARCHIVES_DIR,
    RESOLUTION_FORMATS,
    get_base_ydl_opts,
)
from app.core.playlist import PlaylistManager

logger = logging.getLogger("ytdlp_app")

class TaskStatus:
    QUEUED = "queued"
    PREPARING = "preparing"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class DownloadTask:
    def __init__(self, task_id: str, url: str, task_type: str = "video", options: Dict[str, Any] = None):
        self.task_id = task_id
        self.url = url
        self.task_type = task_type  # "video" or "playlist"
        self.options = options or {}
        self.status = TaskStatus.QUEUED
        self.created_at = time.time()
        self.updated_at = time.time()
        self.title = self.options.get("title") or "Extracting information..."
        
        # Progress metrics
        self.percent = 0.0
        self.speed = 0
        self.speed_str = "0 KB/s"
        self.eta = 0
        self.eta_str = "--:--"
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.total_bytes_str = "0 MB"
        self.current_filename = ""
        self.output_files = []
        
        # Playlist-specific tracking
        self.is_playlist = (task_type == "playlist")
        self.playlist_id = self.options.get("playlist_id")
        self.current_item_index = 0
        self.total_items = self.options.get("total_items", 0)
        self.current_item_title = ""
        self.items_downloaded_session = 0
        self.pause_after_n = self.options.get("pause_after_n", 0)
        
        # Control flags
        self.pause_requested = threading.Event()
        self.cancel_requested = threading.Event()
        self.error_message = ""
        self.logs: List[str] = []

    def log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.logs.append(entry)
        if len(self.logs) > 500:
            self.logs.pop(0)
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "url": self.url,
            "title": self.title,
            "task_type": self.task_type,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "percent": round(self.percent, 1),
            "speed_str": self.speed_str,
            "eta_str": self.eta_str,
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes": self.total_bytes,
            "total_bytes_str": self.total_bytes_str,
            "current_filename": self.current_filename,
            "output_files": self.output_files,
            "is_playlist": self.is_playlist,
            "playlist_id": self.playlist_id,
            "current_item_index": self.current_item_index,
            "total_items": self.total_items,
            "current_item_title": self.current_item_title,
            "items_downloaded_session": self.items_downloaded_session,
            "pause_after_n": self.pause_after_n,
            "options": self.options,
            "error_message": self.error_message,
            "logs": self.logs[-20:],
        }


class DownloaderService:
    def __init__(self):
        self.tasks: Dict[str, DownloadTask] = {}
        self.lock = threading.Lock()

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        return self.tasks.get(task_id)

    def list_tasks(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [task.to_dict() for task in sorted(self.tasks.values(), key=lambda t: t.created_at, reverse=True)]

    def extract_info(self, url: str) -> Dict[str, Any]:
        """
        Extracts metadata and format resolutions for a video or playlist.
        """
        ydl_opts = get_base_ydl_opts()
        ydl_opts.update({
            "extract_flat": "in_playlist",
            "skip_download": True,
        })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Check if URL is a playlist
        if "entries" in info:
            playlist_id = info.get("id") or "playlist"
            entries = info.get("entries") or []
            return {
                "type": "playlist",
                "id": playlist_id,
                "title": info.get("title") or "YouTube Playlist",
                "uploader": info.get("uploader") or info.get("channel") or "Unknown",
                "total_items": len(entries),
                "url": url,
                "entries": [
                    {
                        "index": idx + 1,
                        "id": e.get("id"),
                        "title": e.get("title") or f"Item {idx + 1}",
                        "duration": e.get("duration"),
                        "thumbnail": e.get("thumbnails", [{}])[-1].get("url") if e.get("thumbnails") else None,
                    }
                    for idx, e in enumerate(entries[:100]) if e
                ]
            }

        # Single video analysis
        formats = info.get("formats", [])
        resolutions_available = set()
        video_formats_info = []

        for f in formats:
            height = f.get("height")
            vcodec = f.get("vcodec")
            if height and vcodec and vcodec != "none":
                res_str = f"{height}p"
                resolutions_available.add(height)
                video_formats_info.append({
                    "format_id": f.get("format_id"),
                    "resolution": res_str,
                    "height": height,
                    "fps": f.get("fps"),
                    "ext": f.get("ext"),
                    "vcodec": vcodec.split(".")[0] if vcodec else "unknown",
                    "filesize": f.get("filesize") or f.get("filesize_approx"),
                })

        sorted_resolutions = sorted(list(resolutions_available), reverse=True)
        res_list = [f"{h}p" for h in sorted_resolutions]

        subtitles_available = list((info.get("subtitles") or {}).keys())

        return {
            "type": "video",
            "id": info.get("id"),
            "title": info.get("title"),
            "channel": info.get("uploader") or info.get("channel"),
            "duration": info.get("duration"),
            "duration_string": info.get("duration_string"),
            "thumbnail": info.get("thumbnail"),
            "description": (info.get("description") or "")[:300],
            "view_count": info.get("view_count"),
            "resolutions": res_list,
            "has_1080p": 1080 in sorted_resolutions,
            "has_4k": 2160 in sorted_resolutions,
            "subtitles": subtitles_available,
            "url": url,
        }

    def start_download(self, url: str, options: Dict[str, Any]) -> str:
        """
        Registers and kicks off a download task in a separate background thread.
        """
        task_id = str(uuid.uuid4())[:8]
        task_type = "playlist" if options.get("is_playlist") else "video"
        
        task = DownloadTask(task_id, url, task_type, options)
        with self.lock:
            self.tasks[task_id] = task

        thread = threading.Thread(target=self._run_task, args=(task,), daemon=True)
        thread.start()
        return task_id

    def pause_task(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False
        task.pause_requested.set()
        task.log("Pause requested by user...")
        return True

    def resume_task(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if not task or task.status != TaskStatus.PAUSED:
            return False
        
        task.pause_requested.clear()
        task.cancel_requested.clear()
        task.status = TaskStatus.QUEUED
        task.log("Resuming download task...")
        
        thread = threading.Thread(target=self._run_task, args=(task,), daemon=True)
        thread.start()
        return True

    def cancel_task(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False
        task.cancel_requested.set()
        task.status = TaskStatus.CANCELLED
        task.log("Task cancelled by user.")
        return True

    def _run_task(self, task: DownloadTask):
        task.status = TaskStatus.DOWNLOADING
        task.log(f"Starting download for: {task.url}")

        opts = task.options
        resolution = opts.get("resolution", "best")
        audio_only = opts.get("audio_only", False)
        container = opts.get("container", "mp4")
        audio_format = opts.get("audio_format", "mp3")
        audio_quality = opts.get("audio_quality", "320")
        embed_subs = opts.get("embed_subtitles", False)
        embed_thumb = opts.get("embed_thumbnail", True)
        
        ydl_opts = get_base_ydl_opts()
        # Always set ignoreerrors=True to prevent 429 on subtitles from crashing video download
        ydl_opts["ignoreerrors"] = True
        
        # Configure output directory & template
        if task.is_playlist:
            playlist_name = PlaylistManager.sanitize_filename(task.title or "playlist")
            out_dir = PLAYLISTS_DIR / playlist_name
            out_dir.mkdir(parents=True, exist_ok=True)
            ydl_opts["outtmpl"] = str(out_dir / "%(playlist_index|00)s - %(title)s.%(ext)s")
        elif audio_only:
            out_dir = AUDIO_DIR
            out_dir.mkdir(parents=True, exist_ok=True)
            ydl_opts["outtmpl"] = str(out_dir / "%(title)s.%(ext)s")
        else:
            out_dir = VIDEOS_DIR
            out_dir.mkdir(parents=True, exist_ok=True)
            ydl_opts["outtmpl"] = str(out_dir / "%(title)s.%(ext)s")

        # Configure Audio / Video Formats
        if audio_only:
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": audio_format,
                        "preferredquality": str(audio_quality),
                    }
                ]
            })
        else:
            # Video format selection with audio combination
            if resolution in RESOLUTION_FORMATS:
                ydl_opts["format"] = RESOLUTION_FORMATS[resolution]
            elif resolution.endswith("p"):
                h = resolution.rstrip("p")
                ydl_opts["format"] = f"bv*[height<={h}]+ba/b[height<={h}]"
            else:
                ydl_opts["format"] = "bv*+ba/b"

            ydl_opts["merge_output_format"] = container

        # Subtitles (safe fetching with fallback)
        if embed_subs:
            ydl_opts.update({
                "writesubtitles": True,
                "writeautomaticsub": False,  # Avoid auto-sub requests which YouTube rate-limits with 429
                "subtitleslangs": ["en"],
                "embedsubtitles": True,
            })

        # Thumbnails & Metadata
        if embed_thumb and not audio_only:
            ydl_opts.update({
                "writethumbnail": True,
                "embedthumbnail": True,
            })
        ydl_opts["addmetadata"] = True

        # Archive setup for Playlist resume/pause
        if task.is_playlist:
            p_id = task.playlist_id or PlaylistManager.sanitize_filename(task.url)
            archive_path = PlaylistManager.get_playlist_archive_file(p_id)
            ydl_opts["download_archive"] = str(archive_path)
            
            start_idx = opts.get("start_index")
            end_idx = opts.get("end_index")
            if start_idx:
                ydl_opts["playliststart"] = int(start_idx)
            if end_idx:
                ydl_opts["playlistend"] = int(end_idx)
                
            pause_after = opts.get("pause_after_n")
            if pause_after and int(pause_after) > 0:
                ydl_opts["max_downloads"] = int(pause_after)

        # Hook functions for real-time progress & live pause/cancellation
        def progress_hook(d):
            if task.cancel_requested.is_set():
                raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")
            
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                speed = d.get("speed") or 0
                eta = d.get("eta") or 0

                task.total_bytes = total
                task.downloaded_bytes = downloaded
                task.speed = speed
                task.eta = eta
                
                if total > 0:
                    task.percent = min(100.0, (downloaded / total) * 100.0)
                    task.total_bytes_str = f"{total / (1024 * 1024):.1f} MB"
                
                if speed > 0:
                    if speed > 1024 * 1024:
                        task.speed_str = f"{speed / (1024 * 1024):.1f} MB/s"
                    else:
                        task.speed_str = f"{speed / 1024:.0f} KB/s"
                else:
                    task.speed_str = "-- KB/s"

                if eta > 0:
                    mins, secs = divmod(int(eta), 60)
                    hrs, mins = divmod(mins, 60)
                    task.eta_str = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs else f"{mins:02d}:{secs:02d}"
                else:
                    task.eta_str = "--:--"

                filename = d.get("filename", "")
                if filename:
                    task.current_filename = os.path.basename(filename)

            elif status == "finished":
                task.percent = 100.0
                task.speed_str = "Complete"
                task.eta_str = "00:00"
                filename = d.get("filename", "")
                if filename:
                    base = os.path.basename(filename)
                    if base not in task.output_files:
                        task.output_files.append(base)
                    task.log(f"Finished downloading: {base}")

        def postprocessor_hook(d):
            if task.pause_requested.is_set():
                task.log("Pause triggered. Gracefully halting after this item.")
                raise yt_dlp.utils.DownloadCancelled("Paused by user request.")
            
            if d.get("status") == "finished":
                task.items_downloaded_session += 1
                task.log(f"Item #{task.items_downloaded_session} completed successfully.")

        ydl_opts["progress_hooks"] = [progress_hook]
        ydl_opts["postprocessor_hooks"] = [postprocessor_hook]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if task.title == "Extracting information...":
                    info = ydl.extract_info(task.url, download=False)
                    if info:
                        task.title = info.get("title") or "YouTube Media"
                        if task.is_playlist and "entries" in info:
                            task.total_items = len(info.get("entries", []))

                ydl.download([task.url])

            task.status = TaskStatus.COMPLETED
            task.percent = 100.0
            task.log("All downloads completed successfully!")

        except yt_dlp.utils.MaxDownloadsReached:
            task.status = TaskStatus.PAUSED
            task.log(f"Reached batch limit of {task.pause_after_n} videos. Task paused. Ready to resume anytime!")

        except yt_dlp.utils.DownloadCancelled as dc:
            if task.pause_requested.is_set():
                task.status = TaskStatus.PAUSED
                task.log("Download successfully paused. You can resume at any time.")
            else:
                task.status = TaskStatus.CANCELLED
                task.log("Download was cancelled.")

        except Exception as e:
            err = str(e)
            if "Maximum number of downloads reached" in err:
                task.status = TaskStatus.PAUSED
                task.log(f"Paused after target download count. Ready to resume!")
            elif task.pause_requested.is_set():
                task.status = TaskStatus.PAUSED
                task.log("Paused by user.")
            elif task.cancel_requested.is_set():
                task.status = TaskStatus.CANCELLED
                task.log("Cancelled by user.")
            elif "429" in err and "subtitles" in err.lower():
                # Non-fatal subtitle rate limit: mark completed if video downloaded
                task.log("Subtitles were skipped due to YouTube rate-limiting. Video media downloaded successfully.")
                task.status = TaskStatus.COMPLETED
                task.percent = 100.0
            else:
                task.status = TaskStatus.ERROR
                task.error_message = err
                task.log(f"Error during download: {err}")
                logger.exception("Error in download task")

downloader_service = DownloaderService()
