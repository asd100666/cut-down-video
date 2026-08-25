from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streamlight.dependencies import locate_ffmpeg
from streamlight.editor_engine import probe_media
from streamlight.editor_models import EditProject
from streamlight.highlight_engine import LongVideoHighlightAnalyzer


def run() -> None:
    ffmpeg, _source = locate_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("未找到 FFmpeg")
    directory = Path(tempfile.mkdtemp(prefix="streamlight-highlight-smoke-"))
    source = directory / "scenes.mp4"
    command = [ffmpeg, "-y"]
    for color in ("red", "green", "blue", "white"):
        command += ["-f", "lavfi", "-i", f"color=c={color}:s=320x180:d=1"]
    command += [
        "-filter_complex",
        "[0:v][1:v][2:v][3:v]concat=n=4:v=1:a=0[v]",
        "-map",
        "[v]",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(source),
    ]
    subprocess.run(command, check=True, capture_output=True)

    project = EditProject(name="场景精华测试")
    asset = project.add_asset(probe_media(source, ffmpeg))
    analyzer = LongVideoHighlightAnalyzer()
    boundaries = analyzer.detect_scenes(asset.path, 0.15)
    clips = analyzer.analyze(
        project,
        [asset.id],
        target_duration=2.4,
        max_clip_duration=0.8,
        scene_threshold=0.15,
    )
    if len(boundaries) < 2:
        raise RuntimeError(f"场景切换检测不足：{boundaries}")
    if len(clips) != 3:
        raise RuntimeError(f"精华镜头数量异常：{len(clips)}")
    total = sum(clip.duration for clip in clips)
    if abs(total - 2.4) > 0.05:
        raise RuntimeError(f"精华目标时长异常：{total}")
    if clips != sorted(clips, key=lambda clip: clip.in_point):
        raise RuntimeError("精华镜头没有保持时间顺序")
    print(f"HIGHLIGHT_OK scenes={len(boundaries)} clips={len(clips)} duration={total:.3f}")


if __name__ == "__main__":
    run()
