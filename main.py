from __future__ import annotations

import sys
import traceback
import shutil

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QMessageBox

from streamlight import __version__
from streamlight.icons import app_icon
from streamlight.main_window import MainWindow
from streamlight.styles import APP_STYLE


def check_ai_runtimes() -> int:
    """Packaged/source diagnostic for lazy-loaded offline inference dependencies."""
    try:
        import cv2
        import numpy
        import onnxruntime
        import pywhispercpp.model
        import tokenizers

        from streamlight.model_manager import ModelManager
        from streamlight.narration_engine import LocalNarrationGenerator

        if not cv2.__version__ or not numpy.__version__ or not onnxruntime.get_available_providers():
            raise RuntimeError("运行时版本或 ONNX 执行提供器无效")
        if not tokenizers.__version__ or pywhispercpp.model.Model is None:
            raise RuntimeError("Tokenizer 或 Whisper 运行时无效")
        manager = ModelManager()
        narration_runtime = manager.spec("llama-cpp-runtime")
        qwen_model = manager.spec("qwen2.5-3b-instruct")
        managed_components = len(manager.registry)
        if managed_components != 7:
            raise RuntimeError(f"模型注册数量异常：{managed_components}/7")
        if not narration_runtime.files or not qwen_model.files:
            raise RuntimeError("智能解说模型注册信息无效")
        if LocalNarrationGenerator is None:
            raise RuntimeError("智能解说生成器无效")
    except BaseException as error:
        print(f"AI_RUNTIME_CHECK_FAILED: {error}", file=sys.stderr)
        return 1
    transfer_backend = "curl+urllib" if shutil.which("curl.exe" if sys.platform == "win32" else "curl") else "urllib"
    print(
        "AI_RUNTIME_CHECK_OK "
        f"MANAGED_COMPONENTS={managed_components} "
        "NARRATION_EXTERNAL_LLAMA_CPP=READY "
        f"DOWNLOAD_BACKEND={transfer_backend}"
    )
    return 0


def main() -> int:
    QCoreApplication.setOrganizationName("Streamlight")
    QCoreApplication.setOrganizationDomain("streamlight.local")
    QCoreApplication.setApplicationName("流光下载器")
    QCoreApplication.setApplicationVersion(__version__)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#218B60"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)
    app.setStyleSheet(APP_STYLE)
    app.setWindowIcon(app_icon())
    app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)

    def handle_exception(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(details, file=sys.stderr)
        QMessageBox.critical(None, "应用发生错误", f"发生未处理错误：\n{exc_value}")

    sys.excepthook = handle_exception

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    if "--check-ai-runtimes" in sys.argv:
        raise SystemExit(check_ai_runtimes())
    raise SystemExit(main())
