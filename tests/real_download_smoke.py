from __future__ import annotations

import subprocess
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import imageio_ffmpeg

from streamlight.engine import DownloadEngine
from streamlight.models import DownloadRequest
from streamlight.workers import BatchAnalyzeWorker, BatchDownloadWorker


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source_dir = root / "source"
        output_dir = root / "download"
        audio_output_dir = root / "audio"
        source_dir.mkdir()
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x180:rate=15",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:sample_rate=44100",
            "-t",
            "2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-f",
            "hls",
            "-hls_time",
            "1",
            "-hls_list_size",
            "0",
            str(source_dir / "playlist.m3u8"),
        ]
        subprocess.run(command, check=True)
        (source_dir / "playlist-two.m3u8").write_text(
            (source_dir / "playlist.m3u8").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        handler = partial(QuietHandler, directory=str(source_dir))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            url = f"http://127.0.0.1:{server.server_port}/playlist.m3u8"
            request = DownloadRequest(url=url, output_dir=output_dir, use_archive=False)
            engine = DownloadEngine(request)
            summary = engine.analyze()
            if summary.format_count < 1:
                raise AssertionError("分析阶段没有发现媒体格式")
            engine.download()
            outputs = [path for path in output_dir.iterdir() if path.is_file() and not path.name.startswith(".")]
            if not outputs or not any(path.stat().st_size > 0 for path in outputs):
                raise AssertionError("下载目录中没有生成有效媒体文件")
            print(f"REAL VIDEO DOWNLOAD PASS: {outputs[0].name} ({outputs[0].stat().st_size} bytes)")

            batch_output_dir = root / "batch"
            batch_urls = [
                f"http://127.0.0.1:{server.server_port}/playlist.m3u8",
                f"http://127.0.0.1:{server.server_port}/playlist-two.m3u8",
            ]
            batch_jobs = [
                (
                    index,
                    DownloadRequest(url=batch_url, output_dir=batch_output_dir, use_archive=False),
                )
                for index, batch_url in enumerate(batch_urls)
            ]
            analyzed_indices: list[int] = []
            analyze_worker = BatchAnalyzeWorker(batch_jobs)
            analyze_worker.item_analyzed.connect(
                lambda index, item_url, item_summary: analyzed_indices.append(index)
            )
            analyze_worker.run()
            if analyzed_indices != [0, 1]:
                raise AssertionError(f"批量分析结果异常：{analyzed_indices}")

            downloaded_indices: list[int] = []
            download_worker = BatchDownloadWorker(batch_jobs)
            download_worker.item_downloaded.connect(
                lambda index, item_url, item_output: downloaded_indices.append(index)
            )
            download_worker.run()
            batch_files = [
                path
                for path in batch_output_dir.iterdir()
                if path.is_file() and not path.name.startswith(".")
            ]
            if downloaded_indices != [0, 1] or len(batch_files) < 2:
                raise AssertionError(
                    f"批量下载结果异常：items={downloaded_indices}, files={len(batch_files)}"
                )
            print(f"REAL BATCH DOWNLOAD PASS: {len(batch_files)} files")

            audio_request = DownloadRequest(
                url=url,
                output_dir=audio_output_dir,
                preset_key="audio",
                use_archive=False,
            )
            DownloadEngine(audio_request).download()
            audio_files = list(audio_output_dir.glob("*.mp3"))
            if not audio_files or audio_files[0].stat().st_size <= 0:
                raise AssertionError("仅音频模式没有生成有效 MP3 文件")
            print(f"REAL AUDIO DOWNLOAD PASS: {audio_files[0].name} ({audio_files[0].stat().st_size} bytes)")
        finally:
            server.shutdown()
            server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
