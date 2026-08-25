from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QPoint, QUrl
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from streamlight.dependencies import locate_ffmpeg
from streamlight.editor_models import MediaAsset
from streamlight.editor_widget import EditorWorkbench
from streamlight.styles import APP_STYLE


def wait_until(app: QApplication, predicate, timeout: float = 8.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return bool(predicate())


def run() -> None:
    ffmpeg, _source = locate_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("未找到 FFmpeg")

    with tempfile.TemporaryDirectory(prefix="streamlight-player-smoke-") as directory:
        video = Path(directory) / "player.mp4"
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=640x360:rate=25:duration=3",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=3",
                "-shortest",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                str(video),
            ],
            check=True,
            capture_output=True,
        )

        app = QApplication.instance() or QApplication([])
        app.setStyle("Fusion")
        app.setStyleSheet(APP_STYLE)
        editor = EditorWorkbench()
        editor.resize(1000, 760)
        editor.show()
        asset = MediaAsset.create(
            video,
            kind="video",
            duration=3.0,
            width=640,
            height=360,
            fps=25.0,
            has_audio=True,
        )
        editor.project.add_asset(asset)
        editor._refresh_all(asset_id=asset.id)
        editor.preview_selected_asset()
        if not wait_until(app, lambda: editor.player.duration() >= 2500):
            raise RuntimeError(f"预览视频未就绪：duration={editor.player.duration()}")

        if not wait_until(app, lambda: editor.player.position() >= 250):
            raise RuntimeError(f"一键预览未自动播放：position={editor.player.position()}")
        if editor.player_controls.parentWidget() is editor.video_widget:
            raise RuntimeError("播放器控制条仍挂在原生视频表面下")
        if not editor.preview_surface.rect().contains(editor.player_controls.geometry()):
            raise RuntimeError("播放器控制层超出了视频容器")
        QTest.mouseMove(editor, QPoint(4, 4))
        if not wait_until(app, lambda: not editor.player_controls.isVisible(), timeout=3.0):
            raise RuntimeError("鼠标移出视频后控制层没有自动隐藏")
        QTest.mouseMove(editor.video_widget.viewport(), editor.video_widget.viewport().rect().center())
        if not wait_until(app, editor.player_controls.isVisible):
            raise RuntimeError("鼠标移入视频后控制层没有显示")
        editor.raise_()
        editor.activateWindow()
        app.processEvents()
        active_output = PROJECT_ROOT / "artifacts" / "ui-v3-editor-player-active.png"
        screen = QApplication.primaryScreen()
        if screen is None or not screen.grabWindow(int(editor.winId())).save(str(active_output)):
            raise RuntimeError("无法保存播放中播放器验收图")
        editor.toggle_playback()

        editor.position_slider.sliderMoved.emit(1200)
        if not wait_until(app, lambda: abs(editor.player.position() - 1200) <= 250):
            raise RuntimeError(f"进度拖动未生效：position={editor.player.position()}")

        editor.playback_rate_combo.setCurrentIndex(editor.playback_rate_combo.findData(1.5))
        app.processEvents()
        if abs(editor.player.playbackRate() - 1.5) > 0.01:
            raise RuntimeError(f"倍速未生效：rate={editor.player.playbackRate()}")

        editor.toggle_preview_fullscreen()
        app.processEvents()
        if editor._fullscreen_dialog is None or not editor._fullscreen_dialog.isFullScreen():
            raise RuntimeError("未进入全屏预览")
        editor.toggle_preview_fullscreen()
        if not wait_until(app, lambda: editor._fullscreen_dialog is None):
            raise RuntimeError("未从全屏返回原预览区")

        final_position = editor.player.position()
        final_duration = editor.player.duration()
        editor.player.stop()
        editor.player.setSource(QUrl())
        editor.close()
        editor.deleteLater()
        app.processEvents()
        time.sleep(0.1)
        app.processEvents()
        print(
            "PLAYER_RUNTIME_OK "
            f"duration={final_duration} "
            f"seek_position={final_position} hover_controls=true autoplay=true "
            "rate=1.5 fullscreen_roundtrip=true"
        )


if __name__ == "__main__":
    run()
