from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streamlight.narration_engine import NarrationSynthesizer


def run() -> Path:
    output_dir = Path(tempfile.mkdtemp(prefix="streamlight-narration-smoke-"))
    output = output_dir / "voice.wav"
    asset = NarrationSynthesizer().synthesize(
        "这是一段完全离线生成的智能解说测试。",
        output,
        rate=0,
    )
    if not output.is_file() or output.stat().st_size <= 44 or asset.duration <= 0:
        raise RuntimeError("系统没有生成有效的离线解说音频")
    print(
        f"NARRATION_OK path={output} bytes={output.stat().st_size} "
        f"duration={asset.duration:.3f}"
    )
    return output


if __name__ == "__main__":
    run()
