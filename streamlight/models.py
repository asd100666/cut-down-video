from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class FormatPreset:
    key: str
    label: str
    selector: str
    audio_only: bool = False


FORMAT_PRESETS: tuple[FormatPreset, ...] = (
    FormatPreset("best", "最佳画质", "bv*+ba/b"),
    FormatPreset("2160", "最高 4K", "bv*[height<=2160]+ba/b[height<=2160]"),
    FormatPreset("1440", "最高 2K", "bv*[height<=1440]+ba/b[height<=1440]"),
    FormatPreset("1080", "最高 1080p", "bv*[height<=1080]+ba/b[height<=1080]"),
    FormatPreset("720", "最高 720p", "bv*[height<=720]+ba/b[height<=720]"),
    FormatPreset("480", "最高 480p", "bv*[height<=480]+ba/b[height<=480]"),
    FormatPreset("audio", "仅音频（MP3）", "ba/b", audio_only=True),
)


def get_preset(key: str) -> FormatPreset:
    return next((item for item in FORMAT_PRESETS if item.key == key), FORMAT_PRESETS[0])


@dataclass(slots=True)
class DownloadRequest:
    url: str
    output_dir: Path
    preset_key: str = "best"
    cookie_browser: str | None = None
    referer: str | None = None
    user_agent: str | None = None
    allow_playlist: bool = False
    write_subtitles: bool = False
    write_auto_subtitles: bool = False
    subtitle_languages: list[str] = field(default_factory=lambda: ["zh-Hans", "zh-Hant", "zh", "en"])
    use_archive: bool = True

    @property
    def preset(self) -> FormatPreset:
        return get_preset(self.preset_key)


@dataclass(frozen=True, slots=True)
class MediaSummary:
    title: str
    site: str
    duration: float | None
    uploader: str
    webpage_url: str
    thumbnail: str | None
    available_heights: tuple[int, ...]
    format_count: int
    is_live: bool
    is_playlist: bool
    playlist_count: int | None

    @property
    def duration_text(self) -> str:
        if self.is_live:
            return "直播"
        if self.duration is None:
            return "时长未知"
        total = max(0, int(self.duration))
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def quality_text(self) -> str:
        if not self.available_heights:
            return "清晰度由站点决定"
        return " / ".join(f"{height}p" for height in self.available_heights[-4:])


@dataclass(slots=True)
class BatchMediaItem:
    url: str
    status: str = "pending"
    summary: MediaSummary | None = None
    error_title: str = ""
    error_detail: str = ""

    @property
    def is_downloadable(self) -> bool:
        return self.summary is not None


@dataclass(frozen=True, slots=True)
class ProgressUpdate:
    stage: str
    percent: float | None = None
    speed: str = ""
    eta: str = ""
    filename: str = ""
    message: str = ""


@dataclass(frozen=True, slots=True)
class DependencyStatus:
    yt_dlp_version: str
    ffmpeg_path: str | None
    ffmpeg_source: str

    @property
    def ffmpeg_available(self) -> bool:
        return bool(self.ffmpeg_path)


def media_summary_from_info(info: dict[str, Any]) -> MediaSummary:
    is_playlist = info.get("_type") in {"playlist", "multi_video"}
    playlist_count: int | None = None
    media = info

    if is_playlist:
        entries = [entry for entry in (info.get("entries") or []) if entry]
        playlist_count = info.get("playlist_count") or len(entries) or None
        if entries:
            media = entries[0]

    heights = sorted(
        {
            int(fmt["height"])
            for fmt in (media.get("formats") or [])
            if isinstance(fmt, dict) and isinstance(fmt.get("height"), (int, float))
        }
    )
    webpage_url = media.get("webpage_url") or info.get("webpage_url") or ""

    return MediaSummary(
        title=str(info.get("title") or media.get("title") or "未命名媒体"),
        site=str(media.get("extractor_key") or media.get("extractor") or info.get("extractor_key") or "未知站点"),
        duration=media.get("duration"),
        uploader=str(media.get("uploader") or media.get("channel") or "来源未知"),
        webpage_url=str(webpage_url),
        thumbnail=media.get("thumbnail") or info.get("thumbnail"),
        available_heights=tuple(heights),
        format_count=len(media.get("formats") or []),
        is_live=bool(media.get("is_live") or info.get("is_live")),
        is_playlist=is_playlist,
        playlist_count=playlist_count,
    )
