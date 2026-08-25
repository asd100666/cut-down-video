from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal, Slot

from .engine import DownloadEngine
from .errors import UserCancelled, friendly_error
from .models import DownloadRequest, MediaSummary, ProgressUpdate


class BaseWorker(QObject):
    progress = Signal(object)
    log = Signal(str, str)
    failed = Signal(str, str)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, request: DownloadRequest) -> None:
        super().__init__()
        self.engine = DownloadEngine(
            request,
            progress_callback=self.progress.emit,
            log_callback=self.log.emit,
        )

    @Slot()
    def cancel(self) -> None:
        self.engine.cancel()

    def _handle_error(self, error: BaseException) -> None:
        if isinstance(error, UserCancelled) or self.engine.is_cancelled:
            self.cancelled.emit()
        else:
            title, detail = friendly_error(error)
            self.failed.emit(title, detail)


class AnalyzeWorker(BaseWorker):
    analyzed = Signal(object)

    @Slot()
    def run(self) -> None:
        try:
            summary: MediaSummary = self.engine.analyze()
            self.analyzed.emit(summary)
        except BaseException as error:
            self._handle_error(error)
        finally:
            self.finished.emit()


class DownloadWorker(BaseWorker):
    downloaded = Signal(str)

    @Slot()
    def run(self) -> None:
        try:
            output_dir = self.engine.download()
            self.downloaded.emit(output_dir)
        except BaseException as error:
            self._handle_error(error)
        finally:
            self.finished.emit()


class BatchWorkerBase(QObject):
    item_started = Signal(int, str)
    item_progress = Signal(int, object)
    item_failed = Signal(int, str, str, str)
    log = Signal(str, str)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, jobs: list[tuple[int, DownloadRequest]]) -> None:
        super().__init__()
        self.jobs = jobs
        self._cancel_event = threading.Event()
        self._active_engine: DownloadEngine | None = None

    @Slot()
    def cancel(self) -> None:
        self._cancel_event.set()
        if self._active_engine:
            self._active_engine.cancel()

    def _engine_for(self, index: int, request: DownloadRequest) -> DownloadEngine:
        engine = DownloadEngine(
            request,
            progress_callback=lambda update: self.item_progress.emit(index, update),
            log_callback=self.log.emit,
        )
        self._active_engine = engine
        return engine

    def _is_cancelled(self, error: BaseException | None = None) -> bool:
        return (
            self._cancel_event.is_set()
            or isinstance(error, UserCancelled)
            or bool(self._active_engine and self._active_engine.is_cancelled)
        )

    def _emit_item_error(self, index: int, url: str, error: BaseException) -> None:
        title, detail = friendly_error(error)
        self.item_failed.emit(index, url, title, detail)


class BatchAnalyzeWorker(BatchWorkerBase):
    item_analyzed = Signal(int, str, object)

    @Slot()
    def run(self) -> None:
        try:
            for index, request in self.jobs:
                if self._cancel_event.is_set():
                    self.cancelled.emit()
                    return
                self.item_started.emit(index, request.url)
                try:
                    summary = self._engine_for(index, request).analyze()
                    self.item_analyzed.emit(index, request.url, summary)
                except BaseException as error:
                    if self._is_cancelled(error):
                        self.cancelled.emit()
                        return
                    self._emit_item_error(index, request.url, error)
                finally:
                    self._active_engine = None
        finally:
            self.finished.emit()


class BatchDownloadWorker(BatchWorkerBase):
    item_downloaded = Signal(int, str, str)

    @Slot()
    def run(self) -> None:
        try:
            for index, request in self.jobs:
                if self._cancel_event.is_set():
                    self.cancelled.emit()
                    return
                self.item_started.emit(index, request.url)
                try:
                    output_dir = self._engine_for(index, request).download()
                    self.item_downloaded.emit(index, request.url, output_dir)
                except BaseException as error:
                    if self._is_cancelled(error):
                        self.cancelled.emit()
                        return
                    self._emit_item_error(index, request.url, error)
                finally:
                    self._active_engine = None
        finally:
            self.finished.emit()
