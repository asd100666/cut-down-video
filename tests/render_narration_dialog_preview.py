from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from streamlight.editor_models import EditProject, MediaAsset, SubtitleCue
from streamlight.editor_widget import NarrationDialog, NarrationRecipeDialog
from streamlight.model_manager import ModelManager
from streamlight.styles import APP_STYLE


def run() -> tuple[Path, Path]:
    QCoreApplication.setOrganizationName("Streamlight")
    QCoreApplication.setOrganizationDomain("streamlight.local")
    QCoreApplication.setApplicationName("流光下载器")
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    manager = ModelManager()

    recipe = NarrationRecipeDialog(manager)
    recipe.show()
    app.processEvents()
    recipe_output = PROJECT_ROOT / "artifacts" / "ui-v3.1-narration-recipe.png"
    recipe.grab().save(str(recipe_output))
    recipe.close()

    with tempfile.TemporaryDirectory(prefix="streamlight-narration-dialog-") as directory:
        source = Path(directory) / "sample.mp4"
        source.write_bytes(b"fixture")
        project = EditProject(name="智能解说演示")
        asset = project.add_asset(MediaAsset.create(source, kind="video", duration=8, has_audio=True))
        project.append_video_asset(asset.id)
        project.subtitle_cues.append(SubtitleCue("subtitle", asset.id, 1, 3, "这是一段可编辑字幕", 0.9))
        review = NarrationDialog(
            project,
            "从工作台总览开始，智能分镜与字幕轨让自动结果仍可继续人工修改。",
            "本地 Qwen2.5 3B（llama.cpp）",
            "summary",
        )
        review.show()
        app.processEvents()
        review_output = PROJECT_ROOT / "artifacts" / "ui-v3.1-narration-review.png"
        review.grab().save(str(review_output))
        review.close()
    print(recipe_output)
    print(review_output)
    return recipe_output, review_output


if __name__ == "__main__":
    run()
