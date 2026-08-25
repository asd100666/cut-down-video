from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .editor_models import EditProject, format_timecode


LANE_HEIGHTS = (26, 64, 48, 48)
LANE_NAMES = ("时间", "视频轨", "音频轨", "字幕轨")


class _TimelineItem(QGraphicsRectItem):
    def __init__(
        self,
        timeline: "MultiTrackTimelineWidget",
        kind: str,
        index: int,
        rect: QRectF,
        color: str,
        label: str,
        *,
        movable: bool = False,
    ) -> None:
        super().__init__(rect)
        self.timeline = timeline
        self.kind = kind
        self.index = index
        self.lane_y = rect.y()
        self.setBrush(QBrush(QColor(color)))
        self.setPen(QPen(QColor("#B8D7C5"), 1))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        if movable:
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        text = QGraphicsSimpleTextItem(label, self)
        text.setBrush(QBrush(QColor("#F7FFF9" if kind != "subtitle" else "#173F2D")))
        text.setPos(rect.x() + 7, rect.y() + 6)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.kind == "clip":
            point = QPointF(value)
            return QPointF(max(-self.rect().x(), point.x()), 0.0)
        return super().itemChange(change, value)

    def mousePressEvent(self, event) -> None:
        self.timeline._emit_selection(self.kind, self.index)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if self.kind == "clip" and abs(self.pos().x()) > 0.5:
            center = self.sceneBoundingRect().center().x()
            target = self.timeline.clip_target_at(center)
            self.setPos(0.0, 0.0)
            if target != self.index:
                self.timeline.clipMoveRequested.emit(self.index, target)


class _TransitionItem(QGraphicsRectItem):
    def __init__(self, timeline: "MultiTrackTimelineWidget", clip_index: int, rect: QRectF, label: str) -> None:
        super().__init__(rect)
        self.timeline = timeline
        self.clip_index = clip_index
        self.setBrush(QBrush(QColor("#F1B94C")))
        self.setPen(QPen(QColor("#9A6514"), 1))
        self.setToolTip("点击编辑镜头之间的转场")
        text = QGraphicsSimpleTextItem(label, self)
        text.setBrush(QBrush(QColor("#4A2E08")))
        text.setPos(rect.x() + 4, rect.y() + 2)

    def mousePressEvent(self, event) -> None:
        self.timeline.transitionRequested.emit(self.clip_index)
        event.accept()


class MultiTrackTimelineWidget(QFrame):
    clipSelected = Signal(int)
    audioSelected = Signal(int)
    subtitleSelected = Signal(int)
    clipMoveRequested = Signal(int, int)
    transitionRequested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, objectName="MultiTrackTimeline")
        self.project = EditProject()
        self._pixels_per_second = 8.0
        self._clip_items: list[_TimelineItem] = []
        self._selected_clip = -1
        self._selected_audio = -1
        self._selected_subtitle = -1

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        labels = QFrame(objectName="TimelineLabels")
        labels.setFixedWidth(72)
        label_layout = QVBoxLayout(labels)
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.setSpacing(0)
        for name, height in zip(LANE_NAMES, LANE_HEIGHTS):
            label = QLabel(name, objectName="TimelineLaneLabel")
            label.setFixedHeight(height)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label_layout.addWidget(label)
        zoom_row = QHBoxLayout()
        zoom_row.setContentsMargins(5, 2, 5, 2)
        zoom_row.addWidget(QLabel("缩放", objectName="TimelineZoomLabel"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(35, 300)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setToolTip("调整时间线缩放")
        zoom_row.addWidget(self.zoom_slider, 1)
        label_layout.addLayout(zoom_row)
        root.addWidget(labels)

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, objectName="TimelineGraphicsView")
        self.view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.view.setMinimumHeight(sum(LANE_HEIGHTS) + 12)
        root.addWidget(self.view, 1)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)

        self.playhead = QGraphicsLineItem()
        self.playhead.setPen(QPen(QColor("#F05D5E"), 2))
        self.playhead.setZValue(20)

    def _on_zoom_changed(self, _value: int) -> None:
        self.set_project(
            self.project,
            self._selected_clip,
            self._selected_audio,
            self._selected_subtitle,
        )

    def _base_scale(self, duration: float) -> float:
        viewport_width = max(640, self.view.viewport().width() - 24)
        return max(0.18, min(14.0, viewport_width / max(30.0, duration)))

    @staticmethod
    def _elide(label: str, width: float) -> str:
        limit = max(3, int(width / 8))
        return label if len(label) <= limit else label[: max(1, limit - 1)] + "…"

    def set_project(
        self,
        project: EditProject,
        selected_clip: int = -1,
        selected_audio: int = -1,
        selected_subtitle: int = -1,
    ) -> None:
        self.project = project
        self._selected_clip = selected_clip
        self._selected_audio = selected_audio
        self._selected_subtitle = selected_subtitle
        self.scene.clear()
        self._clip_items = []
        duration = max(
            project.duration,
            max((track.start_time + track.duration for track in project.audio_tracks), default=0.0),
            1.0,
        )
        self._pixels_per_second = self._base_scale(duration) * self.zoom_slider.value() / 100.0
        width = max(self.view.viewport().width() - 2, duration * self._pixels_per_second + 24)
        heights = LANE_HEIGHTS
        lane_tops = (0, heights[0], heights[0] + heights[1], heights[0] + heights[1] + heights[2])
        total_height = sum(heights)
        self.scene.setSceneRect(0, 0, width, total_height)

        lane_colors = ("#102019", "#132A20", "#173326", "#EAF5EE")
        for top, height, color in zip(lane_tops, heights, lane_colors):
            lane = self.scene.addRect(0, top, width, height, QPen(QColor("#395A49"), 1), QBrush(QColor(color)))
            lane.setZValue(-10)

        tick_seconds = self._tick_interval(self._pixels_per_second)
        tick = 0.0
        while tick <= duration + tick_seconds:
            x = tick * self._pixels_per_second
            self.scene.addLine(x, 17, x, heights[0], QPen(QColor("#6F8C7D"), 1))
            text = self.scene.addSimpleText(format_timecode(tick).split(".", 1)[0])
            text.setBrush(QBrush(QColor("#D9EEE2")))
            text.setPos(x + 3, 1)
            tick += tick_seconds

        for index, (clip, start, end) in enumerate(project.clip_timeline_ranges()):
            x = start * self._pixels_per_second
            item_width = max(30.0, (end - start) * self._pixels_per_second)
            rect = QRectF(x + 2, lane_tops[1] + 5, item_width - 4, heights[1] - 10)
            label = self._elide(f"{clip.name}  {format_timecode(clip.duration)}", item_width - 12)
            item = _TimelineItem(self, "clip", index, rect, "#218B60", label, movable=not clip.locked)
            self.scene.addItem(item)
            item.setSelected(index == selected_clip)
            self._clip_items.append(item)
            if index > 0:
                transition_label = "切" if clip.transition == "cut" else "转"
                boundary_x = x - 9
                transition = _TransitionItem(
                    self,
                    index,
                    QRectF(boundary_x, lane_tops[1] + heights[1] / 2 - 10, 20, 20),
                    transition_label,
                )
                self.scene.addItem(transition)
                transition.setZValue(8)

        for index, track in enumerate(project.audio_tracks):
            x = track.start_time * self._pixels_per_second
            item_width = max(34.0, track.duration * self._pixels_per_second)
            rect = QRectF(x + 2, lane_tops[2] + 5, item_width - 4, heights[2] - 10)
            label = self._elide(f"♪ {track.name}", item_width - 12)
            item = _TimelineItem(self, "audio", index, rect, "#486FA8", label)
            self.scene.addItem(item)
            item.setSelected(index == selected_audio)

        for cue_index, start, end, cue in project.timeline_subtitle_instances():
            x = start * self._pixels_per_second
            item_width = max(28.0, (end - start) * self._pixels_per_second)
            rect = QRectF(x + 2, lane_tops[3] + 5, item_width - 4, heights[3] - 10)
            label = self._elide(cue.text, item_width - 12)
            item = _TimelineItem(self, "subtitle", cue_index, rect, "#DCEEE4", label)
            self.scene.addItem(item)
            item.setSelected(cue_index == selected_subtitle)

        self.playhead = QGraphicsLineItem(0, heights[0], 0, total_height)
        self.playhead.setPen(QPen(QColor("#F05D5E"), 2))
        self.playhead.setZValue(20)
        self.scene.addItem(self.playhead)

    @staticmethod
    def _tick_interval(pixels_per_second: float) -> float:
        for interval in (1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0):
            if interval * pixels_per_second >= 72:
                return interval
        return 1800.0

    def set_playhead(self, seconds: float) -> None:
        x = max(0.0, float(seconds)) * self._pixels_per_second
        line = self.playhead.line()
        self.playhead.setLine(x, line.y1(), x, line.y2())

    def clip_target_at(self, scene_x: float) -> int:
        ranges = self.project.clip_timeline_ranges()
        if not ranges:
            return 0
        centers = [((start + end) / 2) * self._pixels_per_second for _clip, start, end in ranges]
        return min(range(len(centers)), key=lambda index: abs(centers[index] - scene_x))

    def _emit_selection(self, kind: str, index: int) -> None:
        if kind == "clip":
            self.clipSelected.emit(index)
        elif kind == "audio":
            self.audioSelected.emit(index)
        elif kind == "subtitle":
            self.subtitleSelected.emit(index)
