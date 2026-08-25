from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streamlight.dependencies import locate_ffmpeg
from streamlight.editor_models import MediaAsset
from streamlight.model_manager import ModelDownloader, ModelFile, ModelManager, ModelSpec
from streamlight.offline_intelligence import OfflineIntelligenceAnalyzer


def run() -> None:
    ffmpeg, _source = locate_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("未找到 FFmpeg")
    tiny = ModelSpec(
        id="whisper-small",
        name="Whisper Tiny 冒烟模型",
        category="语音",
        capability="speech",
        description="仅用于验证 Whisper 原生运行时",
        version="whisper.cpp-tiny-smoke",
        source_name="ggerganov/whisper.cpp",
        source_url="https://huggingface.co/ggerganov/whisper.cpp",
        license_name="MIT",
        files=(
            ModelFile(
                "ggml-small.bin",
                "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin",
                77_691_713,
            ),
        ),
    )
    with tempfile.TemporaryDirectory(prefix="streamlight-asr-smoke-") as directory:
        root = Path(directory)
        manager = ModelManager(root / "models", registry=(tiny,))
        ModelDownloader(manager).download(tiny)
        source = root / "tone.wav"
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=1.5",
                "-ac",
                "1",
                "-ar",
                "16000",
                str(source),
            ],
            check=True,
            capture_output=True,
        )
        asset = MediaAsset.create(source, kind="video", duration=1.5, has_audio=True)
        analyzer = OfflineIntelligenceAnalyzer(manager)
        subtitles, evidence = analyzer._transcribe(asset)
        print(f"ASR_RUNTIME_OK subtitles={len(subtitles)} evidence={len(evidence)}")


if __name__ == "__main__":
    run()
