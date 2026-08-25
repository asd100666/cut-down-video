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
from streamlight.editor_models import SubtitleCue
from streamlight.model_manager import ModelDownloader, ModelManager
from streamlight.offline_intelligence import OfflineIntelligenceAnalyzer


def run() -> None:
    ffmpeg, _source = locate_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("未找到 FFmpeg")
    with tempfile.TemporaryDirectory(prefix="streamlight-intelligence-smoke-") as directory:
        root = Path(directory)
        manager = ModelManager(root / "models")
        for model_id in ("face-yunet", "person-mediapipe", "bge-small-zh", "clip-vit-base-patch32"):
            spec = manager.spec(model_id)
            ModelDownloader(manager).download(spec)
            if not manager.state(spec).ready:
                raise RuntimeError(f"模型未就绪：{model_id}")

        source = root / "sample.mp4"
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=s=320x180:d=2:r=12",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(source),
            ],
            check=True,
            capture_output=True,
        )
        asset = probe_media(source, ffmpeg)
        analyzer = OfflineIntelligenceAnalyzer(manager)
        visual_evidence, visual_scores = analyzer._analyze_visual(asset, [0.5, 1.5])
        text_vectors = analyzer._text_embeddings(["这是中文语义测试。", "另一个不同主题的句子。"])
        cues = [
            SubtitleCue("cue_1", asset.id, 0.0, 0.9, "这是中文语义测试。", 0.9),
            SubtitleCue("cue_2", asset.id, 1.0, 1.9, "另一个不同主题的句子。", 0.9),
        ]
        semantic_evidence, semantic_scores = analyzer._analyze_semantic(asset, [0.5, 1.5], cues)
        if len(visual_evidence) != 2 or len(visual_scores) != 2:
            raise RuntimeError("视觉证据数量异常")
        if text_vectors.shape[0] != 2 or text_vectors.shape[1] < 64:
            raise RuntimeError(f"文本向量形状异常：{text_vectors.shape}")
        if len(semantic_evidence) != 2 or len(semantic_scores) != 2:
            raise RuntimeError("完整语义证据数量异常")
        print(
            "INTELLIGENCE_RUNTIME_OK "
            f"visual={len(visual_evidence)} text_shape={tuple(text_vectors.shape)} "
            f"visual_scores={[round(value, 3) for value in visual_scores.values()]} "
            f"semantic_scores={[round(value, 3) for value in semantic_scores.values()]}"
        )


if __name__ == "__main__":
    run()
