from __future__ import annotations

import tempfile
import threading
import time
import unittest
import socket
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from streamlight.model_manager import (
    MODEL_REGISTRY,
    ModelDownloadCancelled,
    ModelDownloader,
    ModelFile,
    ModelIntegrityError,
    ModelManager,
    ModelSpec,
)


def make_spec(base_url: str, files: tuple[tuple[str, bytes], ...], capability: str = "speech") -> ModelSpec:
    return ModelSpec(
        id="test-model",
        name="测试模型",
        category="测试",
        capability=capability,
        description="本地测试模型",
        version="1.0",
        source_name="Local Test",
        source_url=base_url,
        license_name="Test",
        files=tuple(ModelFile(path, f"{base_url}/{path}", len(data)) for path, data in files),
    )


class _RangeHandler(BaseHTTPRequestHandler):
    payloads: dict[str, bytes] = {}
    saw_range = False

    def do_GET(self) -> None:
        key = self.path.lstrip("/")
        data = self.payloads.get(key)
        if data is None:
            self.send_error(404)
            return
        start = 0
        range_header = self.headers.get("Range")
        if range_header and range_header.startswith("bytes="):
            start = int(range_header[6:].split("-", 1)[0])
            self.__class__.saw_range = True
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{len(data) - 1}/{len(data)}")
        else:
            self.send_response(200)
        body = data[start:]
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


class _StallHandler(BaseHTTPRequestHandler):
    first_chunk_sent = threading.Event()
    release = threading.Event()

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Length", str(1024 * 1024))
        self.end_headers()
        self.wfile.write(b"x" * 1024)
        self.wfile.flush()
        self.__class__.first_chunk_sent.set()
        self.__class__.release.wait(10)

    def log_message(self, format: str, *args) -> None:
        return


class _FlakyRangeHandler(BaseHTTPRequestHandler):
    payload = b""
    request_count = 0
    saw_ranges: list[str] = []

    def do_GET(self) -> None:
        self.__class__.request_count += 1
        range_header = self.headers.get("Range")
        start = 0
        if range_header and range_header.startswith("bytes="):
            self.__class__.saw_ranges.append(range_header)
            start = int(range_header[6:].split("-", 1)[0])
            self.send_response(206)
            self.send_header(
                "Content-Range",
                f"bytes {start}-{len(self.payload) - 1}/{len(self.payload)}",
            )
        else:
            self.send_response(200)
        body = self.payload[start:]
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.__class__.request_count <= 2:
            self.wfile.write(body[:1024])
            self.wfile.flush()
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.connection.close()
            return
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


class ModelManagerTests(unittest.TestCase):
    def test_proxy_hint_never_exposes_proxy_credentials(self) -> None:
        with patch(
            "urllib.request.getproxies",
            return_value={"https": "http://proxy-user:proxy-secret@127.0.0.1:9674"},
        ):
            hint = ModelDownloader._proxy_hint()
        self.assertIn("127.0.0.1:9674", hint)
        self.assertNotIn("proxy-user", hint)
        self.assertNotIn("proxy-secret", hint)

    def test_missing_unverified_installed_and_corrupt_states(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data = b"verified-model-data"
            spec = make_spec("https://example.invalid", (("model.bin", data),))
            manager = ModelManager(directory, (spec,))
            self.assertEqual(manager.state(spec).code, "missing")
            target = manager.file_path(spec, spec.files[0])
            target.parent.mkdir(parents=True)
            target.write_bytes(data)
            self.assertEqual(manager.state(spec).code, "unverified")
            manager.verify_and_record(spec)
            self.assertTrue(manager.state(spec).ready)
            self.assertTrue(manager.capability_ready("speech"))
            target.write_bytes(b"broken")
            self.assertEqual(manager.state(spec).code, "corrupt")
            manager.remove(spec)
            self.assertEqual(manager.state(spec).code, "missing")

    def test_downloader_resumes_part_and_records_integrity(self) -> None:
        first = b"abcdefghij" * 500
        second = b"second-file" * 300
        _RangeHandler.payloads = {"model.bin": first, "tokenizer.json": second}
        _RangeHandler.saw_range = False
        server = ThreadingHTTPServer(("127.0.0.1", 0), _RangeHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            files = (("model.bin", first), ("tokenizer.json", second))
            spec = make_spec(base, files)
            with tempfile.TemporaryDirectory() as directory:
                manager = ModelManager(directory, (spec,))
                target = manager.file_path(spec, spec.files[0])
                target.parent.mkdir(parents=True)
                target.with_name(target.name + ".part").write_bytes(first[:100])
                progress: list[tuple[int, int, str]] = []
                ModelDownloader(manager, lambda done, total, name: progress.append((done, total, name))).download(spec)
                self.assertTrue(_RangeHandler.saw_range)
                self.assertEqual(target.read_bytes(), first)
                self.assertEqual(manager.file_path(spec, spec.files[1]).read_bytes(), second)
                self.assertTrue(manager.state(spec).ready)
                self.assertTrue(progress)
                self.assertTrue(all(total == spec.total_size for _done, total, _name in progress))
                downloads = [done for done, _total, name in progress if name.startswith("下载 · ")]
                verifies = [done for done, _total, name in progress if name.startswith("校验 · ")]
                self.assertEqual(downloads, sorted(downloads))
                self.assertEqual(verifies, sorted(verifies))
                self.assertTrue(downloads)
                self.assertTrue(verifies)
        finally:
            server.shutdown()
            server.server_close()

    def test_transient_eof_retries_and_resumes_automatically(self) -> None:
        data = b"retryable-model-data" * 20_000
        _FlakyRangeHandler.payload = data
        _FlakyRangeHandler.request_count = 0
        _FlakyRangeHandler.saw_ranges = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), _FlakyRangeHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            spec = make_spec(base, (("model.bin", data),))
            with tempfile.TemporaryDirectory() as directory:
                manager = ModelManager(directory, (spec,))
                progress: list[tuple[int, int, str]] = []
                ModelDownloader(
                    manager,
                    lambda done, total, name: progress.append((done, total, name)),
                    retry_delays=(0, 0, 0, 0),
                ).download(spec)
                self.assertEqual(_FlakyRangeHandler.request_count, 3)
                self.assertGreaterEqual(len(_FlakyRangeHandler.saw_ranges), 2)
                self.assertEqual(manager.file_path(spec, spec.files[0]).read_bytes(), data)
                self.assertTrue(manager.state(spec).ready)
                phases = [name for _done, _total, name in progress]
                self.assertTrue(any(name.startswith("重试 1/4 · ") for name in phases))
                self.assertTrue(any(name.startswith("重试 2/4 · ") for name in phases))
        finally:
            server.shutdown()
            server.server_close()

    def test_semantic_models_do_not_require_experimental_narration_model(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = ModelManager(directory, MODEL_REGISTRY)
            self.assertEqual({item.id for item in manager.capability_missing("semantic")}, {
                "bge-small-zh",
                "clip-vit-base-patch32",
            })
            self.assertEqual([item.id for item in manager.capability_missing("narration")], [
                "llama-cpp-runtime",
                "qwen2.5-3b-instruct"
            ])

    def test_verified_llama_runtime_extracts_required_files_safely(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "runtime.zip"
            with zipfile.ZipFile(archive_path, "w") as package:
                package.writestr("llama-completion.exe", b"test-executable")
                package.writestr("llama-common.dll", b"common")
                package.writestr("llama.dll", b"llama")
            data = archive_path.read_bytes()
            spec = ModelSpec(
                id="llama-cpp-runtime",
                name="测试运行时",
                category="运行时",
                capability="narration",
                description="测试",
                version="test",
                source_name="Test",
                source_url="https://example.invalid",
                license_name="Test",
                files=(ModelFile("runtime.zip", "https://example.invalid/runtime.zip", len(data)),),
            )
            manager = ModelManager(Path(directory) / "models", (spec,))
            target = manager.file_path(spec, spec.files[0])
            target.parent.mkdir(parents=True)
            target.write_bytes(data)
            manager.verify_and_record(spec)
            executable = manager.ensure_narration_runtime()
            self.assertTrue(executable.is_file())
            self.assertEqual(executable.read_bytes(), b"test-executable")

    def test_sha256_verification_can_be_cancelled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data = b"verification-block" * 100_000
            spec = make_spec("https://example.invalid", (("model.bin", data),))
            manager = ModelManager(directory, (spec,))
            target = manager.file_path(spec, spec.files[0])
            target.parent.mkdir(parents=True)
            target.write_bytes(data)
            with self.assertRaises(ModelDownloadCancelled):
                manager.verify_and_record(spec, cancel_check=lambda: True)
            self.assertEqual(manager.state(spec).code, "unverified")

    def test_official_sha256_mismatch_is_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data = b"same-size-but-wrong-content"
            spec = ModelSpec(
                id="hash-test",
                name="摘要测试",
                category="测试",
                capability="speech",
                description="摘要测试",
                version="1",
                source_name="Test",
                source_url="https://example.invalid",
                license_name="Test",
                files=(ModelFile("model.bin", "https://example.invalid/model.bin", len(data), "0" * 64),),
            )
            manager = ModelManager(directory, (spec,))
            target = manager.file_path(spec, spec.files[0])
            target.parent.mkdir(parents=True)
            target.write_bytes(data)
            with self.assertRaises(ModelIntegrityError):
                manager.verify_and_record(spec)
            self.assertFalse(target.exists())
            self.assertTrue(target.with_name(target.name + ".corrupt").is_file())
            self.assertEqual(manager.state(spec).code, "corrupt")

    def test_cancel_interrupts_a_blocked_network_read(self) -> None:
        _StallHandler.first_chunk_sent.clear()
        _StallHandler.release.clear()
        server = ThreadingHTTPServer(("127.0.0.1", 0), _StallHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            spec = ModelSpec(
                id="stall-test",
                name="阻塞取消测试",
                category="测试",
                capability="speech",
                description="阻塞取消测试",
                version="1",
                source_name="Local",
                source_url=base,
                license_name="Test",
                files=(ModelFile("model.bin", f"{base}/model.bin", 1024 * 1024),),
            )
            with tempfile.TemporaryDirectory() as directory:
                manager = ModelManager(directory, (spec,))
                downloader = ModelDownloader(manager)
                outcome: list[BaseException] = []

                def run_download() -> None:
                    try:
                        downloader.download(spec)
                    except BaseException as error:
                        outcome.append(error)

                worker = threading.Thread(target=run_download)
                worker.start()
                self.assertTrue(_StallHandler.first_chunk_sent.wait(2))
                started = time.monotonic()
                downloader.cancel()
                worker.join(1.5)
                elapsed = time.monotonic() - started
                self.assertFalse(worker.is_alive(), "取消后网络读取仍在阻塞")
                self.assertLess(elapsed, 1.5)
                self.assertTrue(outcome and isinstance(outcome[0], ModelDownloadCancelled))
        finally:
            _StallHandler.release.set()
            server.shutdown()
            server.server_close()

    def test_cancel_terminates_curl_fallback_and_keeps_part(self) -> None:
        if not ModelDownloader._curl_path():
            self.skipTest("系统没有 curl")
        _StallHandler.first_chunk_sent.clear()
        _StallHandler.release.clear()
        server = ThreadingHTTPServer(("127.0.0.1", 0), _StallHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            spec = ModelSpec(
                id="curl-cancel-test",
                name="备用通道取消测试",
                category="测试",
                capability="narration",
                description="测试",
                version="1",
                source_name="Local",
                source_url=base,
                license_name="Test",
                files=(ModelFile("runtime.zip", f"{base}/runtime.zip", 1024 * 1024),),
            )
            with tempfile.TemporaryDirectory() as directory:
                manager = ModelManager(directory, (spec,))
                downloader = ModelDownloader(manager)
                part = manager.file_path(spec, spec.files[0]).with_suffix(".zip.part")
                part.parent.mkdir(parents=True)
                outcome: list[BaseException] = []

                def run_curl() -> None:
                    try:
                        downloader._download_with_curl(spec, spec.files[0], part, 0)
                    except BaseException as error:
                        outcome.append(error)

                worker = threading.Thread(target=run_curl)
                worker.start()
                self.assertTrue(_StallHandler.first_chunk_sent.wait(2))
                downloader.cancel()
                worker.join(2)
                self.assertFalse(worker.is_alive())
                self.assertTrue(outcome and isinstance(outcome[0], ModelDownloadCancelled))
                self.assertTrue(part.is_file())
        finally:
            _StallHandler.release.set()
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
