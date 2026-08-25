from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streamlight.dependencies import locate_ffmpeg
from streamlight.editor_engine import EditorExporter, probe_media
from streamlight.editor_models import EditProject, SubtitleCue


def run() -> Path:
    ffmpeg, _source = locate_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("未找到 FFmpeg")
    output_dir = Path(tempfile.mkdtemp(prefix="streamlight-editor-smoke-"))
    first = output_dir / "first.mp4"
    second = output_dir / "second.mp4"
    music = output_dir / "music.wav"
    output = output_dir / "edited.mp4"

    commands = [
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=green:s=640x360:d=1.2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1.2",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(first),
        ],
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=854x480:d=1.0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(second),
        ],
        [ffmpeg, "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=2", str(music)],
    ]
    for command in commands:
        subprocess.run(command, check=True, capture_output=True)

    project = EditProject(name="真实导出测试", width=640, height=360, fps=25)
    first_asset = project.add_asset(probe_media(first, ffmpeg))
    second_asset = project.add_asset(probe_media(second, ffmpeg))
    music_asset = project.add_asset(probe_media(music, ffmpeg))
    project.append_video_asset(first_asset.id)
    project.append_video_asset(second_asset.id)
    project.append_video_asset(first_asset.id)
    project.update_clip(0, in_point=0.1, out_point=1.0, volume=0.5, muted=False)
    project.update_clip(1, in_point=0.0, out_point=0.8, volume=0.0, muted=True)
    project.update_clip(2, in_point=0.2, out_point=0.9, volume=0.35, muted=False)
    project.set_clip_transition(1, "dissolve", 0.25)
    project.set_clip_transition(2, "fade", 0.2)
    project.subtitle_cues.extend(
        [
            SubtitleCue("subtitle_first", first_asset.id, 0.2, 0.75, "第一段字幕", 0.95),
            SubtitleCue("subtitle_second", second_asset.id, 0.1, 0.6, "第二段字幕", 0.92),
        ]
    )
    track = project.add_audio_asset(music_asset.id)
    track.start_time = 0.2
    track.out_point = 1.6
    EditorExporter().export(project, output)
    if not output.is_file() or output.stat().st_size < 1000:
        raise RuntimeError("剪辑导出没有生成有效成片")
    result = probe_media(output, ffmpeg)
    if result.duration < 1.8:
        raise RuntimeError(f"成片时长异常：{result.duration}")
    probe = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(output)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    details = probe.stderr or probe.stdout
    stream_types = [
        stream_type.lower()
        for stream_type in re.findall(r"Stream #.*?: (Video|Audio|Subtitle):", details)
    ]
    for required in ("video", "audio", "subtitle"):
        if required not in stream_types:
            raise RuntimeError(f"导出缺少 {required} 流：{stream_types}")
    print(
        f"EDITOR_EXPORT_OK path={output} bytes={output.stat().st_size} "
        f"duration={result.duration:.3f} streams={','.join(stream_types)} transitions=dissolve,fade"
    )
    return output


if __name__ == "__main__":
    run()
