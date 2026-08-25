from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from streamlight.main_window import MainWindow
from streamlight.model_dialog import ModelManagerDialog
from streamlight.styles import APP_STYLE


def main() -> int:
    QCoreApplication.setOrganizationName("StreamlightPreview")
    QCoreApplication.setApplicationName("StreamlightModelPreview")
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    window = MainWindow()
    window.show()
    dialog = ModelManagerDialog(window.model_manager, window)
    dialog.show()
    app.processEvents()
    output = PROJECT_ROOT / "artifacts" / "ui-v2.2.3-model-manager-alignment.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    if not dialog.grab().save(str(output)):
        raise RuntimeError("无法保存模型管理预览图")
    print(output)

    transfer_spec = window.model_manager.spec("person-mediapipe")
    dialog._active_spec = transfer_spec
    dialog.cancel_button.show()
    dialog._on_progress(256 * 1024, transfer_spec.total_size, "下载 · person_detection_mediapipe_2023mar.onnx")
    time.sleep(0.08)
    dialog._on_progress(512 * 1024, transfer_spec.total_size, "下载 · person_detection_mediapipe_2023mar.onnx")
    app.processEvents()
    transfer_output = PROJECT_ROOT / "artifacts" / "ui-v2.2.3-model-transfer.png"
    if not dialog.grab().save(str(transfer_output)):
        raise RuntimeError("无法保存模型传输预览图")
    print(transfer_output)
    dialog.close()
    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
