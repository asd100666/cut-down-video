from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, QSizeF, QThread, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QCursor, QDesktopServices
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsOpacityEffect,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .editor_models import EditProject, MediaAsset, SnapshotHistory, format_timecode, new_id
from .editor_workers import (
    EditorExportWorker,
    LongVideoHighlightWorker,
    MediaProbeWorker,
    NarrationDraftWorker,
    NarrationWorker,
    SceneSplitWorker,
    SpeechRecognitionWorker,
)
from .icons import svg_icon
from .model_manager import ModelManager
from .narration_engine import build_narration_draft
from .timeline_widget import MultiTrackTimelineWidget


VIDEO_FILTER = "视频文件 (*.mp4 *.mov *.mkv *.webm *.avi *.m4v *.ts *.mts *.m2ts);;所有文件 (*.*)"
AUDIO_FILTER = "音频文件 (*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus *.wma);;所有文件 (*.*)"
PROJECT_FILTER = "流光剪辑项目 (*.slproj);;JSON 文件 (*.json)"
TIMELINE_PANEL_MIN_HEIGHT = 290
TIMELINE_PANEL_MAX_HEIGHT = 370


class HighlightDialog(QDialog):
    def __init__(
        self,
        video_assets: list[MediaAsset],
        selected_asset_id: str | None = None,
        model_manager: ModelManager | None = None,
        manage_models_callback: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("生成长视频精华")
        self.setModal(True)
        self.setMinimumWidth(470)
        self.model_manager = model_manager or ModelManager()
        self.manage_models_callback = manage_models_callback
        layout = QVBoxLayout(self)
        intro = QLabel(
            "系统会离线检测场景切换并按目标时长覆盖整段素材。生成结果会进入当前分镜时间线，仍可继续人工切分、改入出点、重排和删除。"
        )
        intro.setObjectName("HighlightIntro")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        self.source_combo = QComboBox()
        all_ids = [asset.id for asset in video_assets]
        if len(video_assets) > 1:
            self.source_combo.addItem(f"全部视频素材（{len(video_assets)} 个，合并精华）", all_ids)
        for asset in video_assets:
            self.source_combo.addItem(
                f"{asset.name} · {format_timecode(asset.duration)}",
                [asset.id],
            )
        if selected_asset_id:
            for index in range(self.source_combo.count()):
                if self.source_combo.itemData(index) == [selected_asset_id]:
                    self.source_combo.setCurrentIndex(index)
                    break

        total_duration = max(1, round(sum(asset.duration for asset in video_assets)))
        self.target_spin = QSpinBox()
        self.target_spin.setRange(1, min(7200, total_duration))
        self.target_spin.setValue(min(60, self.target_spin.maximum()))
        self.target_spin.setSuffix(" 秒")
        self.max_clip_spin = QDoubleSpinBox()
        self.max_clip_spin.setRange(0.5, 30.0)
        self.max_clip_spin.setValue(5.0)
        self.max_clip_spin.setSingleStep(0.5)
        self.max_clip_spin.setSuffix(" 秒")
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.05, 0.95)
        self.threshold_spin.setValue(0.32)
        self.threshold_spin.setSingleStep(0.05)
        self.threshold_spin.setDecimals(2)
        self.replace_check = QCheckBox("替换当前分镜时间线（可撤销）")
        self.replace_check.setChecked(True)
        form.addRow("素材范围", self.source_combo)
        form.addRow("目标总时长", self.target_spin)
        form.addRow("单镜头最长", self.max_clip_spin)
        form.addRow("场景灵敏度", self.threshold_spin)
        form.addRow("", self.replace_check)
        layout.addLayout(form)

        intelligence = QFrame(objectName="IntelligencePanel")
        intelligence_layout = QVBoxLayout(intelligence)
        intelligence_layout.setContentsMargins(10, 8, 10, 8)
        intelligence_layout.setSpacing(5)
        intelligence_header = QHBoxLayout()
        intelligence_header.addWidget(QLabel("本地智能增强", objectName="SubsectionTitle"))
        intelligence_header.addStretch(1)
        self.manage_models_button = QPushButton("管理模型")
        self.manage_models_button.setIcon(svg_icon("sparkles"))
        self.manage_models_button.clicked.connect(self._manage_models)
        intelligence_header.addWidget(self.manage_models_button)
        intelligence_layout.addLayout(intelligence_header)
        self.speech_check = QCheckBox()
        self.face_check = QCheckBox()
        self.semantic_check = QCheckBox()
        intelligence_layout.addWidget(self.speech_check)
        intelligence_layout.addWidget(self.face_check)
        intelligence_layout.addWidget(self.semantic_check)
        layout.addWidget(intelligence)
        self._refresh_model_capabilities()

        hint = QLabel("灵敏度越低会识别更多场景；固定镜头较多的素材会自动使用均匀时间覆盖作为后备。")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("开始分析")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def configuration(self) -> tuple[list[str], dict]:
        return list(self.source_combo.currentData() or []), {
            "target_duration": float(self.target_spin.value()),
            "max_clip_duration": float(self.max_clip_spin.value()),
            "scene_threshold": float(self.threshold_spin.value()),
            "replace_timeline": self.replace_check.isChecked(),
            "speech_enabled": self.speech_check.isChecked(),
            "face_enabled": self.face_check.isChecked(),
            "semantic_enabled": self.semantic_check.isChecked(),
        }

    def _manage_models(self) -> None:
        if self.manage_models_callback:
            self.manage_models_callback()
        self._refresh_model_capabilities()

    def _refresh_model_capabilities(self) -> None:
        rows = (
            (self.speech_check, "speech", "语音识别与自动字幕"),
            (self.face_check, "face_subject", "人脸与人物主体检测"),
            (self.semantic_check, "semantic", "语义理解与智能编排"),
        )
        for checkbox, capability, label in rows:
            missing = self.model_manager.capability_missing(capability)
            ready = not missing
            checkbox.setEnabled(ready)
            if not ready:
                checkbox.setChecked(False)
            checkbox.setText(label if ready else f"{label}（缺少 {len(missing)} 个模型）")
            checkbox.setToolTip(
                "模型已就绪" if ready else "请先安装：\n" + "\n".join(spec.name for spec in missing)
            )


class SceneSplitDialog(QDialog):
    def __init__(self, clip_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("智能分镜")
        self.setModal(True)
        self.setMinimumWidth(390)
        layout = QVBoxLayout(self)
        intro = QLabel(f"对“{clip_name}”执行离线场景检测。结果会替换当前镜头，但仍可拖动、删除和撤销。")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0.05, 0.95)
        self.threshold.setDecimals(2)
        self.threshold.setSingleStep(0.05)
        self.threshold.setValue(0.35)
        self.minimum_duration = QDoubleSpinBox()
        self.minimum_duration.setRange(0.2, 30.0)
        self.minimum_duration.setDecimals(1)
        self.minimum_duration.setValue(1.0)
        form.addRow("场景灵敏度", self.threshold)
        form.addRow("最短镜头（秒）", self.minimum_duration)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("开始分镜")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class NarrationRecipeDialog(QDialog):
    def __init__(
        self,
        model_manager: ModelManager,
        manage_models_callback: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.model_manager = model_manager
        self.manage_models_callback = manage_models_callback
        self.setWindowTitle("智能解说参数")
        self.setModal(True)
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        intro = QLabel(
            "先根据字幕和镜头事实生成可编辑草稿，再使用 Windows 本机语音生成配音。"
            "Qwen 与 llama.cpp 都安装后可执行真实本地生成。"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.style_combo = QComboBox()
        self.style_combo.addItem("精华概述", "summary")
        self.style_combo.addItem("剧情解说", "story")
        self.style_combo.addItem("知识总结", "knowledge")
        self.max_chars = QSpinBox()
        self.max_chars.setRange(80, 1200)
        self.max_chars.setSingleStep(20)
        self.max_chars.setValue(420)
        self.max_chars.setSuffix(" 字")
        form.addRow("解说风格", self.style_combo)
        form.addRow("草稿长度", self.max_chars)
        layout.addLayout(form)
        model_row = QHBoxLayout()
        self.use_model = QCheckBox("使用本地 Qwen2.5 3B 生成")
        model_row.addWidget(self.use_model)
        self.model_status = QLabel(objectName="Muted")
        self.model_status.setFixedHeight(38)
        self.model_status.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        model_row.addWidget(self.model_status, 1)
        self.manage_button = QPushButton("管理模型")
        self.manage_button.setFixedHeight(38)
        self.manage_button.clicked.connect(self._manage_models)
        model_row.addWidget(self.manage_button)
        layout.addLayout(model_row)
        note = QLabel("CPU 首次加载约需数秒；模型不可用时仍可生成确定性草稿，并保留人工修改。")
        note.setObjectName("Hint")
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("生成可编辑草稿")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName("PrimaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._refresh_model_state()

    def _manage_models(self) -> None:
        if self.manage_models_callback:
            self.manage_models_callback()
        self._refresh_model_state()

    def _refresh_model_state(self) -> None:
        ready = self.model_manager.capability_ready("narration")
        missing = self.model_manager.capability_missing("narration")
        self.use_model.setEnabled(ready)
        self.use_model.setChecked(ready)
        self.model_status.setText("模型与运行时已就绪" if ready else f"缺少 {len(missing)} 项，当前使用规则草稿")

    def configuration(self) -> dict:
        return {
            "style": str(self.style_combo.currentData() or "summary"),
            "max_chars": int(self.max_chars.value()),
            "use_model": bool(self.use_model.isChecked() and self.use_model.isEnabled()),
        }


class NarrationDialog(QDialog):
    def __init__(
        self,
        project: EditProject,
        initial_text: str,
        source_label: str,
        style: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("一键添加解说")
        self.setModal(True)
        self.setMinimumSize(560, 430)
        layout = QVBoxLayout(self)
        intro = QLabel(
            f"草稿来源：{source_label}。请先检查和修改文字，再使用 Windows 本机离线语音生成配音并加入音频轨。"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        style_names = {"summary": "精华概述", "story": "剧情解说", "knowledge": "知识总结"}
        self.start_spin = QDoubleSpinBox()
        self.start_spin.setRange(0.0, max(24 * 3600.0, project.duration))
        self.start_spin.setDecimals(2)
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(-10, 10)
        self.rate_spin.setValue(0)
        self.volume_spin = QDoubleSpinBox()
        self.volume_spin.setRange(0.0, 2.0)
        self.volume_spin.setDecimals(2)
        self.volume_spin.setValue(0.9)
        form.addRow("解说风格", QLabel(style_names.get(style, "精华概述")))
        form.addRow("时间线开始", self.start_spin)
        form.addRow("语速", self.rate_spin)
        form.addRow("音量", self.volume_spin)
        layout.addLayout(form)
        self.script_edit = QPlainTextEdit()
        self.script_edit.setPlaceholderText("在这里修改解说文字")
        self.script_edit.setPlainText(initial_text)
        layout.addWidget(self.script_edit, 1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("生成配音并加入音轨")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName("PrimaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def configuration(self) -> dict:
        return {
            "text": self.script_edit.toPlainText().strip(),
            "start_time": float(self.start_spin.value()),
            "rate": int(self.rate_spin.value()),
            "volume": float(self.volume_spin.value()),
        }


class VideoCanvas(QGraphicsView):
    def __init__(self, parent: QWidget | None = None) -> None:
        self.scene = QGraphicsScene()
        super().__init__(self.scene, parent)
        self.setObjectName("VideoPreview")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_item = QGraphicsVideoItem()
        self.video_item.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.scene.addItem(self.video_item)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        size = QSizeF(max(1, self.viewport().width()), max(1, self.viewport().height()))
        self.scene.setSceneRect(0, 0, size.width(), size.height())
        self.video_item.setSize(size)


class VideoPreviewSurface(QFrame):
    """Composited video canvas with native-style hover controls."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, objectName="VideoSurface")
        self.setMinimumHeight(280)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.video_widget = VideoCanvas(self)
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.player_controls = QFrame(self, objectName="PlayerControls")
        self.player_controls.setFixedHeight(68)
        self._playing = False
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(1500)
        self._hide_timer.timeout.connect(self._hide_controls)
        self._opacity = QGraphicsOpacityEffect(self.player_controls)
        self.player_controls.setGraphicsEffect(self._opacity)
        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setDuration(180)
        self._fade.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade.finished.connect(self._on_fade_finished)
        self._fade_hiding = False
        self._leave_hide_requested = False
        for target in (self, self.video_widget, self.video_widget.viewport(), self.player_controls):
            target.setMouseTracking(True)
            target.installEventFilter(self)

    @property
    def video_item(self) -> QGraphicsVideoItem:
        return self.video_widget.video_item

    def install_control_event_filters(self) -> None:
        for child in self.player_controls.findChildren(QWidget):
            child.setMouseTracking(True)
            child.installEventFilter(self)

    def set_playing(self, playing: bool) -> None:
        self._playing = playing
        self.show_controls(auto_hide=playing)

    def show_controls(self, *, auto_hide: bool = True) -> None:
        self._fade.stop()
        self._fade_hiding = False
        self._leave_hide_requested = False
        self.player_controls.show()
        self.player_controls.raise_()
        self._opacity.setOpacity(1.0)
        if auto_hide and self._playing:
            self._hide_timer.start()
        else:
            self._hide_timer.stop()

    def _hide_controls(self) -> None:
        pointer_inside = self.rect().contains(self.mapFromGlobal(QCursor.pos()))
        if pointer_inside or self.player_controls.underMouse():
            return
        if any(child.hasFocus() for child in self.player_controls.findChildren(QWidget)):
            return
        if not self._playing and not self._leave_hide_requested:
            return
        self._fade.stop()
        self._fade_hiding = True
        self._fade.setStartValue(self._opacity.opacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    def _on_fade_finished(self) -> None:
        if self._fade_hiding:
            self.player_controls.hide()

    def eventFilter(self, watched, event) -> bool:
        if event.type() in {
            QEvent.Type.Enter,
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.FocusIn,
        }:
            self.show_controls(auto_hide=self._playing)
        elif event.type() == QEvent.Type.Leave:
            self._leave_hide_requested = True
            self._hide_timer.start(350)
        return super().eventFilter(watched, event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.video_widget.setGeometry(self.rect())
        margin = 10
        height = self.player_controls.height()
        self.player_controls.setGeometry(
            margin,
            max(margin, self.height() - height - margin),
            max(0, self.width() - margin * 2),
            height,
        )
        self.player_controls.raise_()


class EditorWorkbench(QWidget):
    busy_changed = Signal(bool)

    def __init__(
        self,
        model_manager: ModelManager | None = None,
        manage_models_callback: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, objectName="EditorWorkbench")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.model_manager = model_manager or ModelManager()
        self.manage_models_callback = manage_models_callback
        self.project = EditProject()
        self.history = SnapshotHistory()
        self.project_path: Path | None = None
        self.dirty = False
        self._updating_ui = False
        self._thread: QThread | None = None
        self._worker: (
            MediaProbeWorker
            | EditorExportWorker
            | LongVideoHighlightWorker
            | NarrationDraftWorker
            | NarrationWorker
            | SceneSplitWorker
            | SpeechRecognitionWorker
            | None
        ) = None
        self._operation: str | None = None
        self._probe_intent = "video"
        self._preview_clip_index = -1
        self._selected_subtitle = -1
        self._scene_split_clip_index = -1
        self._pending_preview_position: int | None = None
        self._preview_autoplay = False
        self._preview_source_name = ""
        self._last_export: Path | None = None
        self._fullscreen_dialog: QDialog | None = None
        self._pending_narration_recipe: dict = {}
        self._pending_narration_review: tuple[str, dict, dict] | None = None
        self._pending_narration_metadata: dict = {}

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.75)
        self.player.setAudioOutput(self.audio_output)

        self._build_ui()
        self._connect_player()
        self._refresh_all()

    @property
    def has_running_task(self) -> bool:
        return self._operation is not None

    def _panel(self, title: str, hint: str = "") -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame(objectName="EditorPanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 11, 12, 11)
        layout.setSpacing(8)
        header = QHBoxLayout()
        header.addWidget(QLabel(title, objectName="EditorPanelTitle"))
        if hint:
            header.addWidget(QLabel(hint, objectName="Hint"), 1)
        else:
            header.addStretch(1)
        layout.addLayout(header)
        return frame, layout

    def _button(self, text: str, icon: str, *, primary: bool = False) -> QPushButton:
        button = QPushButton(text)
        button.setIcon(svg_icon(icon))
        if primary:
            button.setObjectName("PrimaryButton")
        return button

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        toolbar = QFrame(objectName="EditorToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(12, 8, 12, 8)
        toolbar_layout.setSpacing(7)
        self.new_button = self._button("新建", "file")
        self.open_button = self._button("打开", "folder-open")
        self.save_button = self._button("保存", "save")
        self.undo_button = self._button("撤销", "undo")
        self.redo_button = self._button("重做", "redo")
        self.import_video_button = self._button("导入镜头", "import")
        self.import_audio_button = self._button("添加音轨", "music")
        self.auto_highlight_button = self._button("自动精华", "sparkles")
        self.narration_button = self._button("智能解说", "music")
        self.export_button = self._button("导出成片", "export", primary=True)
        for button in (
            self.new_button,
            self.open_button,
            self.save_button,
            self.undo_button,
            self.redo_button,
            self.import_video_button,
            self.import_audio_button,
            self.auto_highlight_button,
            self.narration_button,
        ):
            toolbar_layout.addWidget(button)
        toolbar_layout.addStretch(1)
        self.project_title = QLabel(objectName="EditorProjectTitle")
        toolbar_layout.addWidget(self.project_title)
        toolbar_layout.addWidget(self.export_button)
        root.addWidget(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("EditorSplitter")
        splitter.setChildrenCollapsible(False)
        splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        library_panel, library_layout = self._panel("素材库", "双击视频可再次加入时间线")
        self.asset_list = QListWidget(objectName="AssetList")
        self.asset_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        library_layout.addWidget(self.asset_list, 1)
        asset_actions = QHBoxLayout()
        self.asset_to_timeline_button = self._button("加入时间线", "plus")
        self.asset_preview_button = self._button("预览", "play")
        asset_actions.addWidget(self.asset_to_timeline_button)
        asset_actions.addWidget(self.asset_preview_button)
        library_layout.addLayout(asset_actions)
        splitter.addWidget(library_panel)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(10)

        preview_panel, preview_layout = self._panel("预览", "选择镜头后可在源素材上精确定位")
        self.preview_panel = preview_panel
        self.preview_layout = preview_layout
        self.preview_surface = VideoPreviewSurface()
        self.video_widget = self.preview_surface.video_widget
        self.player_controls = self.preview_surface.player_controls
        self.player.setVideoOutput(self.preview_surface.video_item)
        playback = QVBoxLayout(self.player_controls)
        playback.setContentsMargins(8, 6, 8, 5)
        playback.setSpacing(2)
        playback_top = QHBoxLayout()
        playback_top.setSpacing(7)
        self.play_button = self._button("播放", "play")
        self.position_label = QLabel("00:00.000 / 00:00.000", objectName="PreviewTime")
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setObjectName("PlayerPosition")
        self.position_slider.setRange(0, 0)
        self.playback_rate_combo = QComboBox(objectName="PlaybackRate")
        for label, rate in (("0.5×", 0.5), ("0.75×", 0.75), ("1.0×", 1.0), ("1.25×", 1.25), ("1.5×", 1.5), ("2.0×", 2.0)):
            self.playback_rate_combo.addItem(label, rate)
        self.playback_rate_combo.setCurrentIndex(2)
        self.playback_rate_combo.setToolTip("播放速度")
        self.playback_rate_combo.setFixedWidth(72)
        self.volume_button = self._button("", "volume")
        self.volume_button.setToolTip("静音 / 恢复声音")
        self.volume_button.setFixedWidth(36)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal, objectName="PlayerVolume")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(75)
        self.volume_slider.setToolTip("预览音量")
        self.fullscreen_button = self._button("全屏", "fullscreen")
        playback_top.addWidget(self.play_button)
        playback_top.addWidget(self.position_label)
        playback_top.addStretch(1)
        playback_top.addWidget(self.playback_rate_combo)
        playback_top.addWidget(self.volume_button)
        playback_top.addWidget(self.volume_slider)
        playback_top.addWidget(self.fullscreen_button)
        playback.addLayout(playback_top)
        playback.addWidget(self.position_slider)
        self.preview_surface.install_control_event_filters()
        self.player_controls.hide()
        preview_layout.addWidget(self.preview_surface, 1)
        center_layout.addWidget(preview_panel, 1)

        timeline_panel, timeline_layout = self._panel("分镜时间线", "自动结果和人工修改共用此时间线")
        self.timeline_panel = timeline_panel
        self.timeline_panel.setMinimumHeight(TIMELINE_PANEL_MIN_HEIGHT)
        self.timeline_panel.setMaximumHeight(TIMELINE_PANEL_MAX_HEIGHT)
        self.timeline_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.timeline_view = MultiTrackTimelineWidget()
        timeline_layout.addWidget(self.timeline_view, 1)
        self.timeline_table = QTableWidget(0, 7, objectName="TimelineTable")
        self.timeline_table.setHorizontalHeaderLabels(["#", "镜头", "入点", "出点", "时长", "依据", "原声音量"])
        self.timeline_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.timeline_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.timeline_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.timeline_table.verticalHeader().setVisible(False)
        self.timeline_table.horizontalHeader().setStretchLastSection(True)
        self.timeline_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.timeline_table.hide()
        timeline_actions = QHBoxLayout()
        self.split_button = self._button("播放头切分", "scissors")
        self.duplicate_button = self._button("复制", "copy")
        self.move_up_button = self._button("前移", "up")
        self.move_down_button = self._button("后移", "down")
        self.delete_clip_button = self._button("删除镜头", "trash")
        self.delete_clip_button.setObjectName("DangerButton")
        for button in (
            self.split_button,
            self.duplicate_button,
            self.move_up_button,
            self.move_down_button,
            self.delete_clip_button,
        ):
            timeline_actions.addWidget(button)
        timeline_actions.addStretch(1)
        self.timeline_duration = QLabel(objectName="TimelineDuration")
        timeline_actions.addWidget(self.timeline_duration)
        timeline_layout.addLayout(timeline_actions)
        timeline_intelligence = QHBoxLayout()
        self.smart_split_button = self._button("智能分镜", "scissors")
        self.recognize_subtitles_button = self._button("识别字幕", "sparkles")
        timeline_intelligence.addWidget(self.smart_split_button)
        timeline_intelligence.addWidget(self.recognize_subtitles_button)
        timeline_intelligence.addStretch(1)
        timeline_layout.addLayout(timeline_intelligence)
        center_layout.addWidget(timeline_panel, 0)
        splitter.addWidget(center)

        inspector = QTabWidget(objectName="InspectorTabs")
        self.inspector_tabs = inspector

        clip_panel, clip_layout = self._panel("镜头属性", "精确修改后仍可继续重排")
        clip_form = QFormLayout()
        self.clip_name = QLineEdit()
        self.clip_name.setReadOnly(True)
        self.clip_in = self._time_spin()
        self.clip_out = self._time_spin()
        self.clip_volume = self._volume_spin()
        self.clip_muted = QCheckBox("静音原声")
        self.clip_reason = QLineEdit()
        self.clip_reason.setReadOnly(True)
        self.clip_evidence = QLineEdit()
        self.clip_evidence.setReadOnly(True)
        self.clip_transition = QComboBox()
        self.clip_transition.addItem("直接切换", "cut")
        self.clip_transition.addItem("淡入淡出", "fade")
        self.clip_transition.addItem("交叉溶解", "dissolve")
        self.clip_transition_duration = QDoubleSpinBox()
        self.clip_transition_duration.setRange(0.1, 2.0)
        self.clip_transition_duration.setDecimals(2)
        self.clip_transition_duration.setSingleStep(0.1)
        self.clip_transition_duration.setValue(0.5)
        clip_form.addRow("镜头", self.clip_name)
        clip_form.addRow("入点（秒）", self.clip_in)
        clip_form.addRow("出点（秒）", self.clip_out)
        clip_form.addRow("音量", self.clip_volume)
        clip_form.addRow("自动选择依据", self.clip_reason)
        clip_form.addRow("关联证据", self.clip_evidence)
        clip_form.addRow("入场转场", self.clip_transition)
        clip_form.addRow("转场时长（秒）", self.clip_transition_duration)
        clip_form.addRow("", self.clip_muted)
        clip_layout.addLayout(clip_form)
        self.apply_clip_button = self._button("应用镜头修改", "check", primary=True)
        clip_layout.addWidget(self.apply_clip_button)
        clip_layout.addStretch(1)
        inspector.addTab(clip_panel, "镜头")

        audio_panel, audio_layout = self._panel("附加音轨", "背景音乐、配音均可编辑")
        self.audio_table = QTableWidget(0, 3, objectName="AudioTable")
        self.audio_table.setHorizontalHeaderLabels(["音轨", "开始", "音量"])
        self.audio_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.audio_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.audio_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.audio_table.verticalHeader().setVisible(False)
        self.audio_table.horizontalHeader().setStretchLastSection(True)
        audio_layout.addWidget(self.audio_table, 1)
        audio_form = QFormLayout()
        self.audio_start = self._time_spin()
        self.audio_in = self._time_spin()
        self.audio_out = self._time_spin()
        self.audio_volume = self._volume_spin()
        self.audio_muted = QCheckBox("停用该音轨")
        audio_form.addRow("时间线开始", self.audio_start)
        audio_form.addRow("素材入点", self.audio_in)
        audio_form.addRow("素材出点", self.audio_out)
        audio_form.addRow("音量", self.audio_volume)
        audio_form.addRow("", self.audio_muted)
        audio_layout.addLayout(audio_form)
        audio_actions = QHBoxLayout()
        self.apply_audio_button = self._button("应用", "check")
        self.delete_audio_button = self._button("删除", "trash")
        self.delete_audio_button.setObjectName("DangerButton")
        audio_actions.addWidget(self.apply_audio_button)
        audio_actions.addWidget(self.delete_audio_button)
        audio_layout.addLayout(audio_actions)
        inspector.addTab(audio_panel, "音轨")

        subtitle_panel, subtitle_layout = self._panel("字幕轨", "识别结果可以逐条修改或删除")
        self.subtitle_table = QTableWidget(0, 3, objectName="SubtitleTable")
        self.subtitle_table.setHorizontalHeaderLabels(["开始", "结束", "字幕"])
        self.subtitle_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.subtitle_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.subtitle_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.subtitle_table.verticalHeader().setVisible(False)
        self.subtitle_table.horizontalHeader().setStretchLastSection(True)
        subtitle_layout.addWidget(self.subtitle_table, 1)
        subtitle_form = QFormLayout()
        self.subtitle_start = self._time_spin()
        self.subtitle_end = self._time_spin()
        self.subtitle_text = QLineEdit()
        self.subtitle_enabled = QCheckBox("启用该字幕")
        subtitle_form.addRow("素材开始", self.subtitle_start)
        subtitle_form.addRow("素材结束", self.subtitle_end)
        subtitle_form.addRow("文字", self.subtitle_text)
        subtitle_form.addRow("", self.subtitle_enabled)
        subtitle_layout.addLayout(subtitle_form)
        subtitle_actions = QHBoxLayout()
        self.apply_subtitle_button = self._button("应用", "check")
        self.delete_subtitle_button = self._button("删除", "trash")
        self.delete_subtitle_button.setObjectName("DangerButton")
        subtitle_actions.addWidget(self.apply_subtitle_button)
        subtitle_actions.addWidget(self.delete_subtitle_button)
        subtitle_layout.addLayout(subtitle_actions)
        inspector.addTab(subtitle_panel, "字幕")

        project_panel, project_layout = self._panel("输出画布")
        project_form = QFormLayout()
        self.resolution_combo = QComboBox()
        for label, width, height in (
            ("1920 × 1080（横屏）", 1920, 1080),
            ("1080 × 1920（竖屏）", 1080, 1920),
            ("1080 × 1080（方形）", 1080, 1080),
            ("1280 × 720（横屏）", 1280, 720),
        ):
            self.resolution_combo.addItem(label, (width, height))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        project_form.addRow("分辨率", self.resolution_combo)
        project_form.addRow("帧率", self.fps_spin)
        project_layout.addLayout(project_form)
        self.apply_project_button = self._button("应用项目设置", "check")
        project_layout.addWidget(self.apply_project_button)
        project_layout.addStretch(1)
        inspector.addTab(project_panel, "项目")
        splitter.addWidget(inspector)

        splitter.setSizes([235, 675, 285])
        splitter.setStretchFactor(0, 20)
        splitter.setStretchFactor(1, 55)
        splitter.setStretchFactor(2, 25)
        root.addWidget(splitter, 1)

        status = QFrame(objectName="EditorStatusBar")
        status_layout = QHBoxLayout(status)
        status_layout.setContentsMargins(10, 6, 10, 6)
        self.editor_status = QLabel("就绪", objectName="EditorStatus")
        self.editor_progress = QProgressBar()
        self.editor_progress.setRange(0, 1000)
        self.editor_progress.setValue(0)
        self.editor_progress.setFixedWidth(250)
        self.cancel_button = self._button("取消任务", "cancel")
        self.cancel_button.hide()
        self.open_export_button = self._button("打开成片", "folder-open")
        self.open_export_button.hide()
        status_layout.addWidget(self.editor_status, 1)
        status_layout.addWidget(self.editor_progress)
        status_layout.addWidget(self.open_export_button)
        status_layout.addWidget(self.cancel_button)
        root.addWidget(status)

        self.new_button.clicked.connect(self.new_project)
        self.open_button.clicked.connect(self.open_project_dialog)
        self.save_button.clicked.connect(self.save_project)
        self.undo_button.clicked.connect(self.undo)
        self.redo_button.clicked.connect(self.redo)
        self.import_video_button.clicked.connect(self.import_video_dialog)
        self.import_audio_button.clicked.connect(self.import_audio_dialog)
        self.auto_highlight_button.clicked.connect(self.open_highlight_dialog)
        self.narration_button.clicked.connect(self.open_narration_dialog)
        self.export_button.clicked.connect(self.export_dialog)
        self.asset_to_timeline_button.clicked.connect(self.add_selected_asset_to_timeline)
        self.asset_preview_button.clicked.connect(self.preview_selected_asset)
        self.asset_list.itemSelectionChanged.connect(self._refresh_actions)
        self.asset_list.itemDoubleClicked.connect(lambda _item: self.add_selected_asset_to_timeline())
        self.timeline_table.itemSelectionChanged.connect(self._on_timeline_selection)
        self.audio_table.itemSelectionChanged.connect(self._on_audio_selection)
        self.subtitle_table.itemSelectionChanged.connect(self._on_subtitle_selection)
        self.timeline_view.clipSelected.connect(self._select_clip_from_track)
        self.timeline_view.audioSelected.connect(self._select_audio_from_track)
        self.timeline_view.subtitleSelected.connect(self._select_subtitle_from_track)
        self.timeline_view.clipMoveRequested.connect(self._move_clip_to_index)
        self.timeline_view.transitionRequested.connect(self._edit_transition_from_track)
        self.split_button.clicked.connect(self.split_selected_clip)
        self.duplicate_button.clicked.connect(self.duplicate_selected_clip)
        self.move_up_button.clicked.connect(lambda: self.move_selected_clip(-1))
        self.move_down_button.clicked.connect(lambda: self.move_selected_clip(1))
        self.delete_clip_button.clicked.connect(self.delete_selected_clip)
        self.smart_split_button.clicked.connect(self.open_scene_split_dialog)
        self.recognize_subtitles_button.clicked.connect(self.recognize_selected_subtitles)
        self.apply_clip_button.clicked.connect(self.apply_clip_changes)
        self.apply_audio_button.clicked.connect(self.apply_audio_changes)
        self.delete_audio_button.clicked.connect(self.delete_selected_audio)
        self.apply_subtitle_button.clicked.connect(self.apply_subtitle_changes)
        self.delete_subtitle_button.clicked.connect(self.delete_selected_subtitle)
        self.apply_project_button.clicked.connect(self.apply_project_settings)
        self.clip_transition.currentIndexChanged.connect(
            lambda _index: self.clip_transition_duration.setEnabled(
                self.clip_transition.isEnabled() and self.clip_transition.currentData() != "cut"
            )
        )
        self.cancel_button.clicked.connect(self.cancel_active_task)
        self.open_export_button.clicked.connect(self.open_last_export)

    @staticmethod
    def _time_spin() -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 24 * 3600.0)
        spin.setDecimals(3)
        spin.setSingleStep(0.1)
        return spin

    @staticmethod
    def _volume_spin() -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 2.0)
        spin.setDecimals(2)
        spin.setSingleStep(0.05)
        spin.setValue(1.0)
        return spin

    def _connect_player(self) -> None:
        self.play_button.clicked.connect(self.toggle_playback)
        self.position_slider.sliderMoved.connect(self.player.setPosition)
        self.playback_rate_combo.currentIndexChanged.connect(self._set_playback_rate)
        self.volume_button.clicked.connect(self.toggle_preview_mute)
        self.volume_slider.valueChanged.connect(self._set_preview_volume)
        self.fullscreen_button.clicked.connect(self.toggle_preview_fullscreen)
        self.player.positionChanged.connect(self._on_player_position)
        self.player.durationChanged.connect(self._on_player_duration)
        self.player.playbackStateChanged.connect(self._on_playback_state)
        self.player.mediaStatusChanged.connect(self._on_media_status)
        self.player.errorOccurred.connect(self._on_player_error)

    def _selected_asset(self) -> MediaAsset | None:
        item = self.asset_list.currentItem()
        if not item or not item.isSelected():
            return None
        asset_id = item.data(Qt.ItemDataRole.UserRole)
        try:
            return self.project.asset(asset_id)
        except KeyError:
            return None

    def _selected_clip_index(self) -> int:
        return self.timeline_table.currentRow()

    def _selected_audio_index(self) -> int:
        return self.audio_table.currentRow()

    def _selected_subtitle_index(self) -> int:
        return self.subtitle_table.currentRow()

    def _record_change(self) -> None:
        self.history.record(self.project)

    def _mark_dirty(self) -> None:
        self.dirty = True
        self._refresh_title()

    def _refresh_title(self) -> None:
        suffix = " *" if self.dirty else ""
        self.project_title.setText(f"{self.project.name}{suffix}")

    def _refresh_all(
        self,
        clip_row: int = -1,
        audio_row: int = -1,
        asset_id: str | None = None,
        subtitle_row: int = -1,
    ) -> None:
        if asset_id is None:
            selected_asset = self._selected_asset()
            asset_id = selected_asset.id if selected_asset else None
        self._updating_ui = True
        self._refresh_title()
        self.asset_list.clear()
        for asset in self.project.assets:
            item = QListWidgetItem()
            icon = svg_icon("video" if asset.kind == "video" else "music")
            item.setIcon(icon)
            meta = format_timecode(asset.duration)
            if asset.kind == "video":
                meta += f" · {asset.width}×{asset.height}"
            item.setText(f"{asset.name}\n{meta}")
            item.setData(Qt.ItemDataRole.UserRole, asset.id)
            item.setToolTip(asset.path)
            self.asset_list.addItem(item)
            if asset.id == asset_id:
                self.asset_list.setCurrentItem(item)

        self.timeline_table.setRowCount(len(self.project.clips))
        for row, clip in enumerate(self.project.clips):
            values = (
                str(row + 1),
                clip.name,
                format_timecode(clip.in_point),
                format_timecode(clip.out_point),
                format_timecode(clip.duration),
                clip.selection_reason or "人工",
                "静音" if clip.muted else f"{clip.volume:.2f}",
            )
            for column, value in enumerate(values):
                self.timeline_table.setItem(row, column, QTableWidgetItem(value))
        self.timeline_table.resizeColumnsToContents()
        self.timeline_table.horizontalHeader().setStretchLastSection(True)
        self.timeline_duration.setText(f"总时长 {format_timecode(self.project.duration)}")

        self.audio_table.setRowCount(len(self.project.audio_tracks))
        for row, track in enumerate(self.project.audio_tracks):
            values = (track.name, format_timecode(track.start_time), "停用" if track.muted else f"{track.volume:.2f}")
            for column, value in enumerate(values):
                self.audio_table.setItem(row, column, QTableWidgetItem(value))
        self.audio_table.resizeColumnsToContents()
        self.audio_table.horizontalHeader().setStretchLastSection(True)

        self.subtitle_table.setRowCount(len(self.project.subtitle_cues))
        for row, cue in enumerate(self.project.subtitle_cues):
            values = (format_timecode(cue.start), format_timecode(cue.end), cue.text)
            for column, value in enumerate(values):
                self.subtitle_table.setItem(row, column, QTableWidgetItem(value))
        self.subtitle_table.resizeColumnsToContents()
        self.subtitle_table.horizontalHeader().setStretchLastSection(True)

        resolution_index = self.resolution_combo.findData((self.project.width, self.project.height))
        if resolution_index >= 0:
            self.resolution_combo.setCurrentIndex(resolution_index)
        self.fps_spin.setValue(round(self.project.fps))
        if 0 <= clip_row < len(self.project.clips):
            self.timeline_table.selectRow(clip_row)
        else:
            self._clear_clip_inspector()
        if 0 <= audio_row < len(self.project.audio_tracks):
            self.audio_table.selectRow(audio_row)
        else:
            self._clear_audio_inspector()
        if 0 <= subtitle_row < len(self.project.subtitle_cues):
            self.subtitle_table.selectRow(subtitle_row)
            self._selected_subtitle = subtitle_row
        else:
            self._selected_subtitle = -1
            self._clear_subtitle_inspector()
        self.timeline_view.set_project(self.project, clip_row, audio_row, subtitle_row)
        self._updating_ui = False
        self._refresh_actions()

    def _refresh_actions(self) -> None:
        asset = self._selected_asset()
        clip_selected = 0 <= self._selected_clip_index() < len(self.project.clips)
        audio_selected = 0 <= self._selected_audio_index() < len(self.project.audio_tracks)
        subtitle_selected = 0 <= self._selected_subtitle_index() < len(self.project.subtitle_cues)
        active = self.has_running_task
        self.undo_button.setEnabled(self.history.can_undo and not active)
        self.redo_button.setEnabled(self.history.can_redo and not active)
        self.export_button.setEnabled(bool(self.project.clips) and not active)
        self.import_video_button.setEnabled(not active)
        self.import_audio_button.setEnabled(not active)
        self.asset_preview_button.setEnabled(asset is not None and not active)
        self.asset_to_timeline_button.setEnabled(
            asset is not None and asset.kind == "video" and not active
        )
        self.auto_highlight_button.setEnabled(
            any(asset.kind == "video" for asset in self.project.assets) and not active
        )
        self.narration_button.setEnabled(bool(self.project.clips) and not active)
        self.split_button.setEnabled(clip_selected and not active)
        self.duplicate_button.setEnabled(clip_selected and not active)
        self.move_up_button.setEnabled(clip_selected and self._selected_clip_index() > 0 and not active)
        self.move_down_button.setEnabled(
            clip_selected and self._selected_clip_index() < len(self.project.clips) - 1 and not active
        )
        self.delete_clip_button.setEnabled(clip_selected and not active)
        self.smart_split_button.setEnabled(clip_selected and not active)
        self.recognize_subtitles_button.setEnabled(clip_selected and not active)
        self.apply_clip_button.setEnabled(clip_selected and not active)
        self.apply_audio_button.setEnabled(audio_selected and not active)
        self.delete_audio_button.setEnabled(audio_selected and not active)
        self.apply_subtitle_button.setEnabled(subtitle_selected and not active)
        self.delete_subtitle_button.setEnabled(subtitle_selected and not active)

    def _clear_clip_inspector(self) -> None:
        self.clip_name.clear()
        self.clip_in.setValue(0.0)
        self.clip_out.setValue(0.0)
        self.clip_volume.setValue(1.0)
        self.clip_muted.setChecked(False)
        self.clip_reason.clear()
        self.clip_evidence.clear()
        self.clip_transition.setCurrentIndex(0)
        self.clip_transition_duration.setValue(0.5)

    def _clear_audio_inspector(self) -> None:
        for spin in (self.audio_start, self.audio_in, self.audio_out):
            spin.setValue(0.0)
        self.audio_volume.setValue(0.65)
        self.audio_muted.setChecked(False)

    def _clear_subtitle_inspector(self) -> None:
        self.subtitle_start.setValue(0.0)
        self.subtitle_end.setValue(0.0)
        self.subtitle_text.clear()
        self.subtitle_enabled.setChecked(False)

    def _show_error(self, title: str, detail: str) -> None:
        self.editor_status.setText(f"{title}：{detail}")
        QMessageBox.warning(self, title, detail)

    def new_project(self) -> None:
        if not self._confirm_discard():
            return
        self.player.stop()
        self.project = EditProject()
        self.project_path = None
        self.history.clear()
        self.dirty = False
        self._refresh_all()
        self.editor_status.setText("已新建剪辑项目")

    def _confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        answer = QMessageBox.question(
            self,
            "尚未保存",
            "当前剪辑有未保存修改，继续将丢失这些修改。是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def open_project_dialog(self) -> None:
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "打开剪辑项目", "", PROJECT_FILTER)
        if path:
            self.load_project(path)

    def load_project(self, path: str | Path) -> None:
        try:
            project = EditProject.load(path)
        except BaseException as error:
            self._show_error("无法打开项目", str(error))
            return
        self.player.stop()
        self.project = project
        self.project_path = Path(path)
        self.history.clear()
        self.dirty = False
        self._refresh_all()
        self.editor_status.setText(f"已打开：{self.project_path.name}")

    def save_project(self) -> None:
        if self.project_path is None:
            self.save_project_as()
            return
        try:
            self.project.save(self.project_path)
        except BaseException as error:
            self._show_error("保存失败", str(error))
            return
        self.dirty = False
        self._refresh_title()
        self.editor_status.setText(f"已保存：{self.project_path.name}")

    def save_project_as(self) -> None:
        initial = f"{self.project.name}.slproj"
        path, _ = QFileDialog.getSaveFileName(self, "保存剪辑项目", initial, PROJECT_FILTER)
        if not path:
            return
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(".slproj")
        self.project_path = target
        self.project.name = target.stem
        self.save_project()

    def import_video_dialog(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "导入视频镜头", "", VIDEO_FILTER)
        if paths:
            self.import_paths(paths, "video")

    def import_audio_dialog(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "添加音轨", "", AUDIO_FILTER)
        if paths:
            self.import_paths(paths, "audio")

    def import_paths(self, paths: list[str], intent: str = "video") -> None:
        if self.has_running_task or not paths:
            return
        self._probe_intent = intent
        worker = MediaProbeWorker(paths)
        worker.item_started.connect(lambda path: self.editor_status.setText(f"正在分析：{Path(path).name}"))
        worker.item_ready.connect(self._on_asset_ready)
        worker.item_failed.connect(self._on_asset_failed)
        worker.cancelled.connect(lambda: self.editor_status.setText("素材导入已取消"))
        self._start_worker(worker, "probe")

    def open_highlight_dialog(self) -> None:
        video_assets = [asset for asset in self.project.assets if asset.kind == "video"]
        if not video_assets or self.has_running_task:
            return
        selected = self._selected_asset()
        selected_id = selected.id if selected and selected.kind == "video" else None
        dialog = HighlightDialog(
            video_assets,
            selected_id,
            self.model_manager,
            self.manage_models_callback,
            self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            asset_ids, settings = dialog.configuration()
            self.start_highlight(asset_ids, settings)

    def start_highlight(self, asset_ids: list[str], settings: dict) -> None:
        if self.has_running_task or not asset_ids:
            return
        worker = LongVideoHighlightWorker(self.project, asset_ids, settings, self.model_manager)
        worker.progress.connect(self._on_export_progress)
        worker.completed.connect(self._on_highlight_completed)
        worker.failed.connect(lambda detail: self._show_error("自动精华失败", detail))
        worker.cancelled.connect(lambda: self.editor_status.setText("自动精华分析已取消"))
        self.editor_status.setText("准备分析长视频场景…")
        self._start_worker(worker, "highlight")

    def _on_highlight_completed(self, clips: list, settings: dict) -> None:
        if not clips:
            self._show_error("没有生成镜头", "当前设置没有产生可用的精华片段。")
            return
        self._record_change()
        result_settings = dict(settings)
        evidence = list(result_settings.pop("_analysis_evidence", []))
        subtitles = list(result_settings.pop("_subtitle_cues", []))
        warnings = list(result_settings.pop("_warnings", []))
        if settings.get("replace_timeline", True):
            self.project.clips = list(clips)
        else:
            self.project.clips.extend(clips)
        analyzed_asset_ids = {clip.asset_id for clip in clips}
        self.project.analysis_evidence = [
            item for item in self.project.analysis_evidence if item.asset_id not in analyzed_asset_ids
        ] + evidence
        self.project.subtitle_cues = [
            item for item in self.project.subtitle_cues if item.asset_id not in analyzed_asset_ids
        ] + subtitles
        self.project.source_recipe = "long_video_highlight"
        self.project.generation_settings = result_settings
        self.project.touch()
        self._mark_dirty()
        self._refresh_all(0)
        self.editor_progress.setRange(0, 1000)
        self.editor_progress.setValue(1000)
        suffix = f" · {len(subtitles)} 条字幕、{len(evidence)} 条证据" if subtitles or evidence else ""
        if warnings:
            suffix += f" · {len(warnings)} 项增强已回退"
        self.editor_status.setText(f"自动精华已生成 {len(clips)} 个镜头{suffix} · 可继续人工修改、撤销或保存")

    def open_scene_split_dialog(self) -> None:
        row = self._selected_clip_index()
        if self.has_running_task or not 0 <= row < len(self.project.clips):
            return
        dialog = SceneSplitDialog(self.project.clips[row].name, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._scene_split_clip_index = row
        worker = SceneSplitWorker(
            self.project,
            row,
            dialog.threshold.value(),
            dialog.minimum_duration.value(),
        )
        worker.progress.connect(self._on_export_progress)
        worker.completed.connect(self._on_scene_split_completed)
        worker.failed.connect(lambda detail: self._show_error("智能分镜失败", detail))
        worker.cancelled.connect(lambda: self.editor_status.setText("智能分镜已取消"))
        self.editor_status.setText("准备检测当前镜头的场景边界…")
        self._start_worker(worker, "scene_split")

    def _on_scene_split_completed(self, boundaries: list[float]) -> None:
        row = self._scene_split_clip_index
        if not 0 <= row < len(self.project.clips):
            return
        if not boundaries:
            self.editor_status.setText("未检测到明显场景切换；可以降低灵敏度后重试")
            return
        self._record_change()
        segments = self.project.split_clip_at_scenes(row, boundaries)
        self._mark_dirty()
        self._refresh_all(row)
        self.editor_status.setText(f"智能分镜完成：生成 {len(segments)} 个可编辑镜头")

    def recognize_selected_subtitles(self) -> None:
        row = self._selected_clip_index()
        if self.has_running_task or not 0 <= row < len(self.project.clips):
            return
        clip = self.project.clips[row]
        asset = self.project.asset(clip.asset_id)
        if not asset.has_audio:
            self._show_error("无法识别字幕", "当前视频不包含可识别的音频轨。")
            return
        if not self.model_manager.capability_ready("speech"):
            self.editor_status.setText("缺少已校验的 Whisper 模型，正在打开模型管理")
            if self.manage_models_callback:
                self.manage_models_callback()
            if not self.model_manager.capability_ready("speech"):
                self.editor_status.setText("Whisper 模型尚未就绪，安装并校验后可一键识别字幕")
                return
        worker = SpeechRecognitionWorker(self.project, asset.id, self.model_manager)
        worker.progress.connect(self._on_export_progress)
        worker.completed.connect(self._on_speech_recognition_completed)
        worker.failed.connect(lambda detail: self._show_error("字幕识别失败", detail))
        worker.cancelled.connect(lambda: self.editor_status.setText("字幕识别已取消"))
        self.editor_status.setText(f"准备识别：{asset.name}")
        self._start_worker(worker, "speech")

    def _on_speech_recognition_completed(self, asset_id: str, subtitles: list, evidence: list) -> None:
        self._record_change()
        self.project.subtitle_cues = [
            cue for cue in self.project.subtitle_cues if cue.asset_id != asset_id
        ] + list(subtitles)
        self.project.analysis_evidence = [
            item
            for item in self.project.analysis_evidence
            if not (item.asset_id == asset_id and item.kind == "speech")
        ] + list(evidence)
        self.project.touch()
        self._mark_dirty()
        first = next(
            (index for index, cue in enumerate(self.project.subtitle_cues) if cue.asset_id == asset_id),
            -1,
        )
        self._refresh_all(self._selected_clip_index(), subtitle_row=first)
        self.editor_status.setText(f"字幕识别完成：{len(subtitles)} 条 · 可在字幕轨逐条修改")

    def open_narration_dialog(self) -> None:
        if self.has_running_task or not self.project.clips:
            return
        dialog = NarrationRecipeDialog(
            self.model_manager,
            self.manage_models_callback,
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        recipe = dialog.configuration()
        self._pending_narration_recipe = recipe
        if recipe["use_model"]:
            worker = NarrationDraftWorker(
                self.project,
                self.model_manager,
                recipe["style"],
                recipe["max_chars"],
            )
            worker.progress.connect(self._on_export_progress)
            worker.completed.connect(self._on_narration_draft_completed)
            worker.failed.connect(self._on_narration_draft_failed)
            worker.cancelled.connect(lambda: self.editor_status.setText("Qwen 解说草稿生成已取消"))
            self.editor_status.setText("准备加载本地 Qwen 解说模型…")
            self._start_worker(worker, "narration_draft")
            return
        draft = build_narration_draft(self.project, recipe["style"], recipe["max_chars"])
        self._pending_narration_review = (
            draft,
            {"provider": "deterministic", "style": recipe["style"], "max_chars": recipe["max_chars"]},
            recipe,
        )
        self._present_pending_narration_review()

    def _on_narration_draft_completed(self, text: str, metadata: dict) -> None:
        self._pending_narration_review = (text, dict(metadata), dict(self._pending_narration_recipe))
        self.editor_status.setText("Qwen 解说草稿已生成 · 即将打开人工修改")

    def _on_narration_draft_failed(self, detail: str) -> None:
        recipe = dict(self._pending_narration_recipe)
        draft = build_narration_draft(self.project, recipe.get("style", "summary"), recipe.get("max_chars", 420))
        self._pending_narration_review = (
            draft,
            {
                "provider": "deterministic_fallback",
                "style": recipe.get("style", "summary"),
                "max_chars": recipe.get("max_chars", 420),
                "warning": detail,
            },
            recipe,
        )
        self.editor_status.setText(f"本地 Qwen 生成失败，已准备规则草稿：{detail}")

    def _present_pending_narration_review(self) -> None:
        if self.has_running_task or self._pending_narration_review is None:
            return
        draft, metadata, recipe = self._pending_narration_review
        self._pending_narration_review = None
        provider = metadata.get("provider")
        source_labels = {
            "llama.cpp": "本地 Qwen2.5 3B（llama.cpp）",
            "deterministic": "字幕/镜头规则草稿",
            "deterministic_fallback": "Qwen 失败后的字幕/镜头规则草稿",
        }
        dialog = NarrationDialog(
            self.project,
            draft,
            source_labels.get(str(provider), str(provider or "本地规则")),
            str(recipe.get("style", "summary")),
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.editor_status.setText("已取消添加解说；当前时间线未修改")
            return
        settings = dialog.configuration()
        if not settings["text"]:
            self._show_error("无法生成解说", "请先填写解说文字。")
            return
        self._pending_narration_metadata = dict(metadata)
        self._pending_narration_metadata["edited_before_tts"] = settings["text"] != draft
        narration_dir = self.model_manager.root.parent / "narrations"
        output = narration_dir / f"{self.project.id}-{new_id('voice')}.wav"
        worker = NarrationWorker(
            settings["text"],
            output,
            settings["rate"],
            settings["start_time"],
            settings["volume"],
        )
        worker.progress.connect(self._on_export_progress)
        worker.completed.connect(self._on_narration_completed)
        worker.failed.connect(lambda detail: self._show_error("解说生成失败", detail))
        worker.cancelled.connect(lambda: self.editor_status.setText("解说生成已取消"))
        self.editor_status.setText("正在生成离线解说配音…")
        self._start_worker(worker, "narration")

    def _on_narration_completed(
        self,
        asset: MediaAsset,
        text: str,
        start_time: float,
        volume: float,
    ) -> None:
        self._record_change()
        added = self.project.add_asset(asset)
        track = self.project.add_audio_asset(added.id)
        track.name = "智能解说"
        track.start_time = max(0.0, start_time)
        track.volume = max(0.0, min(2.0, volume))
        self.project.generation_settings["narration_script"] = text
        self.project.generation_settings["narration"] = dict(self._pending_narration_metadata)
        self.project.touch()
        self._pending_narration_metadata = {}
        self._mark_dirty()
        row = len(self.project.audio_tracks) - 1
        self._refresh_all(audio_row=row, asset_id=added.id)
        self.editor_status.setText("解说已生成并加入音频轨 · 可以继续修改开始时间和音量")

    def _on_asset_ready(self, asset: MediaAsset) -> None:
        self._record_change()
        added = self.project.add_asset(asset)
        try:
            if self._probe_intent == "video":
                self.project.append_video_asset(added.id)
            else:
                self.project.add_audio_asset(added.id)
        except ValueError as error:
            self.editor_status.setText(str(error))
        self._mark_dirty()
        self._refresh_all(
            len(self.project.clips) - 1 if self._probe_intent == "video" else -1,
            len(self.project.audio_tracks) - 1 if self._probe_intent == "audio" else -1,
            added.id,
        )

    def _on_asset_failed(self, path: str, detail: str) -> None:
        self.editor_status.setText(f"导入失败：{Path(path).name} · {detail}")

    def add_selected_asset_to_timeline(self) -> None:
        asset = self._selected_asset()
        if not asset:
            return
        self._record_change()
        try:
            self.project.append_video_asset(asset.id)
        except ValueError as error:
            self._show_error("无法加入时间线", str(error))
            return
        self._mark_dirty()
        self._refresh_all(len(self.project.clips) - 1)

    def preview_selected_asset(self) -> None:
        asset = self._selected_asset()
        if not asset:
            self.editor_status.setText("请先在左侧素材库中选择一个视频，再点击预览")
            return
        self._preview_clip_index = -1
        self._load_preview(asset.path, 0.0, autoplay=True, display_name=asset.name)

    def _load_preview(
        self,
        path: str,
        position: float,
        *,
        autoplay: bool = False,
        display_name: str | None = None,
    ) -> None:
        self.player.stop()
        self._pending_preview_position = max(0, round(position * 1000))
        self._preview_autoplay = autoplay
        self._preview_source_name = display_name or Path(path).name
        self.editor_status.setText(f"正在加载预览：{self._preview_source_name}")
        self.editor_status.setToolTip("")
        self.player.setSource(QUrl.fromLocalFile(path))

    def _on_timeline_selection(self) -> None:
        if self._updating_ui:
            return
        row = self._selected_clip_index()
        if not 0 <= row < len(self.project.clips):
            self._clear_clip_inspector()
            self._refresh_actions()
            return
        clip = self.project.clips[row]
        self.inspector_tabs.setCurrentIndex(0)
        asset = self.project.asset(clip.asset_id)
        self.clip_name.setText(clip.name)
        self.clip_in.setMaximum(asset.duration)
        self.clip_out.setMaximum(asset.duration)
        self.clip_in.setValue(clip.in_point)
        self.clip_out.setValue(clip.out_point)
        self.clip_volume.setValue(clip.volume)
        self.clip_muted.setChecked(clip.muted)
        self.clip_reason.setText(clip.selection_reason or "人工选择")
        self.clip_evidence.setText(f"{len(clip.evidence_ids)} 条" if clip.evidence_ids else "无")
        transition_index = self.clip_transition.findData(clip.transition)
        self.clip_transition.setCurrentIndex(max(0, transition_index))
        self.clip_transition.setEnabled(row > 0)
        self.clip_transition_duration.setValue(max(0.1, clip.transition_duration or 0.5))
        self.clip_transition_duration.setEnabled(row > 0 and clip.transition != "cut")
        self._preview_clip_index = row
        self._load_preview(asset.path, clip.in_point, display_name=asset.name)
        self.timeline_view.set_project(self.project, selected_clip=row)
        self._refresh_actions()

    def apply_clip_changes(self) -> None:
        row = self._selected_clip_index()
        if not 0 <= row < len(self.project.clips):
            return
        self._record_change()
        try:
            self.project.update_clip(
                row,
                in_point=self.clip_in.value(),
                out_point=self.clip_out.value(),
                volume=self.clip_volume.value(),
                muted=self.clip_muted.isChecked(),
            )
            self.project.set_clip_transition(
                row,
                str(self.clip_transition.currentData() or "cut"),
                self.clip_transition_duration.value(),
            )
        except ValueError as error:
            self.project = self.history.undo(self.project)
            self._refresh_all(row)
            self._show_error("镜头参数无效", str(error))
            return
        self._mark_dirty()
        self._refresh_all(row)
        self.editor_status.setText("镜头修改已应用")

    def split_selected_clip(self) -> None:
        row = self._selected_clip_index()
        if not 0 <= row < len(self.project.clips):
            return
        clip = self.project.clips[row]
        point = self.player.position() / 1000.0
        if not clip.in_point < point < clip.out_point:
            point = clip.in_point + clip.duration / 2
        self._record_change()
        try:
            self.project.split_clip(row, point)
        except ValueError as error:
            self._show_error("无法切分", str(error))
            return
        self._mark_dirty()
        self._refresh_all(row + 1)
        self.editor_status.setText(f"已在 {format_timecode(point)} 切分镜头")

    def duplicate_selected_clip(self) -> None:
        row = self._selected_clip_index()
        if 0 <= row < len(self.project.clips):
            self._record_change()
            self.project.duplicate_clip(row)
            self._mark_dirty()
            self._refresh_all(row + 1)

    def delete_selected_clip(self) -> None:
        row = self._selected_clip_index()
        if 0 <= row < len(self.project.clips):
            self._record_change()
            self.project.remove_clip(row)
            self._mark_dirty()
            self._refresh_all(min(row, len(self.project.clips) - 1))

    def move_selected_clip(self, offset: int) -> None:
        row = self._selected_clip_index()
        if 0 <= row < len(self.project.clips):
            self._record_change()
            target = self.project.move_clip(row, row + offset)
            self._mark_dirty()
            self._refresh_all(target)

    def _select_clip_from_track(self, row: int) -> None:
        if 0 <= row < len(self.project.clips):
            self.timeline_table.selectRow(row)
            self._on_timeline_selection()

    def _move_clip_to_index(self, row: int, target: int) -> None:
        if not 0 <= row < len(self.project.clips):
            return
        self._record_change()
        destination = self.project.move_clip(row, target)
        self._mark_dirty()
        self._refresh_all(destination)
        self.editor_status.setText(f"镜头已移动到第 {destination + 1} 位")

    def _edit_transition_from_track(self, row: int) -> None:
        self._select_clip_from_track(row)
        self.inspector_tabs.setCurrentIndex(0)
        self.clip_transition.setFocus()
        self.editor_status.setText("请在右侧镜头属性中选择转场并应用")

    def _on_audio_selection(self) -> None:
        if self._updating_ui:
            return
        row = self._selected_audio_index()
        if not 0 <= row < len(self.project.audio_tracks):
            self._clear_audio_inspector()
            self._refresh_actions()
            return
        track = self.project.audio_tracks[row]
        self.inspector_tabs.setCurrentIndex(1)
        asset = self.project.asset(track.asset_id)
        self.audio_start.setValue(track.start_time)
        self.audio_in.setMaximum(asset.duration)
        self.audio_out.setMaximum(asset.duration)
        self.audio_in.setValue(track.in_point)
        self.audio_out.setValue(track.out_point)
        self.audio_volume.setValue(track.volume)
        self.audio_muted.setChecked(track.muted)
        self.timeline_view.set_project(self.project, selected_audio=row)
        self._refresh_actions()

    def _select_audio_from_track(self, row: int) -> None:
        if 0 <= row < len(self.project.audio_tracks):
            self.audio_table.selectRow(row)
            self._on_audio_selection()

    def apply_audio_changes(self) -> None:
        row = self._selected_audio_index()
        if not 0 <= row < len(self.project.audio_tracks):
            return
        self._record_change()
        try:
            self.project.update_audio_track(
                row,
                start_time=self.audio_start.value(),
                in_point=self.audio_in.value(),
                out_point=self.audio_out.value(),
                volume=self.audio_volume.value(),
                muted=self.audio_muted.isChecked(),
            )
        except ValueError as error:
            self.project = self.history.undo(self.project)
            self._refresh_all(audio_row=row)
            self._show_error("音轨参数无效", str(error))
            return
        self._mark_dirty()
        self._refresh_all(audio_row=row)

    def delete_selected_audio(self) -> None:
        row = self._selected_audio_index()
        if 0 <= row < len(self.project.audio_tracks):
            self._record_change()
            self.project.remove_audio_track(row)
            self._mark_dirty()
            self._refresh_all(audio_row=min(row, len(self.project.audio_tracks) - 1))

    def _on_subtitle_selection(self) -> None:
        if self._updating_ui:
            return
        row = self._selected_subtitle_index()
        if not 0 <= row < len(self.project.subtitle_cues):
            self._selected_subtitle = -1
            self._clear_subtitle_inspector()
            self._refresh_actions()
            return
        cue = self.project.subtitle_cues[row]
        self._selected_subtitle = row
        self.inspector_tabs.setCurrentIndex(2)
        asset = self.project.asset(cue.asset_id)
        self.subtitle_start.setMaximum(asset.duration)
        self.subtitle_end.setMaximum(asset.duration)
        self.subtitle_start.setValue(cue.start)
        self.subtitle_end.setValue(cue.end)
        self.subtitle_text.setText(cue.text)
        self.subtitle_enabled.setChecked(cue.enabled)
        self.timeline_view.set_project(self.project, selected_subtitle=row)
        self._refresh_actions()

    def _select_subtitle_from_track(self, row: int) -> None:
        if 0 <= row < len(self.project.subtitle_cues):
            self.subtitle_table.selectRow(row)
            self._on_subtitle_selection()

    def apply_subtitle_changes(self) -> None:
        row = self._selected_subtitle_index()
        if not 0 <= row < len(self.project.subtitle_cues):
            return
        self._record_change()
        try:
            self.project.update_subtitle(
                row,
                start=self.subtitle_start.value(),
                end=self.subtitle_end.value(),
                text=self.subtitle_text.text(),
                enabled=self.subtitle_enabled.isChecked(),
            )
        except ValueError as error:
            self.project = self.history.undo(self.project)
            self._refresh_all(subtitle_row=row)
            self._show_error("字幕参数无效", str(error))
            return
        self._mark_dirty()
        self._refresh_all(subtitle_row=row)
        self.editor_status.setText("字幕修改已应用")

    def delete_selected_subtitle(self) -> None:
        row = self._selected_subtitle_index()
        if 0 <= row < len(self.project.subtitle_cues):
            self._record_change()
            self.project.remove_subtitle(row)
            self._mark_dirty()
            self._refresh_all(subtitle_row=min(row, len(self.project.subtitle_cues) - 1))

    def apply_project_settings(self) -> None:
        data = self.resolution_combo.currentData()
        if not data:
            return
        self._record_change()
        self.project.width, self.project.height = data
        self.project.fps = float(self.fps_spin.value())
        self.project.touch()
        self._mark_dirty()
        self._refresh_all(self._selected_clip_index(), self._selected_audio_index())
        self.editor_status.setText("项目画布设置已更新")

    def undo(self) -> None:
        if not self.history.can_undo or self.has_running_task:
            return
        self.project = self.history.undo(self.project)
        self.dirty = True
        self._refresh_all()
        self.editor_status.setText("已撤销上一步修改")

    def redo(self) -> None:
        if not self.history.can_redo or self.has_running_task:
            return
        self.project = self.history.redo(self.project)
        self.dirty = True
        self._refresh_all()
        self.editor_status.setText("已重做修改")

    def export_dialog(self) -> None:
        if not self.project.clips or self.has_running_task:
            return
        initial_dir = self.project_path.parent if self.project_path else Path.home() / "Videos"
        initial = initial_dir / f"{self.project.name}.mp4"
        path, _ = QFileDialog.getSaveFileName(self, "导出成片", str(initial), "MP4 视频 (*.mp4)")
        if path:
            target = Path(path)
            if target.suffix.lower() != ".mp4":
                target = target.with_suffix(".mp4")
            self.start_export(target)

    def start_export(self, output_path: str | Path) -> None:
        if self.has_running_task:
            return
        try:
            self.project.validate(check_files=True)
        except BaseException as error:
            self._show_error("无法导出", str(error))
            return
        worker = EditorExportWorker(self.project, output_path)
        worker.progress.connect(self._on_export_progress)
        worker.completed.connect(self._on_export_completed)
        worker.failed.connect(lambda detail: self._show_error("导出失败", detail))
        worker.cancelled.connect(lambda: self.editor_status.setText("导出已取消"))
        self._start_worker(worker, "export")

    def _start_worker(self, worker, operation: str) -> None:
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_worker_finished)
        self._thread = thread
        self._worker = worker
        self._operation = operation
        self.cancel_button.show()
        self.editor_progress.setRange(0, 0 if operation == "probe" else 1000)
        self.editor_progress.setValue(0)
        self.busy_changed.emit(True)
        self._refresh_actions()
        thread.start()

    def _on_export_progress(self, percent: float, message: str) -> None:
        self.editor_progress.setRange(0, 1000)
        self.editor_progress.setValue(round(max(0.0, min(100.0, percent)) * 10))
        self.editor_status.setText(message)

    def _on_export_completed(self, path: str) -> None:
        self._last_export = Path(path)
        self.editor_progress.setRange(0, 1000)
        self.editor_progress.setValue(1000)
        self.editor_status.setText(f"导出完成：{self._last_export.name}")
        self.open_export_button.show()

    def _on_worker_finished(self) -> None:
        operation = self._operation
        self._thread = None
        self._worker = None
        self._operation = None
        self.cancel_button.hide()
        if operation == "probe":
            self.editor_progress.setRange(0, 1000)
            self.editor_progress.setValue(1000)
            self.editor_status.setText(
                f"素材导入完成 · {len(self.project.assets)} 个素材 · {len(self.project.clips)} 个镜头"
            )
        self.busy_changed.emit(False)
        self._refresh_actions()
        if operation == "narration_draft" and self._pending_narration_review is not None:
            QTimer.singleShot(0, self._present_pending_narration_review)

    def cancel_active_task(self) -> None:
        worker = self._worker
        if worker:
            self.editor_status.setText("正在取消任务…")
            worker.cancel()

    def open_last_export(self) -> None:
        if self._last_export and self._last_export.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_export)))

    def toggle_playback(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            return
        if self.player.source().isEmpty():
            asset = self._selected_asset()
            if asset:
                self.preview_selected_asset()
            else:
                self.editor_status.setText("请先从素材库选择视频，或从时间线选择一个镜头")
            return
        self.player.play()

    def _set_playback_rate(self, _index: int) -> None:
        rate = self.playback_rate_combo.currentData()
        if rate is not None:
            self.player.setPlaybackRate(float(rate))

    def _set_preview_volume(self, value: int) -> None:
        self.audio_output.setVolume(max(0.0, min(1.0, value / 100.0)))
        if value > 0 and self.audio_output.isMuted():
            self.audio_output.setMuted(False)
            self.volume_button.setIcon(svg_icon("volume"))

    def toggle_preview_mute(self) -> None:
        muted = not self.audio_output.isMuted()
        self.audio_output.setMuted(muted)
        self.volume_button.setIcon(svg_icon("mute" if muted else "volume"))

    def toggle_preview_fullscreen(self) -> None:
        if self._fullscreen_dialog is not None:
            self._fullscreen_dialog.accept()
            return

        dialog = QDialog(
            self.window(),
            Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint,
        )
        dialog.setObjectName("VideoFullscreenDialog")
        dialog.setWindowTitle("全屏预览")
        full_layout = QVBoxLayout(dialog)
        full_layout.setContentsMargins(0, 0, 0, 0)
        full_layout.setSpacing(0)

        self.preview_layout.removeWidget(self.preview_surface)
        self.preview_surface.setParent(dialog)
        full_layout.addWidget(self.preview_surface)
        self.preview_surface.show()
        self._fullscreen_dialog = dialog
        self.fullscreen_button.setText("退出全屏")
        self.fullscreen_button.setIcon(svg_icon("exit-fullscreen"))
        dialog.finished.connect(lambda _result, host=dialog: self._restore_preview_surface(host))
        dialog.showFullScreen()

    def _restore_preview_surface(self, dialog: QDialog) -> None:
        if self._fullscreen_dialog is not dialog:
            return
        if dialog.layout() is not None:
            dialog.layout().removeWidget(self.preview_surface)
        self.preview_surface.setParent(self.preview_panel)
        self.preview_layout.insertWidget(1, self.preview_surface, 1)
        self.preview_surface.show()
        self._fullscreen_dialog = None
        self.fullscreen_button.setText("全屏")
        self.fullscreen_button.setIcon(svg_icon("fullscreen"))
        dialog.deleteLater()

    def _on_player_position(self, position: int) -> None:
        if not self.position_slider.isSliderDown():
            self.position_slider.setValue(position)
        duration = self.player.duration()
        self.position_label.setText(f"{format_timecode(position / 1000)} / {format_timecode(duration / 1000)}")
        if 0 <= self._preview_clip_index < len(self.project.clips):
            clip = self.project.clips[self._preview_clip_index]
            ranges = self.project.clip_timeline_ranges()
            if self._preview_clip_index < len(ranges):
                timeline_start = ranges[self._preview_clip_index][1]
                self.timeline_view.set_playhead(
                    timeline_start + max(0.0, position / 1000.0 - clip.in_point)
                )
            if position / 1000.0 >= clip.out_point and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
        elif not self.player.source().isEmpty():
            self.timeline_view.set_playhead(position / 1000.0)

    def _on_player_duration(self, duration: int) -> None:
        self.position_slider.setRange(0, max(0, duration))
        self.position_label.setText(
            f"{format_timecode(self.player.position() / 1000)} / {format_timecode(duration / 1000)}"
        )

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.LoadingMedia:
            self.editor_status.setText(f"正在加载预览：{self._preview_source_name}")
            return
        if status in (
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
        ):
            pending_position = self._pending_preview_position
            autoplay = self._preview_autoplay
            self._pending_preview_position = None
            self._preview_autoplay = False
            if pending_position is not None:
                self.player.setPosition(pending_position)
            if autoplay:
                self.player.play()
            elif self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.editor_status.setText(f"正在播放：{self._preview_source_name}")
            else:
                self.editor_status.setText(f"预览已就绪：{self._preview_source_name}")
            return
        if status in (
            QMediaPlayer.MediaStatus.StalledMedia,
            QMediaPlayer.MediaStatus.BufferingMedia,
        ):
            self.editor_status.setText(f"正在缓冲预览：{self._preview_source_name}")
            return
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.editor_status.setText(f"预览播放完成：{self._preview_source_name}")
            return
        if status == QMediaPlayer.MediaStatus.InvalidMedia:
            self._on_player_error(self.player.error(), self.player.errorString())

    def _on_player_error(self, error: QMediaPlayer.Error, error_string: str = "") -> None:
        if error == QMediaPlayer.Error.NoError:
            detail = "当前系统无法读取该媒体文件；建议转换为 H.264/AAC MP4 后重试。"
        else:
            details = {
                QMediaPlayer.Error.ResourceError: "无法读取文件，请确认文件仍存在且没有被其他程序占用。",
                QMediaPlayer.Error.FormatError: "当前系统不支持该视频编码；建议转换为 H.264/AAC MP4 后重试。",
                QMediaPlayer.Error.NetworkError: "读取媒体时发生连接错误，请确认文件位于可访问的本地磁盘。",
                QMediaPlayer.Error.AccessDeniedError: "没有权限读取该文件，请检查文件权限后重试。",
            }
            detail = details.get(error, "播放器无法打开该文件；建议检查文件完整性或转换视频格式。")
        self._pending_preview_position = None
        self._preview_autoplay = False
        name = self._preview_source_name or "所选素材"
        self.editor_status.setText(f"预览失败：{name} · {detail}")
        self.editor_status.setToolTip(error_string)

    def _on_playback_state(self, state: QMediaPlayer.PlaybackState) -> None:
        self.preview_surface.set_playing(state == QMediaPlayer.PlaybackState.PlayingState)
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setText("暂停")
            self.play_button.setIcon(svg_icon("pause"))
            if self._preview_source_name:
                self.editor_status.setText(f"正在播放：{self._preview_source_name}")
        else:
            self.play_button.setText("播放")
            self.play_button.setIcon(svg_icon("play"))
