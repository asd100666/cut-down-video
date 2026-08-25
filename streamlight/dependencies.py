from __future__ import annotations

import shutil
from pathlib import Path

from .models import DependencyStatus


def locate_ffmpeg() -> tuple[str | None, str]:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg, "系统"

    project_ffmpeg = Path(__file__).resolve().parent.parent / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
    if project_ffmpeg.is_file():
        return str(project_ffmpeg), "项目工具"

    try:
        import imageio_ffmpeg

        bundled = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if bundled.is_file():
            return str(bundled), "内置后备"
    except (ImportError, RuntimeError, OSError):
        pass

    return None, "未找到"


def locate_ffprobe(ffmpeg_path: str | None = None) -> str | None:
    system_ffprobe = shutil.which("ffprobe")
    if system_ffprobe:
        return system_ffprobe

    project_ffprobe = Path(__file__).resolve().parent.parent / "tools" / "ffmpeg" / "bin" / "ffprobe.exe"
    if project_ffprobe.is_file():
        return str(project_ffprobe)

    if ffmpeg_path:
        sibling = Path(ffmpeg_path).with_name("ffprobe.exe" if Path(ffmpeg_path).suffix else "ffprobe")
        if sibling.is_file():
            return str(sibling)
    return None


def dependency_status() -> DependencyStatus:
    try:
        from yt_dlp.version import __version__ as yt_dlp_version
    except ImportError:
        yt_dlp_version = "未安装"

    ffmpeg_path, source = locate_ffmpeg()
    return DependencyStatus(
        yt_dlp_version=yt_dlp_version,
        ffmpeg_path=ffmpeg_path,
        ffmpeg_source=source,
    )
