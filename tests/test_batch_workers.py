from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlight.models import DownloadRequest, MediaSummary
from streamlight.workers import BatchAnalyzeWorker, BatchDownloadWorker


def _summary(url: str) -> MediaSummary:
    return MediaSummary(
        title=f"视频 {url.rsplit('/', 1)[-1]}",
        site="Test",
        duration=10,
        uploader="测试",
        webpage_url=url,
        thumbnail=None,
        available_heights=(720,),
        format_count=1,
        is_live=False,
        is_playlist=False,
        playlist_count=None,
    )


class _FakeEngine:
    def __init__(self, request, *, progress_callback=None, log_callback=None) -> None:
        self.request = request
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.is_cancelled = False

    def cancel(self) -> None:
        self.is_cancelled = True

    def analyze(self) -> MediaSummary:
        if "fail" in self.request.url:
            raise RuntimeError("模拟分析失败")
        return _summary(self.request.url)

    def download(self) -> str:
        if "fail" in self.request.url:
            raise RuntimeError("模拟下载失败")
        return str(self.request.output_dir)


class BatchWorkerTests(unittest.TestCase):
    def _jobs(self, directory: str) -> list[tuple[int, DownloadRequest]]:
        urls = ["https://example.com/one", "https://example.com/fail", "https://example.com/two"]
        return [
            (index, DownloadRequest(url=url, output_dir=Path(directory)))
            for index, url in enumerate(urls)
        ]

    @patch("streamlight.workers.DownloadEngine", _FakeEngine)
    def test_batch_analysis_keeps_going_after_one_item_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            worker = BatchAnalyzeWorker(self._jobs(directory))
            analyzed: list[int] = []
            failed: list[int] = []
            finished: list[bool] = []
            worker.item_analyzed.connect(lambda index, url, summary: analyzed.append(index))
            worker.item_failed.connect(lambda index, url, title, detail: failed.append(index))
            worker.finished.connect(lambda: finished.append(True))

            worker.run()

            self.assertEqual(analyzed, [0, 2])
            self.assertEqual(failed, [1])
            self.assertEqual(finished, [True])

    @patch("streamlight.workers.DownloadEngine", _FakeEngine)
    def test_batch_download_reports_each_success_and_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            worker = BatchDownloadWorker(self._jobs(directory))
            downloaded: list[int] = []
            failed: list[int] = []
            worker.item_downloaded.connect(lambda index, url, output: downloaded.append(index))
            worker.item_failed.connect(lambda index, url, title, detail: failed.append(index))

            worker.run()

            self.assertEqual(downloaded, [0, 2])
            self.assertEqual(failed, [1])


if __name__ == "__main__":
    unittest.main()
