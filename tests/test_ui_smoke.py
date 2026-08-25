from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication
from PySide6.QtCore import Qt
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
)

from streamlight.main_window import MainWindow
from streamlight.model_dialog import ModelManagerDialog
from streamlight.editor_widget import NarrationRecipeDialog, TIMELINE_PANEL_MAX_HEIGHT
from streamlight.editor_models import MediaAsset
from streamlight.models import BatchMediaItem, MediaSummary
from streamlight.styles import APP_STYLE, HEADER_ACTION_HEIGHT, HEADER_STATUS_HEIGHT


class UiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        QCoreApplication.setOrganizationName("StreamlightTests")
        QCoreApplication.setApplicationName("StreamlightTests")
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_constructs_and_starts_idle(self) -> None:
        window = MainWindow()
        self.assertEqual(window.windowTitle(), "流光媒体工作台")
        self.assertFalse(window.download_button.isEnabled())
        self.assertTrue(window.analyze_button.isEnabled())
        self.assertIsInstance(window.url_input, QPlainTextEdit)
        self.assertEqual((window.minimumWidth(), window.minimumHeight()), (1180, 760))
        self.assertGreater(window.maximumWidth(), window.minimumWidth())
        self.assertGreater(window.maximumHeight(), window.minimumHeight())
        self.assertTrue(window.windowFlags() & Qt.WindowType.WindowMaximizeButtonHint)
        self.assertEqual((window.width(), window.height()), (1240, 860))
        self.assertEqual(window.findChildren(QScrollArea), [])
        self.assertFalse(window.windowIcon().isNull())
        self.assertIn("本地模型", window.model_button.text())
        self.assertEqual(window.model_manager.summary()[1], 7)
        self.assertEqual(window.workspace_stack.count(), 2)
        self.assertEqual(window.workspace_stack.currentIndex(), 0)
        self.assertTrue(window.download_tab.isChecked())
        self.assertEqual(
            window.log_output.verticalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )

        window.show()
        self.app.processEvents()
        self.assertLess(
            window.open_folder_button.geometry().left(),
            window.batch_download_button.geometry().left(),
        )
        self.assertEqual(window.url_card.height(), window.media_card.height())
        self.assertEqual(
            {
                window.ytdlp_badge.height(),
                window.ffmpeg_badge.height(),
                window.model_button.height(),
            },
            {HEADER_STATUS_HEIGHT},
        )
        dependency_centers = {
            window.ytdlp_badge.geometry().center().y(),
            window.ffmpeg_badge.geometry().center().y(),
            window.model_button.geometry().center().y(),
        }
        self.assertEqual(len(dependency_centers), 1)
        self.assertEqual(window.media_card.geometry().top(), window.url_card.geometry().bottom() + 13)
        self.assertEqual(window.settings_card.geometry().top(), window.media_card.geometry().bottom() + 13)
        self.assertEqual(window.download_card.geometry().top(), window.url_card.geometry().top())
        self.assertEqual(
            window.settings_card.geometry().bottom(),
            window.log_card.geometry().bottom(),
        )
        right_body_height = window.log_card.geometry().bottom() - window.download_card.geometry().top() + 1
        self.assertGreaterEqual(window.log_card.height(), right_body_height / 3)
        self.assertEqual(window.right_column.count(), 2)
        self.assertIs(window.right_column.itemAt(0).widget(), window.download_card)
        self.assertIs(window.right_column.itemAt(1).widget(), window.log_card)
        self.assertFalse(hasattr(window, "advanced_toggle"))
        self.assertTrue(window.advanced_panel.isVisible())
        self.assertEqual(
            [
                window.playlist_check.text(),
                window.subtitle_check.text(),
                window.auto_subtitle_check.text(),
                window.archive_check.text(),
            ],
            ["下载播放列表", "人工字幕", "自动字幕", "跳过重复项"],
        )
        labels = [label.text() for label in window.findChildren(QLabel)]
        self.assertNotIn("视频获取 · 可编辑剪辑 · 本地安全处理", labels)
        self.assertNotIn(
            "仅下载你有权保存的内容。本工具不绕过 DRM、付费墙或网站访问控制。",
            labels,
        )
        self.assertTrue(window.toast.isHidden())
        window.toast.show_message("测试提示", "这是一条倒计时信息", seconds=4)
        self.app.processEvents()
        self.assertTrue(window.toast.isVisible())
        self.assertEqual(window.toast.remaining, 4)
        self.assertFalse(window.brand_logo.is_active)
        window.url_input.setPlainText("https://example.com/one")
        window.url_input.moveCursor(window.url_input.textCursor().MoveOperation.End)
        before_blocks = window.url_input.blockCount()
        QTest.keyClick(window.url_input, Qt.Key.Key_Return)
        self.assertEqual(window.url_input.blockCount(), before_blocks + 1)
        button_texts = [button.text() for button in window.findChildren(QPushButton)]
        self.assertNotIn("粘贴", button_texts)
        self.assertIn("批量下载", button_texts)
        focus_rule = APP_STYLE.split("QCheckBox:focus", 1)[1].split("}", 1)[0]
        self.assertNotIn("2px solid", focus_rule)
        window._set_state("analyzing")
        self.assertTrue(window.brand_logo.is_active)
        window._set_state("idle")
        self.assertFalse(window.brand_logo.is_active)
        window.close()

    def test_editor_preview_expands_with_the_main_window(self) -> None:
        window = MainWindow()
        window._switch_workspace(1)
        window.show()
        self.app.processEvents()
        initial_preview = window.editor_workbench.video_widget.size()
        initial_timeline_height = window.editor_workbench.timeline_panel.height()
        window.toast.show_message("布局测试", "窗口变化时保持右上角定位", seconds=4)
        self.app.processEvents()
        initial_toast_x = window.toast.x()

        window.resize(1600, 1000)
        self.app.processEvents()

        expanded_preview = window.editor_workbench.video_widget.size()
        expanded_timeline_height = window.editor_workbench.timeline_panel.height()
        self.assertGreater(expanded_preview.width(), initial_preview.width())
        self.assertGreater(expanded_preview.height(), initial_preview.height())
        self.assertLessEqual(expanded_timeline_height, TIMELINE_PANEL_MAX_HEIGHT)
        self.assertLessEqual(expanded_timeline_height, initial_timeline_height + 1)
        self.assertGreater(window.toast.x(), initial_toast_x)
        window.close()

    def test_player_controls_stay_inside_surface_rate_fullscreen_and_timeline_scroll(self) -> None:
        window = MainWindow()
        window._switch_workspace(1)
        window.show()
        self.app.processEvents()
        editor = window.editor_workbench

        self.assertIs(editor.player_controls.parentWidget(), editor.preview_surface)
        self.assertIsNot(editor.player_controls.parentWidget(), editor.video_widget)
        self.assertTrue(editor.preview_surface.rect().contains(editor.player_controls.geometry()))
        self.assertTrue(editor.video_widget.geometry().contains(editor.player_controls.geometry()))
        editor.player_controls.hide()
        QTest.mouseMove(editor.video_widget.viewport(), editor.video_widget.viewport().rect().center())
        self.app.processEvents()
        self.assertTrue(editor.player_controls.isVisible())
        self.assertEqual(editor.play_button.text(), "播放")
        self.assertEqual(editor.fullscreen_button.text(), "全屏")
        self.assertEqual(editor.playback_rate_combo.currentData(), 1.0)

        rate_index = editor.playback_rate_combo.findData(1.5)
        editor.playback_rate_combo.setCurrentIndex(rate_index)
        self.app.processEvents()
        self.assertAlmostEqual(editor.player.playbackRate(), 1.5)

        self.assertFalse(editor.timeline_table.isVisible())
        self.assertTrue(editor.timeline_view.isVisible())
        self.assertEqual(
            editor.timeline_view.view.horizontalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )
        self.assertEqual(
            editor.timeline_view.view.verticalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )

        editor.toggle_preview_fullscreen()
        self.app.processEvents()
        self.assertIsNotNone(editor._fullscreen_dialog)
        self.assertTrue(editor._fullscreen_dialog.isFullScreen())
        self.assertEqual(editor.fullscreen_button.text(), "退出全屏")
        editor.toggle_preview_fullscreen()
        self.app.processEvents()
        self.assertIsNone(editor._fullscreen_dialog)
        self.assertIs(editor.preview_surface.parentWidget(), editor.preview_panel)
        window.close()

    def test_asset_preview_selects_new_import_autoplays_and_reports_errors(self) -> None:
        window = MainWindow()
        window._switch_workspace(1)
        editor = window.editor_workbench
        self.assertFalse(editor.asset_preview_button.isEnabled())
        self.assertFalse(editor.asset_to_timeline_button.isEnabled())

        asset = MediaAsset.create(
            "preview-fixture.mp4",
            kind="video",
            duration=3.0,
            width=640,
            height=360,
            fps=25.0,
            has_audio=True,
        )
        editor._on_asset_ready(asset)
        self.app.processEvents()
        selected = editor._selected_asset()
        self.assertIsNotNone(selected)
        self.assertEqual(selected.id, asset.id)
        self.assertTrue(editor.asset_preview_button.isEnabled())
        self.assertTrue(editor.asset_to_timeline_button.isEnabled())

        with patch.object(editor, "_load_preview") as load_preview:
            editor.preview_selected_asset()
            load_preview.assert_called_once_with(
                asset.path,
                0.0,
                autoplay=True,
                display_name=asset.name,
            )

        editor.asset_list.clearSelection()
        self.app.processEvents()
        self.assertFalse(editor.asset_preview_button.isEnabled())
        editor.preview_selected_asset()
        self.assertIn("请先在左侧素材库中选择", editor.editor_status.text())

        editor._preview_source_name = asset.name
        editor._on_player_error(QMediaPlayer.Error.FormatError)
        self.assertIn("预览失败", editor.editor_status.text())
        self.assertIn("H.264/AAC MP4", editor.editor_status.text())
        editor.dirty = False
        window.close()

    def test_model_manager_lists_required_models_and_missing_status(self) -> None:
        window = MainWindow()
        dialog = ModelManagerDialog(window.model_manager, window)
        dialog.show()
        self.app.processEvents()
        self.assertEqual(dialog.table.rowCount(), 7)
        self.assertIn("已安装", dialog.summary_label.text())
        self.assertTrue(dialog.manager.root.is_dir())
        self.assertEqual(dialog.summary_label.height(), HEADER_ACTION_HEIGHT)
        self.assertEqual(dialog.open_dir_button.height(), HEADER_ACTION_HEIGHT)
        self.assertEqual(
            dialog.summary_label.geometry().center().y(),
            dialog.open_dir_button.geometry().center().y(),
        )
        dialog.close()
        window.close()

    def test_narration_recipe_gates_qwen_and_uses_primary_confirmation(self) -> None:
        class NarrationModelState:
            def __init__(self, ready: bool) -> None:
                self.ready = ready

            def capability_ready(self, capability: str) -> bool:
                self.assert_narration(capability)
                return self.ready

            def capability_missing(self, capability: str) -> list[object]:
                self.assert_narration(capability)
                return [] if self.ready else [object(), object()]

            @staticmethod
            def assert_narration(capability: str) -> None:
                if capability != "narration":
                    raise AssertionError(capability)

        missing_dialog = NarrationRecipeDialog(NarrationModelState(False))
        self.assertFalse(missing_dialog.use_model.isEnabled())
        self.assertFalse(missing_dialog.use_model.isChecked())
        self.assertIn("缺少 2 项", missing_dialog.model_status.text())
        missing_dialog.close()

        ready_dialog = NarrationRecipeDialog(NarrationModelState(True))
        self.assertTrue(ready_dialog.use_model.isEnabled())
        self.assertTrue(ready_dialog.use_model.isChecked())
        self.assertEqual(ready_dialog.model_status.text(), "模型与运行时已就绪")
        button_box = ready_dialog.findChild(QDialogButtonBox)
        self.assertIsNotNone(button_box)
        confirm = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.assertEqual(confirm.objectName(), "PrimaryButton")
        self.assertEqual(confirm.text(), "生成可编辑草稿")
        ready_dialog.close()

    def test_editing_workbench_is_second_and_keeps_manual_controls(self) -> None:
        window = MainWindow()
        window._switch_workspace(1)
        editor = window.editor_workbench

        self.assertEqual(window.workspace_stack.currentIndex(), 1)
        self.assertTrue(window.editor_tab.isChecked())
        self.assertEqual(editor.project.source_recipe, "manual")
        self.assertEqual(editor.timeline_table.columnCount(), 7)
        self.assertEqual(editor.timeline_table.horizontalHeaderItem(5).text(), "依据")
        self.assertTrue(hasattr(editor, "clip_in"))
        self.assertTrue(hasattr(editor, "clip_out"))
        self.assertTrue(hasattr(editor, "split_button"))
        self.assertTrue(hasattr(editor, "move_up_button"))
        self.assertTrue(hasattr(editor, "delete_clip_button"))
        self.assertTrue(hasattr(editor, "audio_table"))
        self.assertTrue(hasattr(editor, "auto_highlight_button"))
        self.assertFalse(editor.auto_highlight_button.isEnabled())
        self.assertFalse(editor.export_button.isEnabled())
        self.assertFalse(editor.has_running_task)
        window.close()

    def test_large_result_queue_scrolls_inside_its_card(self) -> None:
        window = MainWindow()
        window._batch_items = [
            BatchMediaItem(url=f"https://example.com/video/{index}") for index in range(20)
        ]
        window._populate_result_rows()
        window.show()
        self.app.processEvents()

        self.assertEqual(
            window.results_list.verticalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )
        self.assertGreater(window.results_list.verticalScrollBar().maximum(), 0)
        self.assertTrue(window.download_card.rect().contains(window.results_list.geometry()))
        self.assertLess(window.results_list.height(), window.download_card.height())
        window.close()

    def test_batch_results_enable_only_successful_items(self) -> None:
        window = MainWindow()
        urls = ["https://example.com/ok", "bad-address"]
        window.url_input.setPlainText("\n".join(urls))
        window._input_snapshot = window.url_input.toPlainText().strip()
        window._batch_items = [BatchMediaItem(url=url) for url in urls]
        window._populate_result_rows()
        window._operation = "analysis"

        summary = MediaSummary(
            title="可下载视频",
            site="Generic",
            duration=65,
            uploader="测试来源",
            webpage_url=urls[0],
            thumbnail=None,
            available_heights=(720, 1080),
            format_count=2,
            is_live=False,
            is_playlist=False,
            playlist_count=None,
        )
        window._on_analyzed(0, urls[0], summary)
        window._on_analysis_failed(1, urls[1], "地址无效", "请输入完整地址")
        window._operation = None
        window._set_state("ready")

        self.assertEqual(window.results_list.count(), 2)
        self.assertTrue(window._result_rows[0].download_button.isEnabled())
        self.assertFalse(window._result_rows[1].download_button.isEnabled())
        self.assertTrue(window.batch_download_button.isEnabled())
        self.assertEqual(window._result_rows[0].status_label.text(), "可下载")
        self.assertEqual(window._result_rows[1].status_label.text(), "分析失败")
        window.close()


if __name__ == "__main__":
    unittest.main()
