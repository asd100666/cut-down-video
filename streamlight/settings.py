from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths


@dataclass(slots=True)
class AppSettings:
    output_dir: str
    preset_key: str = "best"
    cookie_browser: str = ""
    referer: str = ""
    user_agent: str = ""
    allow_playlist: bool = False
    write_subtitles: bool = False
    write_auto_subtitles: bool = False
    use_archive: bool = True


def _default_output_dir() -> str:
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
    base = Path(location) if location else Path.home() / "Downloads"
    return str(base / "流光下载器")


def _as_bool(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


class SettingsStore:
    def __init__(self) -> None:
        self._settings = QSettings()

    def load(self) -> AppSettings:
        return AppSettings(
            output_dir=str(self._settings.value("download/output_dir", _default_output_dir())),
            preset_key=str(self._settings.value("download/preset", "best")),
            cookie_browser=str(self._settings.value("network/cookie_browser", "")),
            referer=str(self._settings.value("network/referer", "")),
            user_agent=str(self._settings.value("network/user_agent", "")),
            allow_playlist=_as_bool(self._settings.value("download/allow_playlist"), False),
            write_subtitles=_as_bool(self._settings.value("download/write_subtitles"), False),
            write_auto_subtitles=_as_bool(self._settings.value("download/write_auto_subtitles"), False),
            use_archive=_as_bool(self._settings.value("download/use_archive"), True),
        )

    def save(self, settings: AppSettings) -> None:
        self._settings.setValue("download/output_dir", settings.output_dir)
        self._settings.setValue("download/preset", settings.preset_key)
        self._settings.setValue("network/cookie_browser", settings.cookie_browser)
        self._settings.setValue("network/referer", settings.referer)
        self._settings.setValue("network/user_agent", settings.user_agent)
        self._settings.setValue("download/allow_playlist", settings.allow_playlist)
        self._settings.setValue("download/write_subtitles", settings.write_subtitles)
        self._settings.setValue("download/write_auto_subtitles", settings.write_auto_subtitles)
        self._settings.setValue("download/use_archive", settings.use_archive)
        self._settings.sync()

