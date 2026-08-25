from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .icons import svg_icon


class CountdownToast(QFrame):
    """Non-layout transient feedback with an explicit auto-dismiss countdown."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setProperty("kind", "info")
        self.setFixedSize(390, 78)
        self.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 11, 12, 11)
        layout.setSpacing(11)

        self.icon_label = QLabel(objectName="ToastIcon")
        self.icon_label.setFixedSize(38, 38)
        self.icon_label.setScaledContents(False)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        self.title_label = QLabel(objectName="ToastTitle")
        self.message_label = QLabel(objectName="ToastMessage")
        self.message_label.setWordWrap(False)
        text_box.addWidget(self.title_label)
        text_box.addWidget(self.message_label)
        layout.addLayout(text_box, 1)

        self.countdown_label = QLabel(objectName="ToastCountdown")
        self.countdown_label.setFixedSize(38, 38)
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.countdown_label)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._remaining = 0

        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity)
        self._animation = QPropertyAnimation(self._opacity, b"opacity", self)
        self._animation.setDuration(180)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.finished.connect(self._on_animation_finished)
        self._dismissing = False

    @property
    def remaining(self) -> int:
        return self._remaining

    def show_message(self, title: str, message: str, kind: str = "info", seconds: int = 4) -> None:
        self._animation.stop()
        self._dismissing = False
        self.setProperty("kind", kind)
        self.style().unpolish(self)
        self.style().polish(self)

        colors = {
            "success": ("check", "#14764E"),
            "error": ("cancel", "#A23A4C"),
            "warning": ("info", "#8A6518"),
            "info": ("info", "#177A55"),
        }
        icon_name, color = colors.get(kind, colors["info"])
        self.icon_label.setPixmap(svg_icon(icon_name, color, 24).pixmap(24, 24))
        self.title_label.setText(title)
        self.message_label.setText(message)
        self.message_label.setToolTip(message)

        self._remaining = max(1, seconds)
        self.countdown_label.setText(f"{self._remaining}s")
        self.reposition()
        self._opacity.setOpacity(0.0)
        self.show()
        self.raise_()
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.start()
        self._timer.start()

    def dismiss(self) -> None:
        self._timer.stop()
        self._animation.stop()
        self._dismissing = True
        self._animation.setStartValue(self._opacity.opacity())
        self._animation.setEndValue(0.0)
        self._animation.start()

    def _on_animation_finished(self) -> None:
        if self._dismissing and self._opacity.opacity() <= 0.01:
            self.hide()
            self._dismissing = False

    def _tick(self) -> None:
        self._remaining -= 1
        if self._remaining <= 0:
            self.dismiss()
            return
        self.countdown_label.setText(f"{self._remaining}s")

    def reposition(self) -> None:
        parent = self.parentWidget()
        if parent:
            x = parent.width() - self.width() - 28
            self.move(max(20, x), 96)
