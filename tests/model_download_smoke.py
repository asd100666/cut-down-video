from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streamlight.model_manager import MODEL_REGISTRY, ModelDownloader, ModelManager


def run() -> None:
    spec = next(item for item in MODEL_REGISTRY if item.id == "face-yunet")
    with tempfile.TemporaryDirectory(prefix="streamlight-model-smoke-") as directory:
        manager = ModelManager(directory, (spec,))
        ModelDownloader(manager).download(spec)
        state = manager.state(spec)
        target = manager.file_path(spec, spec.files[0])
        if not state.ready:
            raise RuntimeError(f"下载后模型未就绪：{state}")
        if target.stat().st_size != 232_589:
            raise RuntimeError(f"模型大小异常：{target.stat().st_size}")
        print(f"MODEL_DOWNLOAD_OK model={spec.id} bytes={target.stat().st_size} status={state.code}")


if __name__ == "__main__":
    run()
