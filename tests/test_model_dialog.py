from __future__ import annotations

import hashlib
import os
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from streamlight.model_dialog import ModelManagerDialog, TransferRateMeter, format_duration
from streamlight.model_manager import ModelDownloadCancelled, ModelFile, ModelManager, ModelSpec


class ModelDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_rate_meter_reports_speed_eta_and_resets_between_phases(self) -> None:
        meter = TransferRateMeter(window_seconds=4)
        speed, eta = meter.update("下载", 0, 4 * 1024 * 1024, now=0)
        self.assertEqual(speed, 0)
        self.assertIsNone(eta)
        speed, eta = meter.update("下载", 2 * 1024 * 1024, 4 * 1024 * 1024, now=2)
        self.assertAlmostEqual(speed, 1024 * 1024)
        self.assertAlmostEqual(eta or 0, 2.0)
        speed, eta = meter.update("校验", 1024, 4096, now=3)
        self.assertEqual(speed, 0)
        self.assertIsNone(eta)
        self.assertEqual(format_duration(65), "1分05秒")

    def test_manual_verification_can_run_repeatedly_without_closing_dialog(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data = b"verified-dialog-data" * 100_000
            digest = hashlib.sha256(data).hexdigest()
            spec = ModelSpec(
                id="dialog-verify",
                name="界面校验模型",
                category="测试",
                capability="speech",
                description="界面校验测试",
                version="1",
                source_name="Local",
                source_url="https://example.invalid",
                license_name="Test",
                files=(ModelFile("model.bin", "https://example.invalid/model.bin", len(data), digest),),
            )
            manager = ModelManager(Path(directory) / "models", (spec,))
            target = manager.file_path(spec, spec.files[0])
            target.parent.mkdir(parents=True)
            target.write_bytes(data)
            dialog = ModelManagerDialog(manager)
            dialog.show()
            for _attempt in range(2):
                dialog.start_verify(spec)
                deadline = time.monotonic() + 5
                while dialog._thread is not None and time.monotonic() < deadline:
                    self.app.processEvents()
                    time.sleep(0.005)
                self.app.processEvents()
                self.assertIsNone(dialog._thread)
                self.assertTrue(dialog.isVisible())
                self.assertTrue(manager.state(spec).ready)
                self.assertIn("校验", dialog.progress_title.text())
            dialog.close()

    def test_manual_verification_can_be_cancelled_without_closing_dialog(self) -> None:
        class SlowVerifyManager(ModelManager):
            def verify_and_record(self, spec, progress=None, cancel_check=None) -> None:
                callback = progress or (lambda _done, _total, _name: None)
                for completed in range(1, 401):
                    if cancel_check and cancel_check():
                        raise ModelDownloadCancelled("模型校验已取消")
                    callback(completed, 400, spec.files[0].path)
                    time.sleep(0.005)

        with tempfile.TemporaryDirectory() as directory:
            spec = ModelSpec(
                id="dialog-cancel-verify",
                name="可取消校验模型",
                category="测试",
                capability="speech",
                description="界面取消校验测试",
                version="1",
                source_name="Local",
                source_url="https://example.invalid",
                license_name="Test",
                files=(ModelFile("model.bin", "https://example.invalid/model.bin", 400),),
            )
            manager = SlowVerifyManager(Path(directory) / "models", (spec,))
            target = manager.file_path(spec, spec.files[0])
            target.parent.mkdir(parents=True)
            target.write_bytes(b"x" * spec.files[0].size)
            dialog = ModelManagerDialog(manager)
            dialog.show()
            dialog.start_verify(spec)

            progress_deadline = time.monotonic() + 2
            while dialog.progress_bar.value() == 0 and time.monotonic() < progress_deadline:
                self.app.processEvents()
                time.sleep(0.005)
            self.assertGreater(dialog.progress_bar.value(), 0)

            cancelled_at = time.monotonic()
            dialog.cancel_active()
            while dialog._thread is not None and time.monotonic() - cancelled_at < 2:
                self.app.processEvents()
                time.sleep(0.005)
            self.app.processEvents()

            self.assertLess(time.monotonic() - cancelled_at, 2)
            self.assertIsNone(dialog._thread)
            self.assertTrue(dialog.isVisible())
            self.assertIn("校验已取消", dialog.progress_title.text())
            self.assertFalse(dialog.cancel_button.isVisible())
            dialog.close()


if __name__ == "__main__":
    unittest.main()
