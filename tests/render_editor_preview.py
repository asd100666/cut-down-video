from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from streamlight.editor_models import MediaAsset
from streamlight.main_window import MainWindow
from streamlight.styles import APP_STYLE


def main() -> int:
    QCoreApplication.setOrganizationName("StreamlightPreview")
    QCoreApplication.setApplicationName("StreamlightPreview")
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    window = MainWindow()
    editor = window.editor_workbench
    first = editor.project.add_asset(
        MediaAsset.create(
            PROJECT_ROOT / "samples" / "访谈长视频.mp4",
            kind="video",
            duration=5420.8,
            width=1920,
            height=1080,
            fps=25,
            has_audio=True,
        )
    )
    second = editor.project.add_asset(
        MediaAsset.create(
            PROJECT_ROOT / "samples" / "补充镜头.mp4",
            kind="video",
            duration=182.4,
            width=3840,
            height=2160,
            fps=30,
            has_audio=True,
        )
    )
    music = editor.project.add_asset(
        MediaAsset.create(
            PROJECT_ROOT / "samples" / "背景音乐.wav",
            kind="audio",
            duration=240,
            has_audio=True,
        )
    )
    editor.project.append_video_asset(first.id)
    editor.project.update_clip(0, in_point=82.5, out_point=104.8, volume=0.85, muted=False)
    editor.project.append_video_asset(second.id)
    editor.project.update_clip(1, in_point=12.1, out_point=19.6, volume=0.0, muted=True)
    editor.project.duplicate_clip(0)
    editor.project.update_clip(1, in_point=220.0, out_point=235.4, volume=1.0, muted=False)
    track = editor.project.add_audio_asset(music.id)
    track.start_time = 1.5
    track.volume = 0.35
    editor.project.name = "长视频精华研究"
    editor._refresh_all()
    window._switch_workspace(1)
    window.show()
    app.processEvents()
    output = PROJECT_ROOT / "artifacts" / "ui-v3-editor-default.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    if not window.grab().save(str(output)):
        raise RuntimeError("无法保存剪辑工作台预览图")
    print(output)

    window.resize(1600, 1000)
    app.processEvents()
    expanded_output = PROJECT_ROOT / "artifacts" / "ui-v3-editor-expanded.png"
    if not window.grab().save(str(expanded_output)):
        raise RuntimeError("无法保存扩展后的剪辑工作台预览图")
    print(expanded_output)

    editor.toggle_preview_fullscreen()
    app.processEvents()
    fullscreen_output = PROJECT_ROOT / "artifacts" / "ui-v3-editor-fullscreen.png"
    if editor._fullscreen_dialog is None or not editor._fullscreen_dialog.grab().save(str(fullscreen_output)):
        raise RuntimeError("无法保存全屏播放器预览图")
    print(fullscreen_output)
    editor.toggle_preview_fullscreen()
    app.processEvents()
    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
