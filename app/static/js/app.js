// YouTube Pro Downloader - Studio Frontend Controller

let currentMediaInfo = null;
let currentPlaylistInfo = null;
let activeTasks = [];
let eventSource = null;

let videoInspectTimer = null;
let playlistInspectTimer = null;

// Selected options state
let selectedResolution = "1080p";
let selectedContainer = "mp4";
let selectedMode = "video"; // "video" or "audio"
let selectedAudioCodec = "mp3";
let selectedAudioQuality = "320";

let selectedPlaylistBatch = "10";
let selectedPlaylistRes = "1080p";

// Tab Switching
function switchTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach((btn) => btn.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach((el) => (el.style.display = "none"));

  const targetTab = document.getElementById(`tab-${tabId}`);
  if (targetTab) {
    targetTab.style.display = "block";
  }

  const buttons = document.querySelectorAll(".tab-btn");
  if (tabId === "single") buttons[0].classList.add("active");
  if (tabId === "playlist") buttons[1].classList.add("active");
  if (tabId === "queue") {
    buttons[2].classList.add("active");
    fetchTasks();
  }
  if (tabId === "files") {
    buttons[3].classList.add("active");
    loadFiles();
  }

  lucide.createIcons();
}

// -------------------------------------------------------------
// AUTOMATIC VIDEO INSPECTION LOGIC
// -------------------------------------------------------------
function isYouTubeUrl(url) {
  if (!url) return false;
  return url.includes("youtube.com/") || url.includes("youtu.be/");
}

function handleVideoInput(val) {
  val = val.trim();
  clearTimeout(videoInspectTimer);
  if (isYouTubeUrl(val)) {
    videoInspectTimer = setTimeout(() => {
      runAutoInspectVideo(val);
    }, 500);
  }
}

function handleVideoPaste(e) {
  setTimeout(() => {
    const val = document.getElementById("video-url").value.trim();
    if (isYouTubeUrl(val)) {
      clearTimeout(videoInspectTimer);
      runAutoInspectVideo(val);
    }
  }, 50);
}

async function runAutoInspectVideo(url) {
  const spinner = document.getElementById("video-spinner");
  const statusBar = document.getElementById("video-auto-status");
  const previewCard = document.getElementById("video-preview-card");
  const optionsPanel = document.getElementById("video-options-panel");

  spinner.classList.add("active");
  statusBar.innerHTML = `<i data-lucide="loader-2" class="spin"></i> <span>Inspecting video formats, codecs, and stream resolutions...</span>`;
  lucide.createIcons();

  try {
    const res = await fetch("/api/info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Inspection failed");

    currentMediaInfo = data.data;

    // Show Preview Card
    previewCard.style.display = "flex";
    document.getElementById("video-thumb").src = currentMediaInfo.thumbnail || "";
    document.getElementById("video-title").textContent = currentMediaInfo.title || "Video";
    document.getElementById("video-channel").innerHTML = `<i data-lucide="user"></i> ${currentMediaInfo.channel || "Unknown"}`;
    document.getElementById("video-duration").innerHTML = `<i data-lucide="clock"></i> ${currentMediaInfo.duration_string || currentMediaInfo.duration + "s"}`;
    document.getElementById("video-views").innerHTML = `<i data-lucide="eye"></i> ${currentMediaInfo.view_count ? currentMediaInfo.view_count.toLocaleString() : "0"} views`;

    // Render detected resolution pills
    renderResolutionPills(currentMediaInfo.resolutions || []);

    // Reveal the Options Panel & Download Button
    optionsPanel.style.display = "block";
    statusBar.innerHTML = `<span style="color: #34d399;"><i data-lucide="check-circle"></i> Successfully inspected formats. Select quality and click download below!</span>`;
  } catch (err) {
    statusBar.innerHTML = `<span style="color: #f87171;"><i data-lucide="alert-circle"></i> Inspection error: ${err.message}</span>`;
  } finally {
    spinner.classList.remove("active");
    lucide.createIcons();
  }
}

function renderResolutionPills(resolutions) {
  const container = document.getElementById("resolution-pills-container");
  container.innerHTML = "";

  const presets = [
    { id: "2160p", name: "4K UHD", badge: "2160P", desc: "Ultra High Definition" },
    { id: "1440p", name: "2K QHD", badge: "1440P", desc: "Quad High Definition" },
    { id: "1080p", name: "1080p FHD", badge: "1080P", desc: "Full High Definition" },
    { id: "720p", name: "720p HD", badge: "720P", desc: "Standard High Definition" },
    { id: "480p", name: "480p SD", badge: "480P", desc: "Standard Definition" },
    { id: "360p", name: "360p", badge: "360P", desc: "Compact Mobile" },
    { id: "best", name: "Best Max", badge: "SOURCE", desc: "Highest Available" },
  ];

  // If YouTube detected specific resolutions, prioritize those
  let chosenDefault = false;

  presets.forEach((preset) => {
    const isDetected = resolutions.includes(preset.id) || preset.id === "best";
    if (!isDetected && preset.id !== "1080p" && preset.id !== "720p") return;

    const pill = document.createElement("div");
    let isSelected = false;

    if (!chosenDefault) {
      if (preset.id === "1080p" || (resolutions.length > 0 && preset.id === resolutions[0])) {
        isSelected = true;
        chosenDefault = true;
        selectedResolution = preset.id;
      }
    }

    pill.className = `pill-card res-pill ${isSelected ? "active" : ""}`;
    pill.dataset.res = preset.id;
    pill.onclick = () => selectResolutionPill(pill, preset.id);

    pill.innerHTML = `
      <div class="pill-res">${preset.name} <span class="pill-badge">${preset.badge}</span></div>
      <div class="pill-desc">${preset.desc}</div>
    `;

    container.appendChild(pill);
  });
}

function selectResolutionPill(pillEl, resId) {
  document.querySelectorAll(".res-pill").forEach((p) => p.classList.remove("active"));
  pillEl.classList.add("active");
  selectedResolution = resId;
}

function setMediaMode(mode) {
  selectedMode = mode;
  document.getElementById("mode-btn-video").classList.toggle("active", mode === "video");
  document.getElementById("mode-btn-audio").classList.toggle("active", mode === "audio");

  document.getElementById("video-resolution-section").style.display = mode === "video" ? "block" : "none";
  document.getElementById("audio-settings-section").style.display = mode === "audio" ? "block" : "none";
}

function setContainer(c) {
  selectedContainer = c;
  document.querySelectorAll(".container-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.container === c);
  });
}

function selectAudioPill(pillEl) {
  document.querySelectorAll(".audio-pill").forEach((p) => p.classList.remove("active"));
  pillEl.classList.add("active");
  const [codec, quality] = pillEl.dataset.audio.split(":");
  selectedAudioCodec = codec;
  selectedAudioQuality = quality;
}

async function executeSingleDownload() {
  const url = document.getElementById("video-url").value.trim();
  if (!url) return;

  const embedSubs = document.getElementById("embed-subs").checked;
  const embedThumb = document.getElementById("embed-thumb").checked;

  const payload = {
    url,
    resolution: selectedResolution,
    container: selectedContainer,
    audio_only: selectedMode === "audio",
    audio_format: selectedAudioCodec,
    audio_quality: selectedAudioQuality,
    embed_subtitles: embedSubs,
    embed_thumbnail: embedThumb,
    is_playlist: false,
    title: currentMediaInfo ? currentMediaInfo.title : null,
  };

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Download failed to initiate");

    switchTab("queue");
  } catch (err) {
    alert("Download Error: " + err.message);
  }
}

// -------------------------------------------------------------
// AUTOMATIC PLAYLIST INSPECTION LOGIC
// -------------------------------------------------------------
function handlePlaylistInput(val) {
  val = val.trim();
  clearTimeout(playlistInspectTimer);
  if (isYouTubeUrl(val) && (val.includes("list=") || val.includes("playlist"))) {
    playlistInspectTimer = setTimeout(() => {
      runAutoInspectPlaylist(val);
    }, 500);
  }
}

function handlePlaylistPaste(e) {
  setTimeout(() => {
    const val = document.getElementById("playlist-url").value.trim();
    if (isYouTubeUrl(val)) {
      clearTimeout(playlistInspectTimer);
      runAutoInspectPlaylist(val);
    }
  }, 50);
}

async function runAutoInspectPlaylist(url) {
  const spinner = document.getElementById("playlist-spinner");
  const statusBar = document.getElementById("playlist-auto-status");
  const previewCard = document.getElementById("playlist-preview-card");
  const optionsPanel = document.getElementById("playlist-options-panel");

  spinner.classList.add("active");
  statusBar.innerHTML = `<i data-lucide="loader-2" class="spin"></i> <span>Inspecting playlist entries & archive state...</span>`;
  lucide.createIcons();

  try {
    const res = await fetch("/api/info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Playlist inspection failed");

    currentPlaylistInfo = data.data;

    previewCard.style.display = "flex";
    document.getElementById("playlist-title").textContent = currentPlaylistInfo.title || "Playlist";
    document.getElementById("playlist-channel").innerHTML = `<i data-lucide="user"></i> ${currentPlaylistInfo.uploader || "Unknown"}`;
    document.getElementById("playlist-total-count").innerHTML = `<i data-lucide="video"></i> ${currentPlaylistInfo.total_items} Total Videos`;

    // Query archive state
    const plRes = await fetch("/api/playlists");
    const plData = await plRes.json();
    const saved = (plData.playlists || []).find((p) => p.playlist_id === currentPlaylistInfo.id);

    const completed = saved ? saved.completed_count : 0;
    const remaining = Math.max(0, currentPlaylistInfo.total_items - completed);

    document.getElementById("playlist-downloaded-count").innerHTML = `<i data-lucide="check-circle"></i> ${completed} Completed`;
    document.getElementById("playlist-remaining-count").innerHTML = `<i data-lucide="clock"></i> ${remaining} Remaining`;

    // Render items table
    const tbody = document.getElementById("playlist-entries-body");
    tbody.innerHTML = "";
    (currentPlaylistInfo.entries || []).forEach((entry) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="font-weight: 700; color: var(--text-muted);">${entry.index}</td>
        <td>${entry.title}</td>
        <td><span class="status-badge" style="font-size: 0.72rem; padding: 0.2rem 0.5rem;">Ready</span></td>
      `;
      tbody.appendChild(tr);
    });

    optionsPanel.style.display = "block";
    statusBar.innerHTML = `<span style="color: #34d399;"><i data-lucide="check-circle"></i> Playlist inspected. Configure batch settings and click start below!</span>`;
  } catch (err) {
    statusBar.innerHTML = `<span style="color: #f87171;"><i data-lucide="alert-circle"></i> Playlist error: ${err.message}</span>`;
  } finally {
    spinner.classList.remove("active");
    lucide.createIcons();
  }
}

function setBatchLimit(limit) {
  selectedPlaylistBatch = limit;
  document.querySelectorAll(".batch-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.batch === limit);
  });
}

function selectPlaylistRes(el) {
  document.querySelectorAll(".playlist-res-pill").forEach((p) => p.classList.remove("active"));
  el.classList.add("active");
  selectedPlaylistRes = el.dataset.res;
}

async function executePlaylistDownload() {
  const url = document.getElementById("playlist-url").value.trim();
  if (!url) return;

  const batchLimit = parseInt(selectedPlaylistBatch) || null;
  const isAudio = selectedPlaylistRes === "audio";
  const startIdx = parseInt(document.getElementById("playlist-start-idx").value) || null;
  const endIdx = parseInt(document.getElementById("playlist-end-idx").value) || null;

  const payload = {
    url,
    resolution: isAudio ? "best" : selectedPlaylistRes,
    audio_only: isAudio,
    audio_format: "mp3",
    audio_quality: "320",
    is_playlist: true,
    pause_after_n: batchLimit,
    start_index: startIdx,
    end_index: endIdx,
    title: currentPlaylistInfo ? currentPlaylistInfo.title : "Playlist",
    playlist_id: currentPlaylistInfo ? currentPlaylistInfo.id : null,
  };

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Playlist download failed to start");

    switchTab("queue");
  } catch (err) {
    alert("Error: " + err.message);
  }
}

// -------------------------------------------------------------
// LIVE TASK QUEUE & SSE
// -------------------------------------------------------------
async function fetchTasks() {
  try {
    const res = await fetch("/api/tasks");
    const data = await res.json();
    activeTasks = data.tasks || [];
    renderTasks(activeTasks);
  } catch (err) {
    console.error("Failed to fetch tasks", err);
  }
}

function renderTasks(tasks) {
  const container = document.getElementById("tasks-container");
  const countBadge = document.getElementById("active-tasks-count");

  const runningCount = tasks.filter((t) => t.status === "downloading" || t.status === "paused").length;
  countBadge.textContent = runningCount;

  if (tasks.length === 0) {
    container.innerHTML = `<p style="color: var(--text-muted); text-align: center; padding: 2.5rem;">No active downloads. Paste a link above to begin!</p>`;
    return;
  }

  container.innerHTML = tasks
    .map((task) => {
      const isPaused = task.status === "paused";
      const isDownloading = task.status === "downloading";
      const isCompleted = task.status === "completed";

      let statusClass = "task-card-sharp";
      if (isPaused) statusClass += " paused";
      if (isCompleted) statusClass += " completed";
      if (task.status === "error") statusClass += " error";

      const badgeText = isPaused && task.pause_after_n
        ? `PAUSED (${task.pause_after_n} videos batch limit reached)`
        : task.status.toUpperCase();

      return `
      <div class="${statusClass}">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 0.5rem;">
          <div>
            <h3 style="font-size: 0.98rem; font-weight: 700; color: var(--text-primary);">${task.title}</h3>
            <p style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.2rem;">
              ${task.is_playlist ? `📑 Playlist Task • Target: ${task.options.resolution || "1080p"}` : `🎬 Video Task • Container: ${task.options.container || "mp4"}`}
              ${task.current_filename ? `• Current file: <b>${task.current_filename}</b>` : ""}
            </p>
          </div>
          <span class="status-badge" style="font-size: 0.72rem; padding: 0.2rem 0.55rem;">
            ${badgeText}
          </span>
        </div>

        <div class="progress-container-sharp">
          <div class="progress-bar-sharp ${isPaused ? "paused" : ""}" style="width: ${task.percent || 0}%;"></div>
        </div>

        <div class="task-stats-sharp">
          <div>
            <span><b>${task.percent}%</b></span>
            ${task.total_bytes_str ? ` • <span>${task.total_bytes_str}</span>` : ""}
            ${task.speed_str ? ` • <span>⚡ ${task.speed_str}</span>` : ""}
            ${task.eta_str && task.eta_str !== "--:--" ? ` • <span>⏱️ ETA: ${task.eta_str}</span>` : ""}
          </div>
          <div style="display: flex; gap: 0.4rem;">
            ${
              isDownloading
                ? `<button class="btn-sharp btn-warning-sharp btn-sm-sharp" onclick="pauseTask('${task.task_id}')">
                    <i data-lucide="pause"></i> Pause
                   </button>`
                : ""
            }
            ${
              isPaused
                ? `<button class="btn-sharp btn-success-sharp btn-sm-sharp" onclick="resumeTask('${task.task_id}')">
                    <i data-lucide="play"></i> Resume
                   </button>`
                : ""
            }
            ${
              isDownloading || isPaused
                ? `<button class="btn-sharp btn-danger-sharp btn-sm-sharp" onclick="cancelTask('${task.task_id}')">
                    <i data-lucide="x"></i> Cancel
                   </button>`
                : ""
            }
          </div>
        </div>
      </div>
    `;
    })
    .join("");

  lucide.createIcons();
}

async function pauseTask(taskId) {
  try {
    await fetch(`/api/tasks/${taskId}/pause`, { method: "POST" });
    fetchTasks();
  } catch (err) {
    alert("Pause failed: " + err.message);
  }
}

async function resumeTask(taskId) {
  try {
    await fetch(`/api/tasks/${taskId}/resume`, { method: "POST" });
    fetchTasks();
  } catch (err) {
    alert("Resume failed: " + err.message);
  }
}

async function cancelTask(taskId) {
  try {
    await fetch(`/api/tasks/${taskId}/cancel`, { method: "POST" });
    fetchTasks();
  } catch (err) {
    alert("Cancel failed: " + err.message);
  }
}

function initSSE() {
  if (eventSource) eventSource.close();
  eventSource = new EventSource("/api/events");

  eventSource.onmessage = (event) => {
    try {
      const tasks = JSON.parse(event.data);
      activeTasks = tasks;
      const currentTab = document.querySelector(".tab-btn.active").textContent;
      if (currentTab.includes("Active Tasks")) {
        renderTasks(tasks);
      }
      const runningCount = tasks.filter((t) => t.status === "downloading" || t.status === "paused").length;
      document.getElementById("active-tasks-count").textContent = runningCount;
    } catch (e) {
      console.error("SSE parse error", e);
    }
  };

  eventSource.onerror = () => {
    document.getElementById("status-text").textContent = "Reconnecting...";
  };

  eventSource.onopen = () => {
    document.getElementById("status-text").textContent = "Engine Connected";
  };
}

// -------------------------------------------------------------
// FILE LIBRARY & PLAYER
// -------------------------------------------------------------
async function loadFiles() {
  try {
    const res = await fetch("/api/files");
    const data = await res.json();
    const files = data.files || [];

    document.getElementById("files-count").textContent = files.length;
    const tbody = document.getElementById("files-table-body");

    if (files.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">No downloaded media yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = files
      .map(
        (f) => `
      <tr>
        <td>
          <div style="font-weight: 700; color: var(--text-primary);">${f.name}</div>
          <div style="font-size: 0.72rem; color: var(--text-muted);">${f.relative_path}</div>
        </td>
        <td>
          <span class="status-badge" style="font-size: 0.7rem; padding: 0.2rem 0.5rem;">
            ${f.category.toUpperCase()}
          </span>
        </td>
        <td style="color: var(--text-secondary);">${f.size_str}</td>
        <td>
          <div style="display: flex; gap: 0.4rem;">
            ${
              f.is_video || f.is_audio
                ? `<button class="btn-sharp btn-primary-sharp btn-sm-sharp" onclick="playMedia('${f.download_url}', '${encodeURIComponent(f.name)}', ${f.is_video})">
                    <i data-lucide="play"></i> Play
                   </button>`
                : ""
            }
            <a href="${f.download_url}" download class="btn-sharp btn-secondary-sharp btn-sm-sharp">
              <i data-lucide="download"></i> Save
            </a>
            <button class="btn-sharp btn-danger-sharp btn-sm-sharp" onclick="deleteFile('${f.category}', '${encodeURIComponent(f.relative_path)}')">
              <i data-lucide="trash-2"></i>
            </button>
          </div>
        </td>
      </tr>
    `
      )
      .join("");

    lucide.createIcons();
  } catch (err) {
    console.error("Failed to load files", err);
  }
}

function playMedia(url, encodedName, isVideo) {
  const name = decodeURIComponent(encodedName);
  document.getElementById("modal-file-title").textContent = name;
  const mount = document.getElementById("player-mount");

  if (isVideo) {
    mount.innerHTML = `<video controls autoplay src="${url}" style="width: 100%; max-height: 480px; background: #000; border-radius: var(--radius-xs);"></video>`;
  } else {
    mount.innerHTML = `<audio controls autoplay src="${url}" style="width: 100%; margin: 2rem 0;"></audio>`;
  }

  document.getElementById("player-modal").classList.add("open");
}

function closePlayerModal() {
  const modal = document.getElementById("player-modal");
  modal.classList.remove("open");
  const mount = document.getElementById("player-mount");
  mount.innerHTML = "";
}

async function deleteFile(category, encodedPath) {
  const path = decodeURIComponent(encodedPath);
  if (!confirm(`Are you sure you want to delete ${path}?`)) return;

  try {
    const res = await fetch(`/api/files/${category}/${encodeURIComponent(path)}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to delete file");
    loadFiles();
  } catch (err) {
    alert("Delete failed: " + err.message);
  }
}

// Initial Boot
document.addEventListener("DOMContentLoaded", () => {
  initSSE();
  fetchTasks();
  loadFiles();
});
