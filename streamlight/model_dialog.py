from __future__ import annotations

import threading
import time
from collections import deque
from pathlib import Path

from PySide6.QtCore import QThread, QUrl, Qt, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .icons import svg_icon
from .model_manager import (
    ModelDownloadCancelled,
    ModelDownloader,
    ModelManager,
    ModelSpec,
    format_bytes,
)
from .styles import HEADER_ACTION_HEIGHT


class TransferRateMeter:
    """Small sliding-window speed/ETA estimator shared by download and hash stages."""

    def __init__(self, window_seconds: float = 3.0) -> None:
        self.window_seconds = max(0.5, float(window_seconds))
        self._phase = ""
        self._samples: deque[tuple[float, int]] = deque()

    def reset(self) -> None:
        self._phase = ""
        self._samples.clear()

    def update(
        self,
        phase: str,
        completed: int,
        total: int,
        *,
        now: float | None = None,
    ) -> tuple[float, float | None]:
        timestamp = time.monotonic() if now is None else float(now)
        done = max(0, int(completed))
        if phase != self._phase or (self._samples and done < self._samples[-1][1]):
            self._phase = phase
            self._samples.clear()
        self._samples.append((timestamp, done))
        while len(self._samples) > 2 and timestamp - self._samples[0][0] > self.window_seconds:
            self._samples.popleft()
        speed = 0.0
        if len(self._samples) >= 2:
            elapsed = self._samples[-1][0] - self._samples[0][0]
            delta = self._samples[-1][1] - self._samples[0][1]
            if elapsed > 0 and delta >= 0:
                speed = delta / elapsed
        remaining = max(0, int(total) - done)
        eta = remaining / speed if speed > 0 else None
        return speed, eta


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "计算中"
    value = max(0, round(seconds))
    hours, remainder = divmod(value, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}时{minutes:02d}分"
    if minutes:
        return f"{minutes}分{secs:02d}秒"
    return f"{secs}秒"


class ModelDownloadWorker(QThread):
    progress = Signal(object, object, str)
    completed = Signal()
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, manager: ModelManager, spec: ModelSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.downloader = ModelDownloader(manager, self.progress.emit)
        self.spec = spec

    def cancel(self) -> None:
        self.downloader.cancel()

    def run(self) -> None:
        try:
            self.downloader.download(self.spec)
            self.completed.emit()
        except ModelDownloadCancelled:
            self.cancelled.emit()
        except BaseException as error:
            self.failed.emit(str(error))


class ModelVerifyWorker(QThread):
    progress = Signal(object, object, str)
    completed = Signal()
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, manager: ModelManager, spec: ModelSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.spec = spec
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    def run(self) -> None:
        try:
            self.manager.verify_and_record(
                self.spec,
                lambda done, total, name: self.progress.emit(done, total, f"校验 · {name}"),
                self._cancelled.is_set,
            )
            self.completed.emit()
        except ModelDownloadCancelled:
            self.cancelled.emit()
        except BaseException as error:
            self.failed.emit(str(error))


class ModelManagerDialog(QDialog):
    models_changed = Signal()

    def __init__(self, manager: ModelManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self._thread: ModelDownloadWorker | ModelVerifyWorker | None = None
        self._active_spec: ModelSpec | None = None
        self._pending_close = False
        self._rate_meter = TransferRateMeter()
        self.setWindowTitle("本地模型管理")
        self.setMinimumSize(1030, 640)
        self.resize(1080, 680)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 15, 16, 15)
        root.setSpacing(11)

        header = QFrame(objectName="ModelManagerHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 11, 14, 11)
        title_box = QVBoxLayout()
        title_box.addWidget(QLabel("本地智能模型", objectName="ModelManagerTitle"))
        title_box.addWidget(
            QLabel("缺失模型会禁用对应能力；下载完成并校验后才能启用。", objectName="Muted")
        )
        header_layout.addLayout(title_box, 1)
        self.summary_label = QLabel(objectName="ModelSummary")
        self.summary_label.setFixedHeight(HEADER_ACTION_HEIGHT)
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.summary_label, 0, Qt.AlignmentFlag.AlignVCenter)
        self.open_dir_button = QPushButton("打开模型目录")
        self.open_dir_button.setFixedHeight(HEADER_ACTION_HEIGHT)
        self.open_dir_button.setIcon(svg_icon("folder-open"))
        self.open_dir_button.clicked.connect(self.open_model_directory)
        header_layout.addWidget(self.open_dir_button, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(header)

        storage_row = QHBoxLayout()
        storage_row.addWidget(QLabel("存储位置", objectName="SubsectionTitle"))
        path_label = QLabel(str(self.manager.root), objectName="ModelPath")
        path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        storage_row.addWidget(path_label, 1)
        root.addLayout(storage_row)

        self.table = QTableWidget(0, 6, objectName="ModelTable")
        self.table.setHorizontalHeaderLabels(["状态", "模型", "用途", "大小", "版本与来源", "操作"])
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self.table, 1)

        progress_panel = QFrame(objectName="ModelProgressPanel")
        progress_layout = QVBoxLayout(progress_panel)
        progress_layout.setContentsMargins(12, 9, 12, 9)
        progress_top = QHBoxLayout()
        self.progress_title = QLabel("没有正在运行的模型任务", objectName="ModelProgressTitle")
        self.progress_detail = QLabel(objectName="Muted")
        progress_top.addWidget(self.progress_title)
        progress_top.addWidget(self.progress_detail, 1)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setIcon(svg_icon("cancel"))
        self.cancel_button.clicked.connect(self.cancel_active)
        self.cancel_button.hide()
        progress_top.addWidget(self.cancel_button)
        progress_layout.addLayout(progress_top)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        root.addWidget(progress_panel)

        note = QLabel(
            "下载使用模型来源的 HTTPS 地址；取消会中断连接并保留 .part。校验在后台每次读取 1 MB，计算 SHA-256；已配置官方摘要的文件会严格比较，异常文件保留为 .corrupt。全程不上传模型内容。"
        )
        note.setObjectName("Hint")
        note.setWordWrap(True)
        root.addWidget(note)

    def refresh(self) -> None:
        ready, total = self.manager.summary()
        self.summary_label.setText(f"已安装 {ready}/{total}")
        self.summary_label.setProperty("kind", "success" if ready == total else "warning")
        self.summary_label.style().unpolish(self.summary_label)
        self.summary_label.style().polish(self.summary_label)
        self.table.setRowCount(len(self.manager.registry))
        busy = self._thread is not None
        for row, spec in enumerate(self.manager.registry):
            state = self.manager.state(spec)
            status = QLabel(state.label, objectName="ModelState")
            status.setProperty("kind", state.code)
            status.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status.setFixedHeight(30)
            status.setToolTip(state.detail)
            status_container = QWidget()
            status_layout = QVBoxLayout(status_container)
            status_layout.setContentsMargins(4, 3, 4, 3)
            status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_layout.addWidget(status)
            self.table.setCellWidget(row, 0, status_container)

            name_box = QWidget()
            name_layout = QVBoxLayout(name_box)
            name_layout.setContentsMargins(4, 3, 4, 3)
            name_layout.setSpacing(1)
            name_layout.addWidget(QLabel(spec.name, objectName="ModelName"))
            description = QLabel(spec.description, objectName="ModelDescription")
            description.setWordWrap(True)
            name_layout.addWidget(description)
            self.table.setCellWidget(row, 1, name_box)
            self.table.setItem(row, 2, QTableWidgetItem(spec.category))
            size_text = format_bytes(spec.total_size)
            if state.downloaded_size and not state.ready:
                size_text = f"{format_bytes(state.downloaded_size)} / {size_text}"
            self.table.setItem(row, 3, QTableWidgetItem(size_text))

            source_box = QWidget()
            source_layout = QVBoxLayout(source_box)
            source_layout.setContentsMargins(4, 3, 4, 3)
            source_layout.setSpacing(1)
            source_layout.addWidget(QLabel(spec.version, objectName="ModelVersion"))
            source_button = QPushButton(spec.source_name, objectName="LinkButton")
            source_button.setToolTip(f"{spec.license_name}\n{spec.source_url}")
            source_button.clicked.connect(lambda _checked=False, url=spec.source_url: QDesktopServices.openUrl(QUrl(url)))
            source_layout.addWidget(source_button)
            self.table.setCellWidget(row, 4, source_box)

            actions = QWidget()
            action_layout = QHBoxLayout(actions)
            action_layout.setContentsMargins(3, 3, 3, 3)
            action_layout.setSpacing(5)
            download = QPushButton("继续" if state.code == "partial" else "修复" if state.code == "corrupt" else "下载")
            download.setIcon(svg_icon("download"))
            download.setEnabled(not busy and state.code in {"missing", "partial", "corrupt"})
            download.clicked.connect(lambda _checked=False, model=spec: self.start_download(model))
            verify = QPushButton("校验")
            verify.setIcon(svg_icon("check"))
            verify.setEnabled(not busy and state.code in {"installed", "unverified"})
            verify.clicked.connect(lambda _checked=False, model=spec: self.start_verify(model))
            remove = QPushButton("删除")
            remove.setIcon(svg_icon("trash"))
            remove.setObjectName("DangerButton")
            remove.setEnabled(not busy and state.downloaded_size > 0)
            remove.clicked.connect(lambda _checked=False, model=spec: self.remove_model(model))
            action_layout.addWidget(download)
            action_layout.addWidget(verify)
            action_layout.addWidget(remove)
            self.table.setCellWidget(row, 5, actions)
            self.table.setRowHeight(row, 72)

    def start_download(self, spec: ModelSpec) -> None:
        if self._thread:
            return
        if spec.total_size >= 1024**3:
            answer = QMessageBox.question(
                self,
                "下载大型模型",
                f"{spec.name} 大小约 {format_bytes(spec.total_size)}。确定开始下载吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        worker = ModelDownloadWorker(self.manager, spec, self)
        worker.progress.connect(self._on_progress)
        worker.completed.connect(lambda: self._task_succeeded("下载并校验完成"))
        worker.cancelled.connect(lambda: self._task_message("下载已取消，可稍后继续"))
        worker.failed.connect(lambda detail: self._task_failed("模型下载失败", detail))
        self._start_worker(worker, spec, "正在下载")

    def start_verify(self, spec: ModelSpec) -> None:
        if self._thread:
            return
        worker = ModelVerifyWorker(self.manager, spec, self)
        worker.progress.connect(self._on_progress)
        worker.completed.connect(lambda: self._task_succeeded("完整性校验完成"))
        worker.cancelled.connect(lambda: self._task_message("模型校验已取消，可稍后重新校验"))
        worker.failed.connect(lambda detail: self._task_failed("模型校验失败", detail))
        self._start_worker(worker, spec, "正在校验")

    def _start_worker(self, worker, spec: ModelSpec, action: str) -> None:
        worker.finished.connect(self._on_worker_finished)
        self._thread = worker
        self._active_spec = spec
        self._rate_meter.reset()
        self.progress_title.setText(f"{action}：{spec.name}")
        self.progress_detail.clear()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.cancel_button.show()
        self.refresh()
        worker.start()

    def _on_progress(self, completed: int, total: int, file_name: str) -> None:
        percent = completed / max(1, total)
        self.progress_bar.setValue(round(max(0.0, min(1.0, percent)) * 1000))
        phase, separator, raw_name = file_name.partition(" · ")
        phase = phase if separator else "处理"
        name = Path(raw_name if separator else file_name).name
        speed, eta = self._rate_meter.update(phase, completed, total)
        speed_text = f"{format_bytes(round(speed))}/s" if speed > 0 else "测速中"
        if self._active_spec:
            self.progress_title.setText(f"正在{phase}：{self._active_spec.name}")
        self.progress_detail.setText(
            f"{format_bytes(completed)} / {format_bytes(total)} · {speed_text} · 剩余 {format_duration(eta)} · {name}"
        )

    def _task_succeeded(self, message: str) -> None:
        self.progress_bar.setValue(1000)
        self._task_message(message)

    def _task_message(self, message: str) -> None:
        self.progress_title.setText(message)

    def _task_failed(self, title: str, detail: str) -> None:
        self.progress_title.setText(title)
        QMessageBox.warning(self, title, detail)

    def _on_worker_finished(self) -> None:
        thread = self._thread
        if thread is None:
            return
        thread.wait()
        self._thread = None
        self._active_spec = None
        self.cancel_button.hide()
        self.cancel_button.setEnabled(True)
        self.refresh()
        self.models_changed.emit()
        thread.deleteLater()
        if self._pending_close:
            self.accept()

    def cancel_active(self) -> None:
        if isinstance(self._thread, (ModelDownloadWorker, ModelVerifyWorker)):
            self.progress_title.setText("正在取消模型任务…")
            self.cancel_button.setEnabled(False)
            self._thread.cancel()

    def remove_model(self, spec: ModelSpec) -> None:
        answer = QMessageBox.question(
            self,
            "删除本地模型",
            f"确定删除“{spec.name}”的本地文件吗？以后可以重新下载。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.manager.remove(spec)
        except BaseException as error:
            QMessageBox.warning(self, "删除失败", str(error))
            return
        self.progress_title.setText(f"已删除：{spec.name}")
        self.refresh()
        self.models_changed.emit()

    def open_model_directory(self) -> None:
        self.manager.root.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.manager.root)))

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._thread:
            answer = QMessageBox.question(
                self,
                "模型任务仍在运行",
                "关闭管理界面将取消当前模型任务。确定继续吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._pending_close = True
            self.cancel_active()
            event.ignore()
            return
        event.accept()

    def reject(self) -> None:
        if self._thread:
            answer = QMessageBox.question(
                self,
                "模型任务仍在运行",
                "退出模型管理将取消当前任务并保留可续传文件。确定继续吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._pending_close = True
                self.cancel_active()
            return
        super().reject()
