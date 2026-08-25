from __future__ import annotations

import sys
import subprocess
import tempfile
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QCoreApplication

from streamlight.dependencies import locate_ffmpeg
from streamlight.editor_engine import EditorExporter, ExportCancelled, probe_media
from streamlight.editor_models import EditProject, SubtitleCue
from streamlight.model_manager import ModelDownloader, ModelManager
from streamlight.narration_engine import LocalNarrationGenerator, NarrationSynthesizer


def app_model_manager() -> ModelManager:
    QCoreApplication.setOrganizationName("Streamlight")
    QCoreApplication.setOrganizationDomain("streamlight.local")
    QCoreApplication.setApplicationName("流光下载器")
    return ModelManager()


def make_project(directory: str) -> EditProject:
    source = Path(directory) / "narration-source.mp4"
    ffmpeg, _source = locate_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("未找到 FFmpeg")
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=640x360:rate=25:duration=4",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=4",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(source),
        ],
        check=True,
        capture_output=True,
    )
    project = EditProject(name="本地模型智能解说测试")
    asset = project.add_asset(probe_media(source, ffmpeg))
    first = project.append_video_asset(asset.id)
    first.name = "产品工作台总览"
    first.selection_reason = "展示剪辑工作台"
    project.split_clip(0, 2.0)
    project.clips[1].name = "智能分镜与字幕轨"
    project.clips[1].selection_reason = "演示自动分析后继续人工修改"
    project.subtitle_cues.extend(
        [
            SubtitleCue("subtitle_one", asset.id, 0.4, 1.4, "视频可以直接在工作台完成分镜", 0.95),
            SubtitleCue("subtitle_two", asset.id, 2.3, 3.4, "自动结果仍然可以手工调整", 0.94),
        ]
    )
    return project


def ensure_runtime(manager: ModelManager) -> None:
    qwen = manager.spec("qwen2.5-3b-instruct")
    if not manager.state(qwen).ready:
        raise RuntimeError("Qwen2.5 3B 模型尚未在应用模型管理中安装并校验")
    runtime = manager.spec("llama-cpp-runtime")
    if not manager.state(runtime).ready:
        print("NARRATION_RUNTIME_INSTALL starting")
        ModelDownloader(
            manager,
            lambda done, total, phase: print(
                f"RUNTIME_PROGRESS percent={done / max(1, total) * 100:.1f} phase={phase}"
            ) if done == total or phase.startswith("校验") else None,
        ).download(runtime)


def run() -> str:
    manager = app_model_manager()
    ensure_runtime(manager)
    with tempfile.TemporaryDirectory(prefix="streamlight-local-narration-") as directory:
        project = make_project(directory)
        progress: list[tuple[float, str]] = []
        generator = LocalNarrationGenerator(manager, lambda value, message: progress.append((value, message)))
        text, metadata = generator.generate(project, "summary", 140)
        if not text or len(text) > 140 or "[end of text]" in text:
            raise RuntimeError(f"本地模型输出无效：{text!r}")
        if metadata.get("provider") != "llama.cpp":
            raise RuntimeError(f"没有记录真实本地模型来源：{metadata}")

        edited_text = text.rstrip("。") + "，这是人工确认后的版本。"
        narration_path = Path(directory) / "edited-narration.wav"
        narration_asset = NarrationSynthesizer().synthesize(edited_text, narration_path, rate=1)
        added = project.add_asset(narration_asset)
        track = project.add_audio_asset(added.id)
        track.name = "智能解说（人工已修改）"
        track.volume = 0.9
        project.generation_settings["narration_script"] = edited_text
        project.generation_settings["narration"] = {**metadata, "edited_before_tts": True}
        output = Path(directory) / "local-narration-edited.mp4"
        EditorExporter().export(project, output)
        exported = probe_media(output)
        if not output.is_file() or output.stat().st_size < 1000 or not exported.has_audio:
            raise RuntimeError("本地模型解说加入音轨后的成片导出无效")

        cancel_generator = LocalNarrationGenerator(manager)
        outcome: list[BaseException] = []

        def generate_until_cancelled() -> None:
            try:
                cancel_generator.generate(project, "story", 1000)
            except BaseException as error:
                outcome.append(error)

        worker = threading.Thread(target=generate_until_cancelled)
        worker.start()
        time.sleep(0.5)
        cancel_generator.cancel()
        worker.join(5.0)
        if worker.is_alive() or not outcome or not isinstance(outcome[0], ExportCancelled):
            raise RuntimeError(f"本地模型取消未及时完成：alive={worker.is_alive()} outcome={outcome}")
        print(
            f"LOCAL_NARRATION_OK chars={len(text)} provider={metadata['provider']} "
            f"progress_events={len(progress)} cancelled=true edited=true "
            f"export_bytes={output.stat().st_size} text={text}"
        )
        return text


if __name__ == "__main__":
    run()
