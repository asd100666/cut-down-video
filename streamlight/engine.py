from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yt_dlp

from .dependencies import locate_ffmpeg
from .errors import UserCancelled, redact_secrets
from .models import DownloadRequest, MediaSummary, ProgressUpdate, media_summary_from_info

LogCallback = Callable[[str, str], None]
ProgressCallback = Callable[[ProgressUpdate], None]


def validate_http_url(url: str) -> str:
    candidate = url.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("请输入完整的 http:// 或 https:// 地址")
    return candidate


def parse_url_lines(text: str) -> list[str]:
    """Return non-empty URL lines in input order with exact duplicates removed."""
    urls: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        candidate = line.strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            urls.append(candidate)
    return urls


def _human_bytes_per_second(value: float | int | None) -> str:
    if not value:
        return ""
    size = float(value)
    units = ("B/s", "KB/s", "MB/s", "GB/s")
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return ""


def _human_eta(value: float | int | None) -> str:
    if value is None:
        return ""
    total = max(0, int(value))
    minutes, seconds = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


class _YtdlpLogger:
    def __init__(self, callback: LogCallback | None) -> None:
        self.callback = callback

    def _emit(self, level: str, message: str) -> None:
        if self.callback and message:
            self.callback(level, redact_secrets(message))

    def debug(self, message: str) -> None:
        if not message.startswith("[debug]"):
            self._emit("info", message)

    def warning(self, message: str) -> None:
        self._emit("warning", message)

    def error(self, message: str) -> None:
        self._emit("error", message)


class DownloadEngine:
    def __init__(
        self,
        request: DownloadRequest,
        *,
        progress_callback: ProgressCallback | None = None,
        log_callback: LogCallback | None = None,
    ) -> None:
        self.request = request
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def _check_cancelled(self) -> None:
        if self.is_cancelled:
            raise UserCancelled("任务已取消")

    def _emit_progress(self, update: ProgressUpdate) -> None:
        if self.progress_callback:
            self.progress_callback(update)

    def _progress_hook(self, data: dict[str, Any]) -> None:
        self._check_cancelled()
        status = data.get("status")
        filename = str(data.get("filename") or "")

        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            downloaded = data.get("downloaded_bytes") or 0
            percent = None
            if total:
                percent = min(100.0, max(0.0, float(downloaded) * 100.0 / float(total)))
            self._emit_progress(
                ProgressUpdate(
                    stage="downloading",
                    percent=percent,
                    speed=_human_bytes_per_second(data.get("speed")),
                    eta=_human_eta(data.get("eta")),
                    filename=Path(filename).name if filename else "",
                    message="正在下载媒体数据",
                )
            )
        elif status == "finished":
            self._emit_progress(
                ProgressUpdate(
                    stage="processing",
                    percent=100.0,
                    filename=Path(filename).name if filename else "",
                    message="媒体已下载，正在合并处理",
                )
            )

    def _postprocessor_hook(self, data: dict[str, Any]) -> None:
        self._check_cancelled()
        status = data.get("status")
        postprocessor = data.get("postprocessor") or "FFmpeg"
        if status == "started":
            self._emit_progress(
                ProgressUpdate(stage="processing", percent=100.0, message=f"正在执行 {postprocessor}")
            )
        elif status == "finished":
            self._emit_progress(
                ProgressUpdate(stage="processing", percent=100.0, message=f"{postprocessor} 已完成")
            )

    def _common_options(self, *, analysis: bool) -> dict[str, Any]:
        request = self.request
        output_dir = request.output_dir.expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        options: dict[str, Any] = {
            "logger": _YtdlpLogger(self.log_callback),
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "noplaylist": not request.allow_playlist,
            "windowsfilenames": True,
            "trim_file_name": 180,
            "retries": 10,
            "fragment_retries": 10,
            "file_access_retries": 3,
            "concurrent_fragment_downloads": 4,
            "continuedl": True,
            "paths": {"home": str(output_dir)},
            "outtmpl": {"default": "%(title).180B [%(id)s].%(ext)s"},
            "progress_hooks": [self._progress_hook],
            "postprocessor_hooks": [self._postprocessor_hook],
        }

        if request.cookie_browser:
            options["cookiesfrombrowser"] = (request.cookie_browser,)
        if request.referer:
            options["referer"] = request.referer
        if request.user_agent:
            options["user_agent"] = request.user_agent

        ffmpeg_path, _ = locate_ffmpeg()
        if ffmpeg_path:
            options["ffmpeg_location"] = ffmpeg_path

        if analysis:
            options.update({"skip_download": True, "playlistend": 20})
        else:
            options["format"] = request.preset.selector
            options["download_archive"] = str(output_dir / ".streamlight-archive.txt") if request.use_archive else None
            if request.preset.audio_only:
                options["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "0",
                    }
                ]
            else:
                options["merge_output_format"] = "mp4"

            if request.write_subtitles or request.write_auto_subtitles:
                options["writesubtitles"] = request.write_subtitles
                options["writeautomaticsub"] = request.write_auto_subtitles
                options["subtitleslangs"] = request.subtitle_languages
                options["subtitlesformat"] = "best"

        return {key: value for key, value in options.items() if value is not None}

    def analyze(self) -> MediaSummary:
        self._check_cancelled()
        url = validate_http_url(self.request.url)
        self._emit_progress(ProgressUpdate(stage="analyzing", message="正在解析播放页"))

        with yt_dlp.YoutubeDL(self._common_options(analysis=True)) as ydl:
            info = ydl.extract_info(url, download=False)

        self._check_cancelled()
        if not info:
            raise RuntimeError("yt-dlp 没有返回媒体信息")
        return media_summary_from_info(info)

    def download(self) -> str:
        self._check_cancelled()
        url = validate_http_url(self.request.url)
        self._emit_progress(ProgressUpdate(stage="starting", percent=0.0, message="正在准备下载"))

        with yt_dlp.YoutubeDL(self._common_options(analysis=False)) as ydl:
            info = ydl.extract_info(url, download=True)

        self._check_cancelled()
        if not info:
            raise RuntimeError("下载完成但没有返回媒体信息")

        self._emit_progress(ProgressUpdate(stage="finished", percent=100.0, message="下载完成"))
        return str(self.request.output_dir.expanduser().resolve())
