from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Callable

from .dependencies import locate_ffmpeg, locate_ffprobe
from .editor_models import EditProject, MediaAsset


ProbeProgress = Callable[[str], None]
ExportProgress = Callable[[float, str], None]


class ExportCancelled(RuntimeError):
    pass


def _creation_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def _fraction(value: str | None) -> float:
    if not value or value in {"0/0", "N/A"}:
        return 0.0
    try:
        if "/" in value:
            numerator, denominator = value.split("/", 1)
            return float(numerator) / float(denominator)
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


def _duration(value: object) -> float:
    try:
        result = float(value)
        return result if result > 0 else 0.0
    except (TypeError, ValueError):
        return 0.0


def probe_media(path: str | Path, ffmpeg_path: str | None = None) -> MediaAsset:
    media_path = Path(path).resolve()
    if not media_path.is_file():
        raise FileNotFoundError(f"找不到媒体文件：{media_path}")

    ffmpeg = ffmpeg_path or locate_ffmpeg()[0]
    ffprobe = locate_ffprobe(ffmpeg)
    if ffprobe:
        command = [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-show_entries",
            "stream=codec_type,width,height,r_frame_rate,duration",
            "-of",
            "json",
            str(media_path),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=_creation_flags(),
            check=False,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout or "{}")
            streams = data.get("streams") or []
            video = next((item for item in streams if item.get("codec_type") == "video"), None)
            audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
            media_duration = _duration((data.get("format") or {}).get("duration"))
            if not media_duration:
                media_duration = max((_duration(item.get("duration")) for item in streams), default=0.0)
            if video:
                return MediaAsset.create(
                    media_path,
                    kind="video",
                    duration=media_duration,
                    width=int(video.get("width") or 0),
                    height=int(video.get("height") or 0),
                    fps=_fraction(video.get("r_frame_rate")),
                    has_audio=audio is not None,
                )
            if audio:
                return MediaAsset.create(media_path, kind="audio", duration=media_duration, has_audio=True)

    if not ffmpeg:
        raise RuntimeError("未找到 FFmpeg，无法分析本地媒体")
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(media_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=_creation_flags(),
        check=False,
    )
    details = result.stderr or result.stdout
    duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", details)
    if not duration_match:
        raise RuntimeError(f"无法读取媒体时长：{media_path.name}")
    hours, minutes, seconds = duration_match.groups()
    media_duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    video_match = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", details)
    has_audio = bool(re.search(r"Audio:", details))
    if video_match:
        fps_match = re.search(r"(\d+(?:\.\d+)?)\s+fps", details)
        return MediaAsset.create(
            media_path,
            kind="video",
            duration=media_duration,
            width=int(video_match.group(1)),
            height=int(video_match.group(2)),
            fps=float(fps_match.group(1)) if fps_match else 0.0,
            has_audio=has_audio,
        )
    if has_audio:
        return MediaAsset.create(media_path, kind="audio", duration=media_duration, has_audio=True)
    raise RuntimeError(f"不支持的媒体文件：{media_path.name}")


class EditorExporter:
    def __init__(self, progress_callback: ExportProgress | None = None) -> None:
        self.progress_callback = progress_callback or (lambda _percent, _message: None)
        self._cancel_event = threading.Event()
        self._process: subprocess.Popen[str] | None = None

    def cancel(self) -> None:
        self._cancel_event.set()
        process = self._process
        if process and process.poll() is None:
            process.terminate()

    def _check_cancelled(self) -> None:
        if self._cancel_event.is_set():
            raise ExportCancelled("导出已取消")

    def _run(self, command: list[str], stage: str) -> None:
        self._check_cancelled()
        self._process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=_creation_flags(),
        )
        stdout, stderr = self._process.communicate()
        return_code = self._process.returncode
        self._process = None
        self._check_cancelled()
        if return_code:
            detail_lines = (stderr or stdout or "FFmpeg 未返回错误详情").strip().splitlines()
            detail = "\n".join(detail_lines[-30:])
            raise RuntimeError(f"{stage}失败：\n{detail}")

    @staticmethod
    def _video_filter(width: int, height: int, fps: float) -> str:
        return (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1,fps={fps:g},format=yuv420p"
        )

    @staticmethod
    def _srt_timestamp(seconds: float) -> str:
        total_ms = max(0, round(float(seconds) * 1000))
        hours, remainder = divmod(total_ms, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        secs, millis = divmod(remainder, 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def export(self, project: EditProject, output_path: str | Path) -> Path:
        project.validate(check_files=True)
        if not project.clips:
            raise ValueError("时间线上没有可导出的镜头")
        ffmpeg, _source = locate_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("未找到 FFmpeg，无法导出剪辑")

        output = Path(output_path).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="streamlight-edit-") as directory:
            temp_dir = Path(directory)
            segments: list[Path] = []
            clip_count = len(project.clips)
            for index, clip in enumerate(project.clips):
                self._check_cancelled()
                asset = project.asset(clip.asset_id)
                segment = temp_dir / f"segment-{index:05d}.mp4"
                command = [
                    ffmpeg,
                    "-nostdin",
                    "-y",
                    "-ss",
                    f"{clip.in_point:.6f}",
                    "-t",
                    f"{clip.duration:.6f}",
                    "-i",
                    asset.path,
                ]
                video_filter = self._video_filter(project.width, project.height, project.fps)
                if asset.has_audio and not clip.muted and clip.volume > 0:
                    command += [
                        "-filter_complex",
                        f"[0:v:0]{video_filter}[v];[0:a:0]aresample=48000,volume={clip.volume:.4f}[a]",
                        "-map",
                        "[v]",
                        "-map",
                        "[a]",
                    ]
                else:
                    command += [
                        "-f",
                        "lavfi",
                        "-t",
                        f"{clip.duration:.6f}",
                        "-i",
                        "anullsrc=channel_layout=stereo:sample_rate=48000",
                        "-filter_complex",
                        f"[0:v:0]{video_filter}[v]",
                        "-map",
                        "[v]",
                        "-map",
                        "1:a:0",
                    ]
                command += [
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "19",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    "-shortest",
                    str(segment),
                ]
                percent = 5.0 + 65.0 * index / max(1, clip_count)
                self.progress_callback(percent, f"正在处理镜头 {index + 1}/{clip_count}")
                self._run(command, f"镜头 {index + 1} 处理")
                segments.append(segment)

            base_video = temp_dir / "base.mp4"
            self.progress_callback(73.0, "正在合并镜头")
            if len(segments) == 1:
                shutil.copyfile(segments[0], base_video)
            elif any(clip.transition != "cut" for clip in project.clips[1:]):
                command = [ffmpeg, "-nostdin", "-y"]
                for segment in segments:
                    command += ["-i", str(segment)]
                filters: list[str] = []
                for index in range(len(segments)):
                    filters.append(
                        f"[{index}:v:0]settb=AVTB,setpts=PTS-STARTPTS,"
                        f"fps={project.fps:g}[vin{index}]"
                    )
                    filters.append(
                        f"[{index}:a:0]aresample=48000:async=1:first_pts=0,"
                        f"asetpts=PTS-STARTPTS[ain{index}]"
                    )
                video_label = "[vin0]"
                audio_label = "[ain0]"
                elapsed = project.clips[0].duration
                for index, clip in enumerate(project.clips[1:], start=1):
                    next_video = f"[vin{index}]"
                    next_audio = f"[ain{index}]"
                    out_video = f"[v{index}]"
                    out_audio = f"[a{index}]"
                    overlap = project.transition_overlap(index)
                    if overlap > 0:
                        offset = max(0.0, elapsed - overlap)
                        transition = "dissolve" if clip.transition == "dissolve" else "fade"
                        filters.append(
                            f"{video_label}{next_video}xfade=transition={transition}:"
                            f"duration={overlap:.6f}:offset={offset:.6f}{out_video}"
                        )
                        filters.append(
                            f"{audio_label}{next_audio}acrossfade=d={overlap:.6f}:"
                            f"c1=tri:c2=tri{out_audio}"
                        )
                        elapsed += clip.duration - overlap
                    else:
                        filters.append(
                            f"{video_label}{audio_label}{next_video}{next_audio}"
                            f"concat=n=2:v=1:a=1{out_video}{out_audio}"
                        )
                        elapsed += clip.duration
                    video_label = out_video
                    audio_label = out_audio
                command += [
                    "-filter_complex",
                    ";".join(filters),
                    "-map",
                    video_label,
                    "-map",
                    audio_label,
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "19",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    str(base_video),
                ]
                self._run(command, "镜头转场合并")
            else:
                concat_file = temp_dir / "concat.txt"
                concat_file.write_text(
                    "\n".join(
                        f"file '{str(path).replace(chr(39), chr(92) + chr(39))}'" for path in segments
                    ),
                    encoding="utf-8",
                )
                self._run(
                    [
                        ffmpeg,
                        "-nostdin",
                        "-y",
                        "-f",
                        "concat",
                        "-safe",
                        "0",
                        "-i",
                        str(concat_file),
                        "-c",
                        "copy",
                        str(base_video),
                    ],
                    "镜头合并",
                )

            active_tracks = [track for track in project.audio_tracks if not track.muted and track.volume > 0]
            composed_video = temp_dir / "composed.mp4"
            if not active_tracks:
                self.progress_callback(86.0, "正在整理成片音轨")
                shutil.copyfile(base_video, composed_video)
            else:
                command = [ffmpeg, "-nostdin", "-y", "-i", str(base_video)]
                for track in active_tracks:
                    asset = project.asset(track.asset_id)
                    command += [
                        "-ss",
                        f"{track.in_point:.6f}",
                        "-t",
                        f"{track.duration:.6f}",
                        "-i",
                        asset.path,
                    ]
                filters = ["[0:a:0]aresample=48000[basea]"]
                mix_inputs = ["[basea]"]
                for index, track in enumerate(active_tracks, start=1):
                    delay = round(track.start_time * 1000)
                    label = f"ext{index}"
                    filters.append(
                        f"[{index}:a:0]aresample=48000,adelay={delay}|{delay},"
                        f"volume={track.volume:.4f},apad,atrim=0:{project.duration:.6f}[{label}]"
                    )
                    mix_inputs.append(f"[{label}]")
                filters.append(
                    f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=0[aout]"
                )
                command += [
                    "-filter_complex",
                    ";".join(filters),
                    "-map",
                    "0:v:0",
                    "-map",
                    "[aout]",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-shortest",
                    str(composed_video),
                ]
                self.progress_callback(82.0, "正在混合音轨")
                self._run(command, "音轨混合")

            subtitle_instances = project.timeline_subtitle_instances()
            if subtitle_instances:
                subtitle_path = temp_dir / "subtitles.srt"
                blocks: list[str] = []
                for number, (_cue_index, start, end, cue) in enumerate(subtitle_instances, start=1):
                    text = cue.text.replace("\r", " ").replace("\n", " ").strip()
                    blocks.append(
                        f"{number}\n{self._srt_timestamp(start)} --> {self._srt_timestamp(end)}\n{text}\n"
                    )
                subtitle_path.write_text("\n".join(blocks), encoding="utf-8-sig")
                self.progress_callback(93.0, "正在写入字幕轨")
                self._run(
                    [
                        ffmpeg,
                        "-nostdin",
                        "-y",
                        "-i",
                        str(composed_video),
                        "-f",
                        "srt",
                        "-i",
                        str(subtitle_path),
                        "-map",
                        "0:v:0",
                        "-map",
                        "0:a:0?",
                        "-map",
                        "1:0",
                        "-c:v",
                        "copy",
                        "-c:a",
                        "copy",
                        "-c:s",
                        "mov_text",
                        "-metadata:s:s:0",
                        "language=zho",
                        str(output),
                    ],
                    "字幕写入",
                )
            else:
                self.progress_callback(93.0, "正在写入成片")
                shutil.copyfile(composed_video, output)

        self.progress_callback(100.0, "导出完成")
        return output
