from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streamlight.model_manager import (
    MODEL_REGISTRY,
    ModelDownloadCancelled,
    ModelDownloader,
    ModelManager,
)


def run() -> None:
    spec = next(item for item in MODEL_REGISTRY if item.id == "person-mediapipe")
    with tempfile.TemporaryDirectory(prefix="streamlight-transfer-smoke-") as directory:
        manager = ModelManager(directory, (spec,))
        cancelled_downloader: ModelDownloader | None = None
        progress_samples: list[tuple[float, int, int, str]] = []

        def cancel_after_one_megabyte(completed: int, total: int, phase: str) -> None:
            progress_samples.append((time.monotonic(), completed, total, phase))
            if "下载" in phase and completed >= 1024 * 1024:
                assert cancelled_downloader is not None
                cancelled_downloader.cancel()

        cancelled_downloader = ModelDownloader(manager, cancel_after_one_megabyte)
        started = time.monotonic()
        try:
            cancelled_downloader.download(spec)
        except ModelDownloadCancelled:
            pass
        else:
            raise RuntimeError("真实模型下载未在进度阈值处取消")
        cancel_elapsed = time.monotonic() - started

        target = manager.file_path(spec, spec.files[0])
        part = target.with_name(target.name + ".part")
        if not part.is_file() or not 0 < part.stat().st_size < spec.total_size:
            raise RuntimeError("取消后未保留有效的 .part 续传文件")
        if not progress_samples or progress_samples[-1][2] != spec.total_size:
            raise RuntimeError("真实下载进度未报告模型总大小")

        resumed_samples: list[tuple[int, int, str]] = []
        ModelDownloader(
            manager,
            lambda completed, total, phase: resumed_samples.append((completed, total, phase)),
        ).download(spec)
        state = manager.state(spec)
        if not state.ready:
            raise RuntimeError(f"续传和官方 SHA-256 校验后模型未就绪：{state}")
        if not any(phase.startswith("校验") for _done, _total, phase in resumed_samples):
            raise RuntimeError("续传完成后没有执行本地 SHA-256 校验")

        print(
            "MODEL_TRANSFER_OK "
            f"cancel_seconds={cancel_elapsed:.3f} "
            f"part_bytes={progress_samples[-1][1]} "
            f"final_bytes={target.stat().st_size} "
            f"progress_events={len(progress_samples) + len(resumed_samples)}"
        )


if __name__ == "__main__":
    run()
