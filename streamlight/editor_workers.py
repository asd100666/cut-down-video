from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from .editor_engine import EditorExporter, ExportCancelled, probe_media
from .highlight_engine import LongVideoHighlightAnalyzer
from .model_manager import ModelManager
from .narration_engine import LocalNarrationGenerator, NarrationSynthesizer
from .offline_intelligence import OfflineIntelligenceAnalyzer


class MediaProbeWorker(QObject):
    item_started = Signal(str)
    item_ready = Signal(object)
    item_failed = Signal(str, str)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, paths: list[str]) -> None:
        super().__init__()
        self.paths = paths
        self._cancel_event = threading.Event()

    @Slot()
    def cancel(self) -> None:
        self._cancel_event.set()

    @Slot()
    def run(self) -> None:
        try:
            for path in self.paths:
                if self._cancel_event.is_set():
                    self.cancelled.emit()
                    return
                self.item_started.emit(path)
                try:
                    self.item_ready.emit(probe_media(path))
                except BaseException as error:
                    self.item_failed.emit(path, str(error))
        finally:
            self.finished.emit()


class EditorExportWorker(QObject):
    progress = Signal(float, str)
    completed = Signal(str)
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, project, output_path: str | Path) -> None:
        super().__init__()
        self.project = project.clone()
        self.output_path = str(output_path)
        self.exporter = EditorExporter(self.progress.emit)

    @Slot()
    def cancel(self) -> None:
        self.exporter.cancel()

    @Slot()
    def run(self) -> None:
        try:
            output = self.exporter.export(self.project, self.output_path)
            self.completed.emit(str(output))
        except ExportCancelled:
            self.cancelled.emit()
        except BaseException as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()


class LongVideoHighlightWorker(QObject):
    progress = Signal(float, str)
    completed = Signal(object, object)
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(
        self,
        project,
        asset_ids: list[str],
        settings: dict,
        model_manager: ModelManager | None = None,
    ) -> None:
        super().__init__()
        self.project = project.clone()
        self.asset_ids = list(asset_ids)
        self.settings = dict(settings)
        self.analyzer = LongVideoHighlightAnalyzer(self.progress.emit, model_manager)

    @Slot()
    def cancel(self) -> None:
        self.analyzer.cancel()

    @Slot()
    def run(self) -> None:
        try:
            clips = self.analyzer.analyze(
                self.project,
                self.asset_ids,
                target_duration=float(self.settings["target_duration"]),
                max_clip_duration=float(self.settings["max_clip_duration"]),
                scene_threshold=float(self.settings["scene_threshold"]),
                speech_enabled=bool(self.settings.get("speech_enabled", False)),
                face_enabled=bool(self.settings.get("face_enabled", False)),
                semantic_enabled=bool(self.settings.get("semantic_enabled", False)),
            )
            result_settings = dict(self.settings)
            result_settings["_analysis_evidence"] = list(self.analyzer.last_evidence)
            result_settings["_subtitle_cues"] = list(self.analyzer.last_subtitles)
            result_settings["_warnings"] = list(self.analyzer.last_warnings)
            self.completed.emit(clips, result_settings)
        except ExportCancelled:
            self.cancelled.emit()
        except BaseException as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()


class SceneSplitWorker(QObject):
    progress = Signal(float, str)
    completed = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, project, clip_index: int, threshold: float, min_duration: float) -> None:
        super().__init__()
        self.project = project.clone()
        self.clip_index = clip_index
        self.threshold = threshold
        self.min_duration = max(0.2, float(min_duration))
        self.analyzer = LongVideoHighlightAnalyzer(self.progress.emit)

    @Slot()
    def cancel(self) -> None:
        self.analyzer.cancel()

    @Slot()
    def run(self) -> None:
        try:
            clip = self.project.clips[self.clip_index]
            asset = self.project.asset(clip.asset_id)
            self.progress.emit(5.0, f"正在检测场景：{clip.name}")
            boundaries = self.analyzer.detect_scenes(asset.path, self.threshold)
            points: list[float] = []
            previous = clip.in_point
            for item in boundaries:
                if item.time <= clip.in_point or item.time >= clip.out_point:
                    continue
                if item.time - previous < self.min_duration or clip.out_point - item.time < self.min_duration:
                    continue
                points.append(item.time)
                previous = item.time
            self.progress.emit(100.0, f"检测到 {len(points)} 个场景边界")
            self.completed.emit(points)
        except ExportCancelled:
            self.cancelled.emit()
        except BaseException as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()


class SpeechRecognitionWorker(QObject):
    progress = Signal(float, str)
    completed = Signal(str, object, object)
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, project, asset_id: str, model_manager: ModelManager) -> None:
        super().__init__()
        self.project = project.clone()
        self.asset_id = asset_id
        self.analyzer = OfflineIntelligenceAnalyzer(model_manager, self.progress.emit)

    @Slot()
    def cancel(self) -> None:
        self.analyzer.cancel()

    @Slot()
    def run(self) -> None:
        try:
            asset = self.project.asset(self.asset_id)
            self.progress.emit(2.0, f"正在提取音频：{asset.name}")
            subtitles, evidence = self.analyzer.transcribe(asset)
            self.progress.emit(100.0, f"识别完成：{len(subtitles)} 条字幕")
            self.completed.emit(asset.id, subtitles, evidence)
        except ExportCancelled:
            self.cancelled.emit()
        except BaseException as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()


class NarrationWorker(QObject):
    progress = Signal(float, str)
    completed = Signal(object, str, float, float)
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(
        self,
        text: str,
        output_path: str | Path,
        rate: int,
        start_time: float,
        volume: float,
    ) -> None:
        super().__init__()
        self.text = text
        self.output_path = output_path
        self.rate = rate
        self.start_time = start_time
        self.volume = volume
        self.synthesizer = NarrationSynthesizer()

    @Slot()
    def cancel(self) -> None:
        self.synthesizer.cancel()

    @Slot()
    def run(self) -> None:
        try:
            self.progress.emit(10.0, "正在调用本机离线语音生成解说")
            asset = self.synthesizer.synthesize(self.text, self.output_path, self.rate)
            self.progress.emit(100.0, "解说音频生成完成")
            self.completed.emit(asset, self.text, self.start_time, self.volume)
        except ExportCancelled:
            self.cancelled.emit()
        except BaseException as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()


class NarrationDraftWorker(QObject):
    progress = Signal(float, str)
    completed = Signal(str, object)
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(
        self,
        project,
        model_manager: ModelManager,
        style: str,
        max_chars: int,
    ) -> None:
        super().__init__()
        self.project = project.clone()
        self.style = style
        self.max_chars = max_chars
        self.generator = LocalNarrationGenerator(model_manager, self.progress.emit)

    @Slot()
    def cancel(self) -> None:
        self.generator.cancel()

    @Slot()
    def run(self) -> None:
        try:
            text, metadata = self.generator.generate(self.project, self.style, self.max_chars)
            self.completed.emit(text, metadata)
        except ExportCancelled:
            self.cancelled.emit()
        except BaseException as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()
