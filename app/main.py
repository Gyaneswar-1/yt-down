import os
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import (
    STATIC_DIR,
    DOWNLOADS_DIR,
    VIDEOS_DIR,
    PLAYLISTS_DIR,
    AUDIO_DIR,
)
from app.core.downloader import downloader_service
from app.core.playlist import PlaylistManager

app = FastAPI(
    title="YouTube Pro Downloader",
    description="Advanced YouTube Downloader powered by yt-dlp with Full Resolution Support, Playlist Pause & Resume",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static assets
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Request Models
class InfoRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    resolution: Optional[str] = "1080p"
    container: Optional[str] = "mp4"
    audio_only: Optional[bool] = False
    audio_format: Optional[str] = "mp3"
    audio_quality: Optional[str] = "320"
    embed_subtitles: Optional[bool] = False
    embed_thumbnail: Optional[bool] = True
    is_playlist: Optional[bool] = False
    pause_after_n: Optional[int] = None
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    title: Optional[str] = None
    playlist_id: Optional[str] = None


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import Response
    return Response(content=b"", media_type="image/x-icon")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>Frontend not found</h1>", status_code=404)
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.post("/api/info")
async def get_media_info(req: InfoRequest):
    """Inspects a video or playlist URL and extracts resolutions, formats, and metadata."""
    if not req.url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, downloader_service.extract_info, req.url)
        return {"success": True, "data": info}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/download")
async def start_download_endpoint(req: DownloadRequest):
    """Starts a new video or playlist download task."""
    if not req.url:
        raise HTTPException(status_code=400, detail="URL is required")

    options = {
        "resolution": req.resolution,
        "container": req.container,
        "audio_only": req.audio_only,
        "audio_format": req.audio_format,
        "audio_quality": req.audio_quality,
        "embed_subtitles": req.embed_subtitles,
        "embed_thumbnail": req.embed_thumbnail,
        "is_playlist": req.is_playlist,
        "pause_after_n": req.pause_after_n,
        "start_index": req.start_index,
        "end_index": req.end_index,
        "title": req.title,
        "playlist_id": req.playlist_id,
    }

    try:
        task_id = downloader_service.start_download(req.url, options)
        return {"success": True, "task_id": task_id, "message": "Download task started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks")
async def get_all_tasks():
    """Returns all active, paused, and completed tasks."""
    return {"tasks": downloader_service.list_tasks()}


@app.get("/api/tasks/{task_id}")
async def get_single_task(task_id: str):
    task = downloader_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": task.to_dict()}


@app.post("/api/tasks/{task_id}/pause")
async def pause_task_endpoint(task_id: str):
    """Pauses a running task (supports playlist pausing)."""
    success = downloader_service.pause_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or cannot be paused")
    return {"success": True, "message": "Pause signal sent to task"}


@app.post("/api/tasks/{task_id}/resume")
async def resume_task_endpoint(task_id: str):
    """Resumes a paused download task."""
    success = downloader_service.resume_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Task not found or not in paused state")
    return {"success": True, "message": "Task resumed"}


@app.post("/api/tasks/{task_id}/cancel")
async def cancel_task_endpoint(task_id: str):
    """Cancels a running task."""
    success = downloader_service.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "message": "Task cancelled"}


@app.get("/api/events")
async def sse_events(request: Request):
    """Server-Sent Events stream delivering real-time download progress."""
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            tasks = downloader_service.list_tasks()
            data = json.dumps(tasks)
            yield f"data: {data}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/files")
async def list_downloaded_files():
    """Lists all downloaded files grouped by category."""
    categories = {
        "videos": VIDEOS_DIR,
        "audio": AUDIO_DIR,
        "playlists": PLAYLISTS_DIR,
    }
    
    files_list = []
    for cat_name, cat_dir in categories.items():
        if not cat_dir.exists():
            continue
        for p in cat_dir.rglob("*"):
            if p.is_file() and not p.name.endswith(".part") and not p.name.endswith(".ytdl"):
                stat = p.stat()
                rel_path = str(p.relative_to(cat_dir))
                size_mb = stat.st_size / (1024 * 1024)
                files_list.append({
                    "name": p.name,
                    "relative_path": rel_path,
                    "category": cat_name,
                    "size_bytes": stat.st_size,
                    "size_str": f"{size_mb:.2f} MB" if size_mb >= 1 else f"{stat.st_size / 1024:.1f} KB",
                    "modified_time": stat.st_mtime,
                    "download_url": f"/api/files/{cat_name}/{rel_path}",
                    "is_video": p.suffix.lower() in [".mp4", ".mkv", ".webm", ".avi", ".mov"],
                    "is_audio": p.suffix.lower() in [".mp3", ".m4a", ".flac", ".wav", ".opus", ".aac"],
                })

    files_list.sort(key=lambda x: x["modified_time"], reverse=True)
    return {"files": files_list}


@app.get("/api/files/{category}/{file_path:path}")
async def serve_file(category: str, file_path: str):
    """Serves or streams a downloaded file."""
    cat_dirs = {
        "videos": VIDEOS_DIR,
        "audio": AUDIO_DIR,
        "playlists": PLAYLISTS_DIR,
    }
    base_dir = cat_dirs.get(category)
    if not base_dir:
        raise HTTPException(status_code=404, detail="Invalid category")

    target = (base_dir / file_path).resolve()
    # Path traversal protection
    if not str(target).startswith(str(base_dir.resolve())) or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=target,
        filename=target.name,
        media_type="application/octet-stream"
    )


@app.delete("/api/files/{category}/{file_path:path}")
async def delete_file(category: str, file_path: str):
    """Deletes a downloaded file from disk."""
    cat_dirs = {
        "videos": VIDEOS_DIR,
        "audio": AUDIO_DIR,
        "playlists": PLAYLISTS_DIR,
    }
    base_dir = cat_dirs.get(category)
    if not base_dir:
        raise HTTPException(status_code=404, detail="Invalid category")

    target = (base_dir / file_path).resolve()
    if not str(target).startswith(str(base_dir.resolve())) or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    target.unlink()
    return {"success": True, "message": f"Deleted {target.name}"}


@app.get("/api/playlists")
async def list_playlists():
    """Lists saved playlist download sessions and archive statuses."""
    return {"playlists": PlaylistManager.list_saved_playlists()}
