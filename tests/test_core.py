from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from streamlight.engine import DownloadEngine, parse_url_lines, validate_http_url
from streamlight.errors import UserCancelled, redact_secrets
from streamlight.models import DownloadRequest, get_preset, media_summary_from_info


class CoreTests(unittest.TestCase):
    def test_validate_http_url(self) -> None:
        self.assertEqual(validate_http_url(" https://example.com/watch/1 "), "https://example.com/watch/1")
        for value in ("", "example.com", "file:///tmp/video.mp4", "javascript:alert(1)"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_http_url(value)

    def test_parse_url_lines_preserves_order_and_removes_duplicates(self) -> None:
        self.assertEqual(
            parse_url_lines("\n https://a.example/v1 \nhttps://b.example/v2\nhttps://a.example/v1\n"),
            ["https://a.example/v1", "https://b.example/v2"],
        )

    def test_redacts_secret_query_values_and_cookie(self) -> None:
        message = "https://cdn.test/a.m3u8?token=secret&expires=123 Cookie: session=abc"
        cleaned = redact_secrets(message)
        self.assertNotIn("secret", cleaned)
        self.assertNotIn("session=abc", cleaned)
        self.assertIn("token=<已隐藏>", cleaned)

    def test_media_summary_uses_available_formats(self) -> None:
        summary = media_summary_from_info(
            {
                "title": "测试视频",
                "extractor_key": "Generic",
                "duration": 65,
                "uploader": "测试来源",
                "webpage_url": "https://example.com/v",
                "formats": [{"height": 720}, {"height": 1080}, {"height": 1080}, {"height": None}],
            }
        )
        self.assertEqual(summary.title, "测试视频")
        self.assertEqual(summary.duration_text, "01:05")
        self.assertEqual(summary.available_heights, (720, 1080))

    def test_format_presets(self) -> None:
        self.assertEqual(get_preset("1080").label, "最高 1080p")
        self.assertTrue(get_preset("audio").audio_only)
        self.assertEqual(get_preset("missing").key, "best")

    def test_engine_options_create_output_and_hide_archive_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            request = DownloadRequest(
                url="https://example.com/video",
                output_dir=Path(directory) / "output",
                preset_key="720",
                use_archive=False,
            )
            options = DownloadEngine(request)._common_options(analysis=False)
            self.assertEqual(options["format"], get_preset("720").selector)
            self.assertNotIn("download_archive", options)
            self.assertTrue((Path(directory) / "output").is_dir())

    def test_cancelled_engine_stops_before_network_access(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            engine = DownloadEngine(
                DownloadRequest(url="https://example.com/video", output_dir=Path(directory))
            )
            engine.cancel()
            with self.assertRaises(UserCancelled):
                engine.analyze()


if __name__ == "__main__":
    unittest.main()
