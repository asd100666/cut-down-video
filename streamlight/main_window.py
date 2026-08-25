from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSize, QThread, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices, QResizeEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .dependencies import dependency_status
from .editor_widget import EditorWorkbench
from .engine import parse_url_lines, validate_http_url
from .icons import AnimatedLogoWidget, app_icon, svg_icon
from .models import BatchMediaItem, FORMAT_PRESETS, DownloadRequest, MediaSummary, ProgressUpdate
from .model_dialog import ModelManagerDialog
from .model_manager import ModelManager
from .settings import AppSettings, SettingsStore
from .styles import HEADER_STATUS_HEIGHT
from .toast import CountdownToast
from .workers import BatchAnalyzeWorker, BatchDownloadWorker, BatchWorkerBase


class BatchResultRow(QFrame):
    download_requested = Signal(int)

    def __init__(self, index: int, url: str) -> None:
        super().__init__(objectName="BatchResultRow")
        self.index = index
        self._summary: MediaSummary | None = None
        self._summary_meta = ""
        self.setToolTip(url)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 9, 7)
        layout.setSpacing(10)

        self.status_label = QLabel("等待分析", objectName="ResultStatus")
        self.status_label.setProperty("kind", "pending")
        self.status_label.setFixedWidth(66)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        self.title_label = QLabel(url, objectName="ResultTitle")
        self.meta_label = QLabel("等待分析", objectName="ResultMeta")
        self.title_label.setToolTip(url)
        self.meta_label.setToolTip(url)
        text_box.addWidget(self.title_label)
        text_box.addWidget(self.meta_label)
        layout.addLayout(text_box, 1)

        self.download_button = QPushButton("下载")
        self.download_button.setIcon(svg_icon("download"))
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(lambda: self.download_requested.emit(self.index))
        layout.addWidget(self.download_button)

    def _set_status(self, text: str, kind: str) -> None:
        self.status_label.setText(text)
        self.status_label.setProperty("kind", kind)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def set_analyzing(self) -> None:
        self._set_status("分析中", "working")
        self.meta_label.setText("正在识别页面和媒体格式")
        self.download_button.setEnabled(False)

    def set_success(self, summary: MediaSummary) -> None:
        self._summary = summary
        self._set_status("可下载", "success")
        self.title_label.setText(summary.title)
        self.title_label.setToolTip(summary.title)
        playlist = f" · 列表 {summary.playlist_count or '未知'} 项" if summary.is_playlist else ""
        meta = f"{summary.site} · {summary.duration_text} · {summary.quality_text}{playlist}"
        self._summary_meta = meta
        self.meta_label.setText(meta)
        self.meta_label.setToolTip(meta)

    def set_failed(self, title: str, detail: str) -> None:
        self._summary = None
        self._set_status("分析失败", "error")
        self.title_label.setText(title)
        self.meta_label.setText(detail)
        self.title_label.setToolTip(title)
        self.meta_label.setToolTip(detail)
        self.download_button.setEnabled(False)

    def set_queued(self) -> None:
        self._set_status("等待下载", "pending")
        if self._summary_meta:
            self.meta_label.setText(self._summary_meta)
            self.meta_label.setToolTip(self._summary_meta)
        self.download_button.setEnabled(False)

    def set_downloading(self) -> None:
        self._set_status("下载中", "working")
        self.download_button.setEnabled(False)

    def set_completed(self) -> None:
        self._set_status("已完成", "success")
        self.download_button.setEnabled(False)

    def set_download_failed(self, detail: str) -> None:
        self._set_status("下载失败", "error")
        self.meta_label.setText(detail)
        self.meta_label.setToolTip(detail)
        self.download_button.setEnabled(False)

    def set_action_enabled(self, enabled: bool) -> None:
        self.download_button.setEnabled(enabled and self._summary is not None)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("流光媒体工作台")
        self.setWindowIcon(app_icon())
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.setMinimumSize(1180, 760)
        self.resize(1240, 860)

        self._settings_store = SettingsStore()
        self._settings = self._settings_store.load()
        self.model_manager = ModelManager()
        self._thread: QThread | None = None
        self._worker: BatchWorkerBase | None = None
        self._operation: str | None = None
        self._batch_items: list[BatchMediaItem] = []
        self._result_rows: dict[int, BatchResultRow] = {}
        self._input_snapshot = ""
        self._download_indices: list[int] = []
        self._download_position = 0
        self._download_success_count = 0
        self._download_failure_count = 0
        self._operation_cancelled = False
        self._last_output_dir = self._settings.output_dir
        self._pending_close = False

        self._build_ui()
        self._restore_settings()
        self._refresh_dependency_badges()
        self._set_state("idle")

    def _build_ui(self) -> None:
        root = QWidget(objectName="AppRoot")
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 16, 18, 12)
        root_layout.setSpacing(11)

        header = self._create_header()
        header.setFixedHeight(74)
        root_layout.addWidget(header)

        self.workspace_stack = QStackedWidget(objectName="WorkspaceStack")
        self.workspace_stack.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        download_page = QWidget(objectName="DownloadWorkbench")
        body = QHBoxLayout(download_page)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(12)

        left = QVBoxLayout()
        self.left_column = left
        left.setSpacing(12)
        self.url_card = self._create_url_card()
        self.url_card.setFixedHeight(154)
        left.addWidget(self.url_card)
        self.media_card = self._create_media_card()
        self.media_card.setFixedHeight(154)
        left.addWidget(self.media_card)
        self.settings_card = self._create_settings_card()
        left.addWidget(self.settings_card, 1)

        right = QVBoxLayout()
        self.right_column = right
        right.setSpacing(12)
        self.download_card = self._create_download_card()
        right.addWidget(self.download_card, 63)
        self.log_card = self._create_log_card()
        right.addWidget(self.log_card, 37)

        body.addLayout(left, 47)
        body.addLayout(right, 53)
        self.workspace_stack.addWidget(download_page)
        self.editor_workbench = EditorWorkbench(self.model_manager, self.open_model_manager)
        self.editor_workbench.busy_changed.connect(self._on_editor_busy_changed)
        self.workspace_stack.addWidget(self.editor_workbench)
        root_layout.addWidget(self.workspace_stack, 1)
        self.toast = CountdownToast(root)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "toast") and self.toast.isVisible():
            self.toast.reposition()

    def _switch_workspace(self, index: int) -> None:
        self.workspace_stack.setCurrentIndex(index)
        if index == 0:
            self.download_tab.setChecked(True)
        else:
            self.editor_tab.setChecked(True)

    def _on_editor_busy_changed(self, busy: bool) -> None:
        self.editor_tab.setProperty("busy", busy)
        self.editor_tab.style().unpolish(self.editor_tab)
        self.editor_tab.style().polish(self.editor_tab)
        if not busy and self._pending_close:
            QTimer.singleShot(0, self.close)

    def _card(self) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame(objectName="Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        return card, card_layout

    def _section_heading(self, step: str, title: str, hint: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        step_label = QLabel(step)
        step_label.setObjectName("StepBadge")
        step_label.setFixedSize(27, 27)
        step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label = QLabel(title, objectName="CardTitle")
        hint_label = QLabel(hint, objectName="Hint")
        hint_label.setWordWrap(True)
        row.addWidget(step_label)
        row.addWidget(title_label)
        row.addWidget(hint_label, 1)
        return row

    def _create_header(self) -> QFrame:
        frame = QFrame(objectName="HeaderCard")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(12)

        self.brand_logo = AnimatedLogoWidget(50)
        layout.addWidget(self.brand_logo)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title_box.addWidget(QLabel("流光媒体工作台", objectName="BrandTitle"))
        layout.addLayout(title_box)
        self.workspace_tabs = QButtonGroup(self)
        self.workspace_tabs.setExclusive(True)
        self.download_tab = QPushButton("下载工作台", objectName="WorkspaceTab")
        self.editor_tab = QPushButton("剪辑工作台", objectName="WorkspaceTab")
        for index, button in enumerate((self.download_tab, self.editor_tab)):
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, page=index: self._switch_workspace(page))
            self.workspace_tabs.addButton(button, index)
            layout.addWidget(button)
        self.download_tab.setChecked(True)
        layout.addStretch(1)

        self.ytdlp_badge = QLabel()
        self.ffmpeg_badge = QLabel()
        self.model_button = QPushButton(objectName="ModelStatusButton")
        self.model_button.setIcon(svg_icon("sparkles"))
        self.model_button.clicked.connect(self.open_model_manager)
        for control in (self.ytdlp_badge, self.ffmpeg_badge, self.model_button):
            control.setFixedHeight(HEADER_STATUS_HEIGHT)
        self.ytdlp_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ffmpeg_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.ytdlp_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.ffmpeg_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.model_button, 0, Qt.AlignmentFlag.AlignVCenter)
        return frame

    def open_model_manager(self) -> None:
        dialog = ModelManagerDialog(self.model_manager, self)
        dialog.models_changed.connect(self._refresh_model_badge)
        dialog.exec()
        self._refresh_model_badge()

    def _refresh_model_badge(self) -> None:
        ready, total = self.model_manager.summary()
        self.model_button.setText(f"本地模型 {ready}/{total}")
        self.model_button.setProperty("kind", "success" if ready == total else "warning")
        missing = [spec.name for spec in self.model_manager.registry if not self.model_manager.state(spec).ready]
        self.model_button.setToolTip("所有模型已安装" if not missing else "缺失或未校验：\n" + "\n".join(missing))
        self.model_button.style().unpolish(self.model_button)
        self.model_button.style().polish(self.model_button)

    def _create_url_card(self) -> QFrame:
        card, layout = self._card()
        layout.addLayout(self._section_heading("1", "添加视频", "支持播放页、m3u8、mpd 和普通媒体直链"))

        row = QHBoxLayout()
        row.setSpacing(9)
        self.url_input = QPlainTextEdit(objectName="UrlInput")
        self.url_input.setPlaceholderText("每行粘贴一个完整的视频地址，按 Enter 换行")
        self.url_input.setAccessibleName("视频网址列表")
        self.url_input.setFixedHeight(76)
        self.url_input.textChanged.connect(self._on_url_changed)
        row.addWidget(self.url_input, 1)

        self.analyze_button = QPushButton("批量分析", objectName="PrimaryButton")
        self.analyze_button.setIcon(svg_icon("search", "#FFFFFF"))
        self.analyze_button.clicked.connect(self.start_analysis)
        row.addWidget(self.analyze_button, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(row)

        return card

    def _create_media_card(self) -> QFrame:
        self.media_card, layout = self._card()
        layout.addLayout(self._section_heading("2", "媒体信息", "确认标题、来源和可用清晰度"))

        panel = QFrame(objectName="InfoPanel")
        panel_layout = QHBoxLayout(panel)
        panel_layout.setContentsMargins(15, 13, 15, 13)
        panel_layout.setSpacing(13)

        self.media_icon = QLabel()
        self.media_icon.setObjectName("MediaIcon")
        self.media_icon.setFixedSize(44, 44)
        self.media_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.media_icon.setPixmap(svg_icon("play", "#218B60", 20).pixmap(20, 20))
        panel_layout.addWidget(self.media_icon)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        self.media_title = QLabel("等待批量分析", objectName="MediaTitle")
        self.media_title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.media_title.setWordWrap(True)
        self.media_meta = QLabel("每行输入一个地址，分析结果将在下载队列中逐项显示", objectName="MediaMeta")
        self.media_meta.setWordWrap(True)
        text_layout.addWidget(self.media_title)
        text_layout.addWidget(self.media_meta)
        panel_layout.addLayout(text_layout, 1)
        layout.addWidget(panel)
        return self.media_card

    def _create_settings_card(self) -> QFrame:
        card, layout = self._card()
        layout.addLayout(self._section_heading("3", "下载设置", "默认设置适合大多数网站"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("画质"), 0, 0)
        self.preset_combo = QComboBox()
        self.preset_combo.setAccessibleName("下载画质")
        for preset in FORMAT_PRESETS:
            self.preset_combo.addItem(preset.label, preset.key)
        grid.addWidget(self.preset_combo, 1, 0)

        grid.addWidget(QLabel("浏览器登录状态"), 0, 1)
        self.browser_combo = QComboBox()
        self.browser_combo.setAccessibleName("浏览器登录状态")
        self.browser_combo.addItem("不读取 Cookie", "")
        self.browser_combo.addItem("Chrome", "chrome")
        self.browser_combo.addItem("Microsoft Edge", "edge")
        self.browser_combo.addItem("Firefox", "firefox")
        grid.addWidget(self.browser_combo, 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        output_label = QLabel("保存到")
        layout.addWidget(output_label)
        output_row = QHBoxLayout()
        output_row.setSpacing(9)
        self.output_input = QLineEdit()
        self.output_input.setAccessibleName("保存目录")
        output_row.addWidget(self.output_input, 1)
        browse_button = QPushButton("选择目录")
        browse_button.setIcon(svg_icon("folder"))
        browse_button.clicked.connect(self._choose_output_dir)
        output_row.addWidget(browse_button)
        layout.addLayout(output_row)

        layout.addWidget(QLabel("高级选项", objectName="SubsectionTitle"))

        self.advanced_panel = QFrame(objectName="InfoPanel")
        advanced = QGridLayout(self.advanced_panel)
        advanced.setContentsMargins(13, 12, 13, 12)
        advanced.setHorizontalSpacing(10)
        advanced.setVerticalSpacing(8)

        advanced.addWidget(QLabel("Referer"), 0, 0)
        self.referer_input = QLineEdit()
        self.referer_input.setPlaceholderText("仅在网站要求防盗链来源时填写")
        advanced.addWidget(self.referer_input, 0, 1)

        advanced.addWidget(QLabel("User-Agent"), 1, 0)
        self.user_agent_input = QLineEdit()
        self.user_agent_input.setPlaceholderText("留空时使用 yt-dlp 默认值")
        advanced.addWidget(self.user_agent_input, 1, 1)

        checks = QGridLayout()
        checks.setHorizontalSpacing(28)
        checks.setVerticalSpacing(10)
        self.playlist_check = QCheckBox("下载播放列表")
        self.playlist_check.setToolTip("允许下载播放页中包含的整个播放列表")
        self.subtitle_check = QCheckBox("人工字幕")
        self.subtitle_check.setToolTip("下载视频作者或平台提供的人工字幕")
        self.auto_subtitle_check = QCheckBox("自动字幕")
        self.auto_subtitle_check.setToolTip("下载平台自动生成的字幕")
        self.archive_check = QCheckBox("跳过重复项")
        self.archive_check.setToolTip("记录已完成项目，再次下载时自动跳过")
        checks.addWidget(self.playlist_check, 0, 0)
        checks.addWidget(self.subtitle_check, 0, 1)
        checks.addWidget(self.auto_subtitle_check, 1, 0)
        checks.addWidget(self.archive_check, 1, 1)
        checks.setColumnStretch(0, 1)
        checks.setColumnStretch(1, 1)
        advanced.addLayout(checks, 2, 0, 1, 2)
        advanced.setColumnStretch(1, 1)
        layout.addWidget(self.advanced_panel)
        return card

    def _create_download_card(self) -> QFrame:
        card, layout = self._card()
        heading = self._section_heading("4", "下载队列", "仅成功项目可下载")

        self.open_folder_button = QPushButton("打开目录")
        self.open_folder_button.setIcon(svg_icon("folder"))
        self.open_folder_button.clicked.connect(self._open_output_dir)
        heading.addWidget(self.open_folder_button)

        self.batch_download_button = QPushButton("批量下载", objectName="PrimaryButton")
        self.batch_download_button.setIcon(svg_icon("download", "#FFFFFF"))
        self.batch_download_button.clicked.connect(self.start_batch_download)
        heading.addWidget(self.batch_download_button)
        self.download_button = self.batch_download_button

        self.cancel_button = QPushButton("取消", objectName="DangerButton")
        self.cancel_button.setIcon(svg_icon("cancel", "#9A3345"))
        self.cancel_button.clicked.connect(self.cancel_operation)
        heading.addWidget(self.cancel_button)
        layout.addLayout(heading)

        self.results_list = QListWidget(objectName="BatchResults")
        self.results_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.results_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.results_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.results_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.results_list.setSpacing(5)
        layout.addWidget(self.results_list, 1)
        self._show_results_placeholder()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setAccessibleName("下载进度")
        layout.addWidget(self.progress_bar)

        progress_row = QHBoxLayout()
        self.task_status = QLabel("等待分析", objectName="QueueStatus")
        self.progress_label = QLabel("0%", objectName="Muted")
        self.speed_label = QLabel("", objectName="Muted")
        self.eta_label = QLabel("", objectName="Muted")
        progress_row.addWidget(self.task_status)
        progress_row.addStretch(1)
        progress_row.addWidget(self.progress_label)
        progress_row.addWidget(self.speed_label)
        progress_row.addWidget(self.eta_label)
        layout.addLayout(progress_row)

        return card

    def _create_log_card(self) -> QFrame:
        card, layout = self._card()
        header = QHBoxLayout()
        header.addWidget(QLabel("运行记录", objectName="CardTitle"))
        header.addWidget(QLabel("敏感请求参数会自动隐藏", objectName="Hint"))
        header.addStretch(1)
        clear_button = QToolButton()
        clear_button.setText("清空")
        clear_button.clicked.connect(self._clear_log)
        header.addWidget(clear_button)
        layout.addLayout(header)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumBlockCount(500)
        self.log_output.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.log_output.setPlaceholderText("分析和下载信息将显示在这里")
        layout.addWidget(self.log_output, 1)
        return card

    def _restore_settings(self) -> None:
        settings = self._settings
        self.output_input.setText(settings.output_dir)
        self._select_combo_data(self.preset_combo, settings.preset_key)
        self._select_combo_data(self.browser_combo, settings.cookie_browser)
        self.referer_input.setText(settings.referer)
        self.user_agent_input.setText(settings.user_agent)
        self.playlist_check.setChecked(settings.allow_playlist)
        self.subtitle_check.setChecked(settings.write_subtitles)
        self.auto_subtitle_check.setChecked(settings.write_auto_subtitles)
        self.archive_check.setChecked(settings.use_archive)

    @staticmethod
    def _select_combo_data(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _collect_settings(self) -> AppSettings:
        return AppSettings(
            output_dir=self.output_input.text().strip(),
            preset_key=str(self.preset_combo.currentData()),
            cookie_browser=str(self.browser_combo.currentData()),
            referer=self.referer_input.text().strip(),
            user_agent=self.user_agent_input.text().strip(),
            allow_playlist=self.playlist_check.isChecked(),
            write_subtitles=self.subtitle_check.isChecked(),
            write_auto_subtitles=self.auto_subtitle_check.isChecked(),
            use_archive=self.archive_check.isChecked(),
        )

    def _prepare_request_context(self) -> tuple[AppSettings, Path]:
        settings = self._collect_settings()
        output = settings.output_dir.strip()
        if not output:
            raise ValueError("请选择有效的保存目录")

        output_path = Path(output).expanduser()
        output_path.mkdir(parents=True, exist_ok=True)
        self._settings_store.save(settings)
        self._last_output_dir = str(output_path.resolve())
        return settings, output_path

    @staticmethod
    def _request_for_url(url: str, settings: AppSettings, output_path: Path) -> DownloadRequest:
        return DownloadRequest(
            url=url,
            output_dir=output_path,
            preset_key=settings.preset_key,
            cookie_browser=settings.cookie_browser or None,
            referer=settings.referer or None,
            user_agent=settings.user_agent or None,
            allow_playlist=settings.allow_playlist,
            write_subtitles=settings.write_subtitles,
            write_auto_subtitles=settings.write_auto_subtitles,
            use_archive=settings.use_archive,
        )

    def _refresh_dependency_badges(self) -> None:
        status = dependency_status()
        self.ytdlp_badge.setText(f"yt-dlp {status.yt_dlp_version}")
        self.ytdlp_badge.setObjectName("StatusGood" if status.yt_dlp_version != "未安装" else "StatusWarn")
        ffmpeg_text = f"FFmpeg {status.ffmpeg_source}" if status.ffmpeg_available else "FFmpeg 不可用"
        self.ffmpeg_badge.setText(ffmpeg_text)
        self.ffmpeg_badge.setObjectName("StatusGood" if status.ffmpeg_available else "StatusWarn")
        self.ytdlp_badge.style().unpolish(self.ytdlp_badge)
        self.ytdlp_badge.style().polish(self.ytdlp_badge)
        self.ffmpeg_badge.style().unpolish(self.ffmpeg_badge)
        self.ffmpeg_badge.style().polish(self.ffmpeg_badge)
        self._refresh_model_badge()

    def _choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择视频保存目录", self.output_input.text())
        if directory:
            self.output_input.setText(directory)

    def _open_output_dir(self) -> None:
        directory = Path(self.output_input.text().strip() or self._last_output_dir).expanduser()
        directory.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory.resolve())))

    def _on_url_changed(self) -> None:
        current = self.url_input.toPlainText().strip()
        if current != self._input_snapshot and self._operation is None:
            self._batch_items.clear()
            self._result_rows.clear()
            self._show_results_placeholder()
            self.media_title.setText("等待批量分析")
            self.media_meta.setText("每行输入一个地址，分析结果将在下载队列中逐项显示")
            self._set_state("idle")

    def _show_results_placeholder(self) -> None:
        self.results_list.clear()
        placeholder = QListWidgetItem("分析后，每个地址的结果会显示在这里")
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        placeholder.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setSizeHint(QSize(0, 62))
        self.results_list.addItem(placeholder)

    def _populate_result_rows(self) -> None:
        self.results_list.clear()
        self._result_rows.clear()
        for index, item in enumerate(self._batch_items):
            list_item = QListWidgetItem()
            list_item.setSizeHint(QSize(0, 61))
            row = BatchResultRow(index, item.url)
            row.download_requested.connect(self.start_item_download)
            self.results_list.addItem(list_item)
            self.results_list.setItemWidget(list_item, row)
            self._result_rows[index] = row

    def _refresh_batch_summary(self) -> None:
        total = len(self._batch_items)
        success = sum(item.is_downloadable for item in self._batch_items)
        failed = sum(item.status == "analysis_failed" for item in self._batch_items)
        complete = success + failed
        if not total:
            self.media_title.setText("等待批量分析")
            self.media_meta.setText("每行输入一个地址，分析结果将在下载队列中逐项显示")
        elif self._operation == "analysis":
            self.media_title.setText(f"正在分析 {complete}/{total}")
            self.media_meta.setText(f"成功 {success} 项 · 失败 {failed} 项 · 其余正在排队")
        else:
            self.media_title.setText(f"已分析 {total} 个地址")
            self.media_meta.setText(f"成功 {success} 项 · 失败 {failed} 项 · 批量下载仅处理成功项目")

    def _clear_log(self) -> None:
        self.log_output.clear()

    def _append_log(self, level: str, message: str) -> None:
        labels = {"error": "错误", "warning": "警告", "info": "信息"}
        timestamp = datetime.now().strftime("%H:%M:%S")
        cleaned = " ".join(str(message).splitlines()).strip()
        if cleaned:
            self.log_output.appendPlainText(f"[{timestamp}] {labels.get(level, '信息')}  {cleaned}")

    def _show_error(self, title: str, detail: str) -> None:
        self.toast.show_message(title, detail, "error", 6)
        self._append_log("error", f"{title}：{detail}")

    def _set_state(self, state: str) -> None:
        active = state in {"analyzing", "downloading", "cancelling"}
        successful = sum(item.is_downloadable for item in self._batch_items)
        self.analyze_button.setEnabled(not active)
        self.batch_download_button.setEnabled(not active and successful > 0)
        self.cancel_button.setVisible(active)
        self.url_input.setEnabled(not active)
        self.preset_combo.setEnabled(not active)
        self.browser_combo.setEnabled(not active)
        self.output_input.setEnabled(not active)
        self.referer_input.setEnabled(not active)
        self.user_agent_input.setEnabled(not active)
        for checkbox in (
            self.playlist_check,
            self.subtitle_check,
            self.auto_subtitle_check,
            self.archive_check,
        ):
            checkbox.setEnabled(not active)
        for row in self._result_rows.values():
            row.set_action_enabled(not active)
        self.brand_logo.set_active(active)

        if state == "idle":
            self.task_status.setText("等待分析")
            self._set_progress_value(0.0)
        elif state == "analyzing":
            self.task_status.setText(f"正在分析 0/{len(self._batch_items)}")
            self._set_indeterminate_progress("分析中")
        elif state == "ready":
            self.task_status.setText(f"可下载 {successful} 项" if successful else "没有可下载项目")
            self._set_progress_value(0.0)
        elif state == "downloading":
            self.task_status.setText(f"准备下载 {len(self._download_indices)} 项")
        elif state == "cancelling":
            self.task_status.setText("正在取消")
        elif state == "finished":
            self.task_status.setText(
                f"完成 {self._download_success_count} 项 · 失败 {self._download_failure_count} 项"
            )

    def _set_indeterminate_progress(self, text: str = "") -> None:
        self.progress_bar.setRange(0, 0)
        self.progress_label.setText(text)
        self.speed_label.clear()
        self.eta_label.clear()

    def _set_progress_value(self, percent: float) -> None:
        value = max(0.0, min(100.0, percent))
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(round(value * 10))
        self.progress_label.setText(f"{value:.1f}%")

    def _start_worker(self, worker: BatchWorkerBase, operation: str) -> None:
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.item_progress.connect(self._on_item_progress)
        worker.log.connect(self._append_log)
        worker.cancelled.connect(self._on_cancelled)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_thread_finished)

        self._thread = thread
        self._worker = worker
        self._operation = operation
        self._operation_cancelled = False
        self._set_state("analyzing" if operation == "analysis" else "downloading")
        thread.start()

    def start_analysis(self) -> None:
        if self._operation:
            return
        urls = parse_url_lines(self.url_input.toPlainText())
        if not urls:
            self._show_error("没有视频地址", "请每行输入一个完整的 http:// 或 https:// 地址。")
            return
        try:
            settings, output_path = self._prepare_request_context()
        except (ValueError, OSError) as error:
            self._show_error("无法开始分析", str(error))
            return

        self._input_snapshot = self.url_input.toPlainText().strip()
        self._batch_items = [BatchMediaItem(url=url) for url in urls]
        self._populate_result_rows()
        jobs: list[tuple[int, DownloadRequest]] = []
        for index, item in enumerate(self._batch_items):
            try:
                valid_url = validate_http_url(item.url)
            except ValueError as error:
                item.status = "analysis_failed"
                item.error_title = "地址无效"
                item.error_detail = str(error)
                self._result_rows[index].set_failed(item.error_title, item.error_detail)
                continue
            jobs.append((index, self._request_for_url(valid_url, settings, output_path)))

        self._refresh_batch_summary()
        if not jobs:
            self._show_error("没有可分析地址", "输入内容中没有有效的 http:// 或 https:// 地址。")
            self._set_state("ready")
            return

        self.toast.show_message("正在批量分析", f"共 {len(jobs)} 个有效地址，正在逐项识别", "info", 5)
        self._append_log("info", f"开始批量分析，共 {len(jobs)} 个有效地址")
        worker = BatchAnalyzeWorker(jobs)
        worker.item_started.connect(self._on_analysis_started)
        worker.item_analyzed.connect(self._on_analyzed)
        worker.item_failed.connect(self._on_analysis_failed)
        self._start_worker(worker, "analysis")

    def _on_analysis_started(self, index: int, url: str) -> None:
        self._batch_items[index].status = "analyzing"
        self._result_rows[index].set_analyzing()
        position = sum(item.status in {"analysis_ready", "analysis_failed"} for item in self._batch_items)
        self.task_status.setText(f"正在分析 {position + 1}/{len(self._batch_items)}")

    def _on_analyzed(self, index: int, url: str, summary: MediaSummary) -> None:
        item = self._batch_items[index]
        item.status = "analysis_ready"
        item.summary = summary
        item.error_title = ""
        item.error_detail = ""
        self._result_rows[index].set_success(summary)
        self._append_log("info", f"分析完成：{summary.title}")
        self._refresh_batch_summary()

    def _on_analysis_failed(self, index: int, url: str, title: str, detail: str) -> None:
        item = self._batch_items[index]
        item.status = "analysis_failed"
        item.error_title = title
        item.error_detail = detail
        self._result_rows[index].set_failed(title, detail)
        self._append_log("error", f"分析失败：{url} · {title}：{detail}")
        self._refresh_batch_summary()

    def start_download(self) -> None:
        self.start_batch_download()

    def start_batch_download(self) -> None:
        indices = [index for index, item in enumerate(self._batch_items) if item.is_downloadable]
        self._start_download_indices(indices)

    def start_item_download(self, index: int) -> None:
        self._start_download_indices([index])

    def _start_download_indices(self, indices: list[int]) -> None:
        if self._operation:
            return
        indices = [index for index in indices if 0 <= index < len(self._batch_items)]
        indices = [index for index in indices if self._batch_items[index].is_downloadable]
        if not indices:
            self._show_error("没有可下载项目", "只有分析成功的视频才能开始下载。")
            return
        try:
            settings, output_path = self._prepare_request_context()
        except (ValueError, OSError) as error:
            self._show_error("无法开始下载", str(error))
            return

        jobs = [
            (index, self._request_for_url(self._batch_items[index].url, settings, output_path))
            for index in indices
        ]
        self._download_indices = indices
        self._download_position = 0
        self._download_success_count = 0
        self._download_failure_count = 0
        for index in indices:
            self._batch_items[index].status = "download_queued"
            self._result_rows[index].set_queued()
        self._append_log("info", f"开始下载，共 {len(indices)} 个分析成功项目")
        worker = BatchDownloadWorker(jobs)
        worker.item_started.connect(self._on_download_started)
        worker.item_downloaded.connect(self._on_downloaded)
        worker.item_failed.connect(self._on_download_failed)
        self._start_worker(worker, "download")

    def cancel_operation(self) -> None:
        if not self._worker:
            return
        self._set_state("cancelling")
        self._append_log("warning", "用户请求取消当前任务")
        self._worker.cancel()

    def _on_download_started(self, index: int, url: str) -> None:
        self._download_position = self._download_indices.index(index)
        self._batch_items[index].status = "downloading"
        self._result_rows[index].set_downloading()
        self.task_status.setText(
            f"正在下载 {self._download_position + 1}/{len(self._download_indices)}"
        )

    def _on_item_progress(self, index: int, update: ProgressUpdate) -> None:
        if self._operation == "analysis":
            self._set_indeterminate_progress("分析中")
            return
        total = max(1, len(self._download_indices))
        item_percent = update.percent if update.percent is not None else 0.0
        if update.stage in {"processing", "finished"}:
            item_percent = 100.0
        overall = (self._download_position + item_percent / 100.0) * 100.0 / total
        self._set_progress_value(overall)
        self.speed_label.setText(update.speed)
        self.eta_label.setText(f"剩余 {update.eta}" if update.eta else "")

    def _on_downloaded(self, index: int, url: str, output_dir: str) -> None:
        self._last_output_dir = output_dir
        self._batch_items[index].status = "downloaded"
        self._result_rows[index].set_completed()
        self._download_success_count += 1
        self._append_log("info", f"下载完成：{self._batch_items[index].summary.title}")

    def _on_download_failed(self, index: int, url: str, title: str, detail: str) -> None:
        self._batch_items[index].status = "download_failed"
        self._result_rows[index].set_download_failed(f"{title}：{detail}")
        self._download_failure_count += 1
        self._append_log("error", f"下载失败：{url} · {title}：{detail}")

    def _on_cancelled(self) -> None:
        self._operation_cancelled = True
        self._append_log("warning", "任务已取消")

    def _on_thread_finished(self) -> None:
        operation = self._operation
        self._thread = None
        self._worker = None
        self._operation = None

        if operation == "analysis":
            for index, item in enumerate(self._batch_items):
                if item.status in {"pending", "analyzing"}:
                    item.status = "analysis_failed"
                    item.error_title = "未完成"
                    item.error_detail = "批量分析已取消"
                    self._result_rows[index].set_failed(item.error_title, item.error_detail)
            self._refresh_batch_summary()
            success = sum(item.is_downloadable for item in self._batch_items)
            failed = sum(item.status == "analysis_failed" for item in self._batch_items)
            if self._operation_cancelled:
                self.toast.show_message("分析已取消", f"成功 {success} 项，未成功 {failed} 项", "warning", 5)
            else:
                kind = "success" if success else "error"
                self.toast.show_message("批量分析完成", f"成功 {success} 项，失败 {failed} 项", kind, 5)
            self._set_state("ready")
        elif operation == "download":
            for index in self._download_indices:
                item = self._batch_items[index]
                if item.status in {"download_queued", "downloading"} and item.summary:
                    item.status = "analysis_ready"
                    self._result_rows[index].set_success(item.summary)
            if self._operation_cancelled:
                self.toast.show_message(
                    "下载已取消",
                    f"已完成 {self._download_success_count} 项",
                    "warning",
                    5,
                )
                self._set_state("ready")
            else:
                self._set_progress_value(100.0)
                self.toast.show_message(
                    "批量下载完成",
                    f"成功 {self._download_success_count} 项，失败 {self._download_failure_count} 项",
                    "success" if self._download_failure_count == 0 else "warning",
                    5,
                )
                self._set_state("finished")
        else:
            self._set_state("ready" if self._batch_items else "idle")
        if self._pending_close:
            QTimer.singleShot(0, self.close)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._settings_store.save(self._collect_settings())
        editor_active = self.editor_workbench.has_running_task
        if self._operation or editor_active:
            if self._pending_close:
                event.ignore()
                return
            answer = QMessageBox.question(
                self,
                "任务仍在运行",
                "关闭窗口将取消正在运行的下载、分析或导出任务，确定继续吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._pending_close = True
            if self._worker:
                self._worker.cancel()
            if self._operation:
                self._set_state("cancelling")
            if editor_active:
                self.editor_workbench.cancel_active_task()
            event.ignore()
            return
        if self.editor_workbench.dirty:
            answer = QMessageBox.warning(
                self,
                "剪辑项目尚未保存",
                "剪辑工作台中有未保存的修改。",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.StandardButton.Save:
                self.editor_workbench.save_project()
                if self.editor_workbench.dirty:
                    event.ignore()
                    return
        self.editor_workbench.player.stop()
        event.accept()
