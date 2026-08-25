from __future__ import annotations

import copy
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".avi",
    ".m4v",
    ".ts",
    ".mts",
    ".m2ts",
}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma"}


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def format_timecode(seconds: float) -> str:
    total_ms = max(0, round(float(seconds) * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    return f"{minutes:02d}:{secs:02d}.{millis:03d}"


@dataclass(slots=True)
class MediaAsset:
    id: str
    path: str
    name: str
    kind: str
    duration: float
    width: int = 0
    height: int = 0
    fps: float = 0.0
    has_audio: bool = False

    @classmethod
    def create(
        cls,
        path: str | Path,
        *,
        kind: str,
        duration: float,
        width: int = 0,
        height: int = 0,
        fps: float = 0.0,
        has_audio: bool = False,
    ) -> "MediaAsset":
        media_path = Path(path).resolve()
        return cls(
            id=new_id("asset"),
            path=str(media_path),
            name=media_path.stem,
            kind=kind,
            duration=max(0.0, float(duration)),
            width=max(0, int(width)),
            height=max(0, int(height)),
            fps=max(0.0, float(fps)),
            has_audio=bool(has_audio),
        )


@dataclass(slots=True)
class TimelineClip:
    id: str
    asset_id: str
    name: str
    in_point: float
    out_point: float
    volume: float = 1.0
    muted: bool = False
    locked: bool = False
    selection_score: float = 0.0
    selection_reason: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    transition: str = "cut"
    transition_duration: float = 0.0

    @property
    def duration(self) -> float:
        return max(0.0, self.out_point - self.in_point)


@dataclass(slots=True)
class AudioTrack:
    id: str
    asset_id: str
    name: str
    start_time: float
    in_point: float
    out_point: float
    volume: float = 0.65
    muted: bool = False

    @property
    def duration(self) -> float:
        return max(0.0, self.out_point - self.in_point)


@dataclass(slots=True)
class SubtitleCue:
    id: str
    asset_id: str
    start: float
    end: float
    text: str
    confidence: float = 0.0
    enabled: bool = True


@dataclass(slots=True)
class AnalysisEvidence:
    id: str
    kind: str
    asset_id: str
    start: float
    end: float
    score: float
    label: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EditProject:
    name: str = "未命名剪辑"
    id: str = field(default_factory=lambda: new_id("project"))
    schema_version: int = 3
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    assets: list[MediaAsset] = field(default_factory=list)
    clips: list[TimelineClip] = field(default_factory=list)
    audio_tracks: list[AudioTrack] = field(default_factory=list)
    subtitle_cues: list[SubtitleCue] = field(default_factory=list)
    analysis_evidence: list[AnalysisEvidence] = field(default_factory=list)
    source_recipe: str = "manual"
    generation_settings: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    @property
    def duration(self) -> float:
        ranges = self.clip_timeline_ranges()
        return ranges[-1][2] if ranges else 0.0

    def transition_overlap(self, index: int) -> float:
        if index <= 0 or index >= len(self.clips):
            return 0.0
        clip = self.clips[index]
        if clip.transition == "cut":
            return 0.0
        previous = self.clips[index - 1]
        return max(0.0, min(clip.transition_duration, previous.duration / 2, clip.duration / 2))

    def clip_timeline_ranges(self) -> list[tuple[TimelineClip, float, float]]:
        elapsed = 0.0
        ranges: list[tuple[TimelineClip, float, float]] = []
        for index, clip in enumerate(self.clips):
            elapsed = max(0.0, elapsed - self.transition_overlap(index))
            end = elapsed + clip.duration
            ranges.append((clip, elapsed, end))
            elapsed = end
        return ranges

    def timeline_subtitle_instances(self) -> list[tuple[int, float, float, SubtitleCue]]:
        instances: list[tuple[int, float, float, SubtitleCue]] = []
        for clip, timeline_start, _timeline_end in self.clip_timeline_ranges():
            for cue_index, cue in enumerate(self.subtitle_cues):
                if not cue.enabled or cue.asset_id != clip.asset_id:
                    continue
                overlap_start = max(cue.start, clip.in_point)
                overlap_end = min(cue.end, clip.out_point)
                if overlap_end - overlap_start < 0.01:
                    continue
                start = timeline_start + overlap_start - clip.in_point
                end = timeline_start + overlap_end - clip.in_point
                instances.append((cue_index, start, end, cue))
        instances.sort(key=lambda item: (item[1], item[2], item[0]))
        merged: list[tuple[int, float, float, SubtitleCue]] = []
        for cue_index, start, end, cue in instances:
            if merged and merged[-1][0] == cue_index and start <= merged[-1][2] + 0.01:
                previous_index, previous_start, previous_end, previous_cue = merged[-1]
                merged[-1] = (previous_index, previous_start, max(previous_end, end), previous_cue)
            else:
                merged.append((cue_index, start, end, cue))
        return merged

    def touch(self) -> None:
        self.updated_at = utc_now()

    def asset(self, asset_id: str) -> MediaAsset:
        for item in self.assets:
            if item.id == asset_id:
                return item
        raise KeyError(f"未找到素材：{asset_id}")

    def find_asset_by_path(self, path: str | Path) -> MediaAsset | None:
        resolved = str(Path(path).resolve()).casefold()
        return next((item for item in self.assets if item.path.casefold() == resolved), None)

    def add_asset(self, asset: MediaAsset) -> MediaAsset:
        existing = self.find_asset_by_path(asset.path)
        if existing:
            return existing
        self.assets.append(asset)
        self.touch()
        return asset

    def append_video_asset(self, asset_id: str) -> TimelineClip:
        asset = self.asset(asset_id)
        if asset.kind != "video":
            raise ValueError("只有视频素材可以加入主时间线")
        if asset.duration <= 0:
            raise ValueError("视频时长无效，无法加入时间线")
        clip = TimelineClip(
            id=new_id("clip"),
            asset_id=asset.id,
            name=asset.name,
            in_point=0.0,
            out_point=asset.duration,
        )
        self.clips.append(clip)
        self.touch()
        return clip

    def add_audio_asset(self, asset_id: str) -> AudioTrack:
        asset = self.asset(asset_id)
        if asset.kind not in {"audio", "video"}:
            raise ValueError("该素材没有可用音频")
        if asset.kind == "video" and not asset.has_audio:
            raise ValueError("该视频不包含音频轨")
        if asset.duration <= 0:
            raise ValueError("音频时长无效，无法加入音轨")
        track = AudioTrack(
            id=new_id("audio"),
            asset_id=asset.id,
            name=asset.name,
            start_time=0.0,
            in_point=0.0,
            out_point=asset.duration,
        )
        self.audio_tracks.append(track)
        self.touch()
        return track

    def split_clip(self, index: int, source_time: float) -> tuple[TimelineClip, TimelineClip]:
        clip = self.clips[index]
        point = float(source_time)
        if point <= clip.in_point + 0.04 or point >= clip.out_point - 0.04:
            raise ValueError("切分位置必须位于镜头内部，并距离边界至少 0.04 秒")
        left = copy.deepcopy(clip)
        left.id = new_id("clip")
        left.out_point = point
        right = copy.deepcopy(clip)
        right.id = new_id("clip")
        right.in_point = point
        right.name = f"{clip.name}（续）"
        right.transition = "cut"
        right.transition_duration = 0.0
        self.clips[index : index + 1] = [left, right]
        self.touch()
        return left, right

    def split_clip_at_scenes(self, index: int, boundaries: list[float]) -> list[TimelineClip]:
        clip = self.clips[index]
        points = [clip.in_point]
        points.extend(
            point
            for point in sorted({float(value) for value in boundaries})
            if clip.in_point + 0.04 <= point <= clip.out_point - 0.04
        )
        points.append(clip.out_point)
        segments: list[TimelineClip] = []
        for segment_index, (start, end) in enumerate(zip(points, points[1:]), start=1):
            if end - start < 0.04:
                continue
            segment = copy.deepcopy(clip)
            segment.id = new_id("clip")
            segment.name = f"{clip.name} · 分镜 {segment_index:02d}"
            segment.in_point = start
            segment.out_point = end
            if segment_index > 1:
                segment.transition = "cut"
                segment.transition_duration = 0.0
            segments.append(segment)
        if not segments:
            raise ValueError("没有检测到可用的分镜边界")
        self.clips[index : index + 1] = segments
        self.touch()
        return segments

    def duplicate_clip(self, index: int) -> TimelineClip:
        duplicate = copy.deepcopy(self.clips[index])
        duplicate.id = new_id("clip")
        duplicate.name = f"{duplicate.name}（副本）"
        duplicate.transition = "cut"
        duplicate.transition_duration = 0.0
        self.clips.insert(index + 1, duplicate)
        self.touch()
        return duplicate

    def remove_clip(self, index: int) -> TimelineClip:
        clip = self.clips.pop(index)
        if self.clips:
            self.clips[0].transition = "cut"
            self.clips[0].transition_duration = 0.0
        self.touch()
        return clip

    def move_clip(self, index: int, target_index: int) -> int:
        if not self.clips:
            return 0
        target = max(0, min(len(self.clips) - 1, target_index))
        if index == target:
            return target
        clip = self.clips.pop(index)
        self.clips.insert(target, clip)
        self.clips[0].transition = "cut"
        self.clips[0].transition_duration = 0.0
        self.touch()
        return target

    def set_clip_transition(self, index: int, transition: str, duration: float) -> None:
        if not 0 <= index < len(self.clips):
            raise IndexError("镜头索引无效")
        allowed = {"cut", "fade", "dissolve"}
        value = transition if transition in allowed else "cut"
        if index == 0:
            value = "cut"
        clip = self.clips[index]
        clip.transition = value
        clip.transition_duration = 0.0 if value == "cut" else max(0.1, min(2.0, float(duration)))
        self.touch()

    def update_clip(
        self,
        index: int,
        *,
        in_point: float,
        out_point: float,
        volume: float,
        muted: bool,
    ) -> None:
        clip = self.clips[index]
        asset = self.asset(clip.asset_id)
        start = max(0.0, float(in_point))
        end = min(asset.duration, float(out_point))
        if end - start < 0.04:
            raise ValueError("镜头结束时间必须晚于开始时间至少 0.04 秒")
        clip.in_point = start
        clip.out_point = end
        clip.volume = max(0.0, min(2.0, float(volume)))
        clip.muted = bool(muted)
        self.touch()

    def update_audio_track(
        self,
        index: int,
        *,
        start_time: float,
        in_point: float,
        out_point: float,
        volume: float,
        muted: bool,
    ) -> None:
        track = self.audio_tracks[index]
        asset = self.asset(track.asset_id)
        start = max(0.0, float(in_point))
        end = min(asset.duration, float(out_point))
        if end - start < 0.04:
            raise ValueError("音轨结束时间必须晚于开始时间至少 0.04 秒")
        track.start_time = max(0.0, float(start_time))
        track.in_point = start
        track.out_point = end
        track.volume = max(0.0, min(2.0, float(volume)))
        track.muted = bool(muted)
        self.touch()

    def remove_audio_track(self, index: int) -> AudioTrack:
        track = self.audio_tracks.pop(index)
        self.touch()
        return track

    def update_subtitle(
        self,
        index: int,
        *,
        start: float,
        end: float,
        text: str,
        enabled: bool,
    ) -> None:
        cue = self.subtitle_cues[index]
        asset = self.asset(cue.asset_id)
        cue_start = max(0.0, float(start))
        cue_end = min(asset.duration, float(end))
        value = str(text).strip()
        if cue_end - cue_start < 0.01:
            raise ValueError("字幕结束时间必须晚于开始时间至少 0.01 秒")
        if not value:
            raise ValueError("字幕文字不能为空")
        cue.start = cue_start
        cue.end = cue_end
        cue.text = value
        cue.enabled = bool(enabled)
        self.touch()

    def remove_subtitle(self, index: int) -> SubtitleCue:
        cue = self.subtitle_cues.pop(index)
        self.touch()
        return cue

    def validate(self, *, check_files: bool = True) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("项目分辨率必须大于 0")
        if self.fps <= 0:
            raise ValueError("项目帧率必须大于 0")
        asset_ids = {asset.id for asset in self.assets}
        if len(asset_ids) != len(self.assets):
            raise ValueError("项目中存在重复素材 ID")
        if check_files:
            missing = [asset.path for asset in self.assets if not Path(asset.path).is_file()]
            if missing:
                raise FileNotFoundError(f"找不到素材：{missing[0]}")
        for clip in self.clips:
            if clip.asset_id not in asset_ids:
                raise ValueError(f"镜头引用了不存在的素材：{clip.name}")
            asset = self.asset(clip.asset_id)
            if clip.in_point < 0 or clip.out_point > asset.duration + 0.001 or clip.duration < 0.04:
                raise ValueError(f"镜头时间范围无效：{clip.name}")
            if clip.transition not in {"cut", "fade", "dissolve"}:
                raise ValueError(f"镜头转场无效：{clip.name}")
            if clip.transition != "cut" and not 0.1 <= clip.transition_duration <= 2.0:
                raise ValueError(f"镜头转场时长无效：{clip.name}")
        for track in self.audio_tracks:
            if track.asset_id not in asset_ids:
                raise ValueError(f"音轨引用了不存在的素材：{track.name}")
            asset = self.asset(track.asset_id)
            if track.in_point < 0 or track.out_point > asset.duration + 0.001 or track.duration < 0.04:
                raise ValueError(f"音轨时间范围无效：{track.name}")
        for cue in self.subtitle_cues:
            if cue.asset_id not in asset_ids:
                raise ValueError(f"字幕引用了不存在的素材：{cue.text[:20]}")
            asset = self.asset(cue.asset_id)
            if cue.start < 0 or cue.end > asset.duration + 0.001 or cue.end - cue.start < 0.01:
                raise ValueError(f"字幕时间范围无效：{cue.text[:20]}")
        for evidence in self.analysis_evidence:
            if evidence.asset_id not in asset_ids:
                raise ValueError(f"分析证据引用了不存在的素材：{evidence.label}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EditProject":
        payload = dict(data)
        source_schema = int(payload.get("schema_version", 1) or 1)
        if source_schema > cls.__dataclass_fields__["schema_version"].default:
            raise ValueError(f"项目版本过新，当前程序无法打开（schema {source_schema}）")
        assets = [MediaAsset(**item) for item in payload.pop("assets", [])]
        clips = [TimelineClip(**item) for item in payload.pop("clips", [])]
        audio_tracks = [AudioTrack(**item) for item in payload.pop("audio_tracks", [])]
        subtitle_cues = [SubtitleCue(**item) for item in payload.pop("subtitle_cues", [])]
        analysis_evidence = [AnalysisEvidence(**item) for item in payload.pop("analysis_evidence", [])]
        allowed = {
            name
            for name in cls.__dataclass_fields__
            if name not in {"assets", "clips", "audio_tracks", "subtitle_cues", "analysis_evidence"}
        }
        project = cls(**{key: value for key, value in payload.items() if key in allowed})
        # Older projects are normalized in memory so the next save persists the
        # transition/subtitle-aware schema instead of remaining on a stale tag.
        project.schema_version = cls.__dataclass_fields__["schema_version"].default
        project.assets = assets
        project.clips = clips
        project.audio_tracks = audio_tracks
        project.subtitle_cues = subtitle_cues
        project.analysis_evidence = analysis_evidence
        project.validate(check_files=False)
        return project

    def clone(self) -> "EditProject":
        return EditProject.from_dict(copy.deepcopy(self.to_dict()))

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.touch()
        target.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: str | Path) -> "EditProject":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("剪辑项目格式无效")
        return cls.from_dict(data)


class SnapshotHistory:
    """Small snapshot-based undo stack for non-destructive project edits."""

    def __init__(self, limit: int = 60) -> None:
        self.limit = max(1, int(limit))
        self._undo: list[dict[str, Any]] = []
        self._redo: list[dict[str, Any]] = []

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()

    def record(self, project: EditProject) -> None:
        self._undo.append(copy.deepcopy(project.to_dict()))
        if len(self._undo) > self.limit:
            del self._undo[0]
        self._redo.clear()

    def undo(self, current: EditProject) -> EditProject:
        if not self._undo:
            return current
        self._redo.append(copy.deepcopy(current.to_dict()))
        return EditProject.from_dict(self._undo.pop())

    def redo(self, current: EditProject) -> EditProject:
        if not self._redo:
            return current
        self._undo.append(copy.deepcopy(current.to_dict()))
        return EditProject.from_dict(self._redo.pop())


# Automatic recipes return this same editable structure; the alias documents the boundary.
EditPlan = EditProject
