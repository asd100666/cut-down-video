from __future__ import annotations

from PySide6.QtCore import QByteArray, QTimer, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget


_PATHS = {
    "paste": '<rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
    "folder": '<path d="M3 6a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v2H3z"/><path d="M3 10h18l-2 9a2 2 0 0 1-2 1H5a2 2 0 0 1-2-2z"/>',
    "cancel": '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6m0-6-6 6"/>',
    "download": '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 20h14"/>',
    "play": '<path d="m8 5 11 7-11 7z"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
    "file": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5"/>',
    "folder-open": '<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v2H6l-3 8z"/><path d="M6 11h16l-3 8H3"/>',
    "save": '<path d="M5 3h12l2 2v16H5z"/><path d="M8 3v6h8V3"/><path d="M8 21v-7h8v7"/>',
    "undo": '<path d="M9 7 4 12l5 5"/><path d="M5 12h9a6 6 0 0 1 6 6"/>',
    "redo": '<path d="m15 7 5 5-5 5"/><path d="M19 12h-9a6 6 0 0 0-6 6"/>',
    "import": '<path d="M12 3v12"/><path d="m7 8 5-5 5 5"/><path d="M5 20h14"/>',
    "export": '<path d="M12 21V9"/><path d="m7 14 5-5 5 5"/><path d="M5 4h14"/>',
    "music": '<path d="M9 18V5l10-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="16" cy="16" r="3"/>',
    "video": '<rect x="3" y="5" width="14" height="14" rx="2"/><path d="m17 10 4-3v10l-4-3z"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "scissors": '<circle cx="6" cy="7" r="3"/><circle cx="6" cy="17" r="3"/><path d="m8.5 8.5 11 6.5M8.5 15.5 19.5 9"/>',
    "copy": '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
    "trash": '<path d="M4 7h16M9 7V4h6v3M7 7l1 14h8l1-14M10 11v6M14 11v6"/>',
    "up": '<path d="m6 15 6-6 6 6"/>',
    "down": '<path d="m6 9 6 6 6-6"/>',
    "pause": '<path d="M8 5v14M16 5v14"/>',
    "fullscreen": '<path d="M8 3H3v5M16 3h5v5M21 16v5h-5M3 16v5h5"/>',
    "exit-fullscreen": '<path d="M8 8H3M8 8V3M16 8h5M16 8V3M16 16h5M16 16v5M8 16H3M8 16v5"/>',
    "volume": '<path d="M5 10v4h4l5 4V6l-5 4z"/><path d="M17 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12"/>',
    "mute": '<path d="M5 10v4h4l5 4V6l-5 4z"/><path d="m17 10 4 4m0-4-4 4"/>',
    "sparkles": '<path d="m12 3 1.4 4.1L17.5 8.5l-4.1 1.4L12 14l-1.4-4.1-4.1-1.4 4.1-1.4z"/><path d="m19 14 .8 2.2L22 17l-2.2.8L19 20l-.8-2.2L16 17l2.2-.8z"/><path d="m5 14 .7 1.8 1.8.7-1.8.7L5 19l-.7-1.8-1.8-.7 1.8-.7z"/>',
}


def _logo_svg(angle: int = 0, active: bool = False) -> str:
    dot_opacity = "1" if active else ".72"
    return f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <defs>
        <linearGradient id="surface" x1="8" y1="6" x2="56" y2="58" gradientUnits="userSpaceOnUse">
          <stop stop-color="#F8FFFB"/>
          <stop offset="1" stop-color="#DDF7E9"/>
        </linearGradient>
        <linearGradient id="stream" x1="14" y1="16" x2="52" y2="48" gradientUnits="userSpaceOnUse">
          <stop stop-color="#67DCA2"/>
          <stop offset=".52" stop-color="#1FAA72"/>
          <stop offset="1" stop-color="#08734B"/>
        </linearGradient>
      </defs>
      <rect x="4" y="4" width="56" height="56" rx="18" fill="url(#surface)" stroke="#A9DEC1" stroke-width="2"/>
      <path d="M14 29C18 18 27 13 38 15c8 1 13 6 15 13" fill="none" stroke="url(#stream)" stroke-width="5" stroke-linecap="round"/>
      <path d="M50 36c-4 10-14 15-24 13-7-1-12-6-14-12" fill="none" stroke="#70D5A0" stroke-width="5" stroke-linecap="round"/>
      <circle cx="32" cy="32" r="23" fill="none" stroke="#C9EEDD" stroke-width="1.5" stroke-dasharray="2 5"/>
      <g transform="rotate({angle} 32 32)" opacity="{dot_opacity}">
        <circle cx="32" cy="9" r="3.6" fill="#0B8255" stroke="#F5FFF9" stroke-width="2"/>
      </g>
      <path d="M32 20v22m0 0-8-8m8 8 8-8" fill="none" stroke="#075F40" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M23 49h18" fill="none" stroke="#075F40" stroke-width="3.5" stroke-linecap="round"/>
    </svg>
    """


def _icon_from_svg(svg: str, size: int) -> QIcon:
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def svg_icon(name: str, color: str = "#315B47", size: int = 20) -> QIcon:
    paths = _PATHS[name]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f"{paths}</svg>"
    )
    return _icon_from_svg(svg, size)


def app_icon(size: int = 64) -> QIcon:
    return _icon_from_svg(_logo_svg(), size)


class AnimatedLogoWidget(QWidget):
    """SVG-rendered logo whose orbit animates only during active work."""

    def __init__(self, size: int = 50, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAccessibleName("流光下载器动态标识")
        self._angle = 0
        self._active = False
        self._renderer = QSvgRenderer(QByteArray(_logo_svg().encode("utf-8")), self)
        self._timer = QTimer(self)
        self._timer.setInterval(70)
        self._timer.timeout.connect(self._advance)

    @property
    def is_active(self) -> bool:
        return self._active

    def set_active(self, active: bool) -> None:
        if active == self._active:
            return
        self._active = active
        if active:
            self._timer.start()
        else:
            self._timer.stop()
            self._angle = 0
            self._reload()

    def _advance(self) -> None:
        self._angle = (self._angle + 8) % 360
        self._reload()

    def _reload(self) -> None:
        self._renderer.load(QByteArray(_logo_svg(self._angle, self._active).encode("utf-8")))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._renderer.render(painter, self.rect())
        painter.end()
