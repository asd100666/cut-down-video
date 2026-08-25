from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PySide6.QtWidgets import QApplication, QWidget

from streamlight.editor_models import MediaAsset
from streamlight.editor_widget import HighlightDialog
from streamlight.model_manager import ModelManager
from streamlight.styles import APP_STYLE


def render() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    host = QWidget()
    asset = MediaAsset.create(
        PROJECT_ROOT / "artifacts" / "preview-long-video.mp4",
        kind="video",
        duration=5420.8,
        width=1920,
        height=1080,
        has_audio=True,
    )
    manager = ModelManager(PROJECT_ROOT / "artifacts" / "empty-model-preview")
    dialog = HighlightDialog([asset], asset.id, manager, None, host)
    dialog.show()
    app.processEvents()
    output = PROJECT_ROOT / "artifacts" / "ui-v2.2-highlight-model-gates.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    if not dialog.grab().save(str(output)):
        raise RuntimeError("无法保存自动精华模型开关预览")
    print(output)
    dialog.close()


if __name__ == "__main__":
    render()
