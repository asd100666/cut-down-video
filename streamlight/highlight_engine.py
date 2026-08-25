from __future__ import annotations

import math
import os
import re
import subprocess
import threading
from dataclasses import dataclass
from typing import Callable, Iterable

from .dependencies import locate_ffmpeg
from .editor_engine import ExportCancelled
from .editor_models import AnalysisEvidence, EditProject, SubtitleCue, TimelineClip, new_id
from .model_manager import ModelManager
from .offline_intelligence import OfflineIntelligenceAnalyzer


HighlightProgress = Callable[[float, str], None]


@dataclass(frozen=True, slots=True)
class SceneBoundary:
    time: float
    score: float
    reason: str = "场景切换"


@dataclass(frozen=True, slots=True)
class HighlightRange:
    start: float
    end: float
    score: float
    reason: str

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def plan_highlight_ranges(
    duration: float,
    boundaries: Iterable[SceneBoundary],
    target_duration: float,
    max_clip_duration: float,
) -> list[HighlightRange]:
    """Create chronological, non-overlapping ranges spread across the full source."""

    source_duration = max(0.0, float(duration))
    if source_duration < 0.04:
        return []
    target = max(0.04, min(source_duration, float(target_duration)))
    maximum = max(0.2, float(max_clip_duration))
    clip_count = max(1, math.ceil(target / maximum))
    clip_length = target / clip_count
    bucket_length = source_duration / clip_count
    points = sorted(
        (
            SceneBoundary(
                max(0.0, min(source_duration, item.time)),
                max(0.0, item.score),
                item.reason,
            )
            for item in boundaries
            if 0.0 < item.time < source_duration
        ),
        key=lambda item: item.time,
    )

    ranges: list[HighlightRange] = []
    for index in range(clip_count):
        bucket_start = index * bucket_length
        bucket_end = source_duration if index == clip_count - 1 else (index + 1) * bucket_length
        available = max(0.04, bucket_end - bucket_start)
        length = min(clip_length, available)
        candidates = [item for item in points if bucket_start <= item.time < bucket_end]
        if candidates:
            boundary = max(candidates, key=lambda item: item.score)
            start = max(bucket_start, min(boundary.time, bucket_end - length))
            score = boundary.score
            reason = boundary.reason
        else:
            start = bucket_start + (available - length) / 2
            score = 0.0
            reason = "时间覆盖"
        end = min(source_duration, start + length)
        if ranges and start < ranges[-1].end:
            start = ranges[-1].end
            end = min(source_duration, start + length)
        if end - start >= 0.04:
            ranges.append(HighlightRange(start, end, score, reason))
    return ranges


class LongVideoHighlightAnalyzer:
    def __init__(
        self,
        progress_callback: HighlightProgress | None = None,
        model_manager: ModelManager | None = None,
    ) -> None:
        self.progress_callback = progress_callback or (lambda _percent, _message: None)
        self.model_manager = model_manager or ModelManager()
        self._cancel_event = threading.Event()
        self._process: subprocess.Popen[str] | None = None
        self._intelligence: OfflineIntelligenceAnalyzer | None = None
        self.last_evidence: list[AnalysisEvidence] = []
        self.last_subtitles: list[SubtitleCue] = []
        self.last_warnings: list[str] = []

    def cancel(self) -> None:
        self._cancel_event.set()
        if self._intelligence:
            self._intelligence.cancel()
        if self._process and self._process.poll() is None:
            self._process.terminate()

    def _check_cancelled(self) -> None:
        if self._cancel_event.is_set():
            raise ExportCancelled("自动精华分析已取消")

    @staticmethod
    def _creation_flags() -> int:
        return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

    def detect_scenes(self, path: str, threshold: float) -> list[SceneBoundary]:
        ffmpeg, _source = locate_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("未找到 FFmpeg，无法分析长视频场景")
        scene_threshold = max(0.05, min(0.95, float(threshold)))
        filter_graph = f"scale=320:-2,select=gt(scene\\,{scene_threshold:.4f}),metadata=print"
        command = [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-i",
            path,
            "-an",
            "-sn",
            "-dn",
            "-vf",
            filter_graph,
            "-fps_mode",
            "vfr",
            "-f",
            "null",
            "-",
        ]
        self._check_cancelled()
        self._process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=self._creation_flags(),
        )
        stdout, stderr = self._process.communicate()
        return_code = self._process.returncode
        self._process = None
        self._check_cancelled()
        details = stderr or stdout or ""
        if return_code:
            tail = "\n".join(details.strip().splitlines()[-10:])
            raise RuntimeError(f"场景分析失败：\n{tail}")

        boundaries: list[SceneBoundary] = []
        pending_time: float | None = None
        for line in details.splitlines():
            time_match = re.search(r"pts_time:([0-9]+(?:\.[0-9]+)?)", line)
            if time_match:
                pending_time = float(time_match.group(1))
            score_match = re.search(r"lavfi\.scene_score=([0-9]+(?:\.[0-9]+)?)", line)
            if score_match and pending_time is not None:
                boundary = SceneBoundary(pending_time, float(score_match.group(1)))
                if not boundaries or boundary.time - boundaries[-1].time >= 0.25:
                    boundaries.append(boundary)
                elif boundary.score > boundaries[-1].score:
                    boundaries[-1] = boundary
                pending_time = None
        return boundaries

    def analyze(
        self,
        project: EditProject,
        asset_ids: list[str],
        *,
        target_duration: float,
        max_clip_duration: float,
        scene_threshold: float,
        speech_enabled: bool = False,
        face_enabled: bool = False,
        semantic_enabled: bool = False,
    ) -> list[TimelineClip]:
        assets = [project.asset(asset_id) for asset_id in asset_ids]
        assets = [asset for asset in assets if asset.kind == "video" and asset.duration > 0]
        if not assets:
            raise ValueError("没有可用于自动精华的视频素材")
        total_source_duration = sum(asset.duration for asset in assets)
        target_total = max(0.04, min(total_source_duration, float(target_duration)))
        clips: list[TimelineClip] = []
        self.last_evidence = []
        self.last_subtitles = []
        self.last_warnings = []
        remaining_target = target_total
        remaining_source = total_source_duration

        for asset_index, asset in enumerate(assets):
            self._check_cancelled()
            analysis_start = 5.0 + 55.0 * asset_index / len(assets)
            self.progress_callback(analysis_start, f"正在分析场景 {asset_index + 1}/{len(assets)}：{asset.name}")
            if asset_index == len(assets) - 1:
                asset_target = remaining_target
            else:
                asset_target = remaining_target * asset.duration / max(asset.duration, remaining_source)
            asset_target = max(0.04, min(asset.duration, asset_target))
            boundaries = self.detect_scenes(asset.path, scene_threshold)
            clip_count = max(1, math.ceil(asset_target / max(0.2, max_clip_duration)))
            bucket = asset.duration / clip_count
            intelligent_times = {
                max(0.0, min(asset.duration - 0.01, item.time)) for item in boundaries
            }
            intelligence_enabled = speech_enabled or face_enabled or semantic_enabled
            if intelligence_enabled:
                for bucket_index in range(clip_count):
                    for fraction in (1 / 3, 2 / 3):
                        intelligent_times.add(min(asset.duration - 0.01, (bucket_index + fraction) * bucket))
            sample_scores: dict[float, float] = {}
            if intelligence_enabled:
                base_progress = 10.0 + 70.0 * asset_index / len(assets)
                span = 70.0 / len(assets)
                self._intelligence = OfflineIntelligenceAnalyzer(
                    self.model_manager,
                    lambda percent, message, start=base_progress, width=span: self.progress_callback(
                        min(92.0, start + width * percent / 100.0), message
                    ),
                )
                intelligence = self._intelligence.analyze(
                    asset,
                    sorted(intelligent_times),
                    speech_enabled=speech_enabled,
                    face_enabled=face_enabled,
                    semantic_enabled=semantic_enabled,
                )
                self._intelligence = None
                self.last_evidence.extend(intelligence.evidence)
                self.last_subtitles.extend(intelligence.subtitles)
                self.last_warnings.extend(intelligence.warnings)
                sample_scores = intelligence.sample_scores

            scene_scores = {round(item.time, 4): item.score for item in boundaries}
            candidates: list[SceneBoundary] = []
            for time in sorted(intelligent_times):
                scene_score = scene_scores.get(round(time, 4), 0.0)
                intelligence_score = sample_scores.get(time, 0.0)
                if intelligence_enabled:
                    combined = min(1.0, scene_score * 0.5 + intelligence_score * 0.5)
                    reason = "智能证据" if intelligence_score > scene_score else "场景切换"
                else:
                    combined = scene_score
                    reason = "场景切换" if scene_score > 0 else "时间覆盖"
                candidates.append(SceneBoundary(time, combined, reason))
            ranges = plan_highlight_ranges(
                asset.duration,
                candidates,
                asset_target,
                max_clip_duration,
            )
            for range_index, item in enumerate(ranges, start=1):
                related = [
                    evidence
                    for evidence in self.last_evidence
                    if evidence.asset_id == asset.id
                    and evidence.end >= item.start - 0.01
                    and evidence.start <= item.end + 0.01
                ]
                evidence_ids = [evidence.id for evidence in related]
                best_evidence = max((evidence.score for evidence in related), default=0.0)
                clips.append(
                    TimelineClip(
                        id=new_id("clip"),
                        asset_id=asset.id,
                        name=f"{asset.name} · 精华 {range_index:02d}",
                        in_point=item.start,
                        out_point=item.end,
                        selection_score=max(item.score, best_evidence),
                        selection_reason=item.reason,
                        evidence_ids=evidence_ids,
                    )
                )
            remaining_target = max(0.0, remaining_target - sum(item.duration for item in ranges))
            remaining_source = max(0.0, remaining_source - asset.duration)

        self.progress_callback(96.0, f"已生成 {len(clips)} 个可编辑精华镜头")
        return clips
