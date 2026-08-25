from __future__ import annotations

import hashlib
import hmac
import http.client
import json
import os
import shutil
import ssl
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QStandardPaths


@dataclass(frozen=True, slots=True)
class ModelFile:
    path: str
    url: str
    size: int
    sha256: str | None = None


@dataclass(frozen=True, slots=True)
class ModelSpec:
    id: str
    name: str
    category: str
    capability: str
    description: str
    version: str
    source_name: str
    source_url: str
    license_name: str
    files: tuple[ModelFile, ...]

    @property
    def total_size(self) -> int:
        return sum(item.size for item in self.files)


@dataclass(frozen=True, slots=True)
class ModelState:
    code: str
    label: str
    ready: bool
    downloaded_size: int
    total_size: int
    detail: str = ""


class ModelDownloadCancelled(RuntimeError):
    pass


class ModelIntegrityError(RuntimeError):
    pass


class ModelTransferInterrupted(OSError):
    pass


def _hf(repo: str, path: str) -> str:
    return f"https://huggingface.co/{repo}/resolve/main/{path}"


MODEL_REGISTRY: tuple[ModelSpec, ...] = (
    ModelSpec(
        id="whisper-small",
        name="Whisper Small 多语言语音识别",
        category="语音",
        capability="speech",
        description="离线语音识别、逐句时间戳和自动字幕；支持中文。",
        version="whisper.cpp-main-small-2026-08",
        source_name="ggerganov/whisper.cpp",
        source_url="https://huggingface.co/ggerganov/whisper.cpp",
        license_name="MIT（以来源仓库为准）",
        files=(
            ModelFile(
                "ggml-small.bin",
                _hf("ggerganov/whisper.cpp", "ggml-small.bin"),
                487_601_967,
                "1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b",
            ),
        ),
    ),
    ModelSpec(
        id="face-yunet",
        name="YuNet 人脸检测",
        category="视觉",
        capability="face_subject",
        description="检测画面中的人脸位置和占比，不执行身份识别。",
        version="opencv-zoo-2023mar",
        source_name="OpenCV Zoo",
        source_url="https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet",
        license_name="Apache-2.0（以来源仓库为准）",
        files=(
            ModelFile(
                "face_detection_yunet_2023mar.onnx",
                "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
                232_589,
                "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
            ),
        ),
    ),
    ModelSpec(
        id="person-mediapipe",
        name="MediaPipe 人物检测",
        category="视觉",
        capability="face_subject",
        description="离线检测画面人物主体，用于人物优先和后续智能裁剪。",
        version="opencv-zoo-2023mar",
        source_name="OpenCV Zoo",
        source_url="https://github.com/opencv/opencv_zoo/tree/main/models/person_detection_mediapipe",
        license_name="Apache-2.0（以来源仓库为准）",
        files=(
            ModelFile(
                "person_detection_mediapipe_2023mar.onnx",
                "https://github.com/opencv/opencv_zoo/raw/main/models/person_detection_mediapipe/person_detection_mediapipe_2023mar.onnx",
                11_990_159,
                "47fd5599d6fa17608f03e0eb0ae230baa6e597d7e8a2c8199fe00abea55a701f",
            ),
        ),
    ),
    ModelSpec(
        id="bge-small-zh",
        name="BGE Small 中文文本语义",
        category="语义",
        capability="semantic",
        description="将字幕、标题和剪辑目标转换为中文语义向量。",
        version="bge-small-zh-v1.5-quantized",
        source_name="Xenova/bge-small-zh-v1.5",
        source_url="https://huggingface.co/Xenova/bge-small-zh-v1.5",
        license_name="MIT（以来源仓库为准）",
        files=(
            ModelFile("config.json", _hf("Xenova/bge-small-zh-v1.5", "config.json"), 716),
            ModelFile(
                "onnx/model_quantized.onnx",
                _hf("Xenova/bge-small-zh-v1.5", "onnx/model_quantized.onnx"),
                24_010_842,
                "15b717c382bcb518ba457b93ea6850ede7f4f1cd8937454aa06972366cd19bcc",
            ),
            ModelFile("tokenizer.json", _hf("Xenova/bge-small-zh-v1.5", "tokenizer.json"), 439_125),
            ModelFile(
                "tokenizer_config.json",
                _hf("Xenova/bge-small-zh-v1.5", "tokenizer_config.json"),
                367,
            ),
        ),
    ),
    ModelSpec(
        id="clip-vit-base-patch32",
        name="CLIP 画面语义",
        category="语义",
        capability="semantic",
        description="生成画面与文本向量，用于主题相关性和镜头多样性。",
        version="clip-vit-base-patch32-quantized",
        source_name="Xenova/clip-vit-base-patch32",
        source_url="https://huggingface.co/Xenova/clip-vit-base-patch32",
        license_name="MIT（以来源仓库为准）",
        files=(
            ModelFile("config.json", _hf("Xenova/clip-vit-base-patch32", "config.json"), 4_524),
            ModelFile("merges.txt", _hf("Xenova/clip-vit-base-patch32", "merges.txt"), 524_619),
            ModelFile(
                "onnx/text_model_quantized.onnx",
                _hf("Xenova/clip-vit-base-patch32", "onnx/text_model_quantized.onnx"),
                64_504_507,
                "73baab855d406190da9faa498cfedf65f15cf309f4cc7385b7b032e6d08e5c3a",
            ),
            ModelFile(
                "onnx/vision_model_quantized.onnx",
                _hf("Xenova/clip-vit-base-patch32", "onnx/vision_model_quantized.onnx"),
                89_117_001,
                "583fd1110a514667812fee7d684952aaf82a99b959760c8d7dca7e0ab9839299",
            ),
            ModelFile(
                "preprocessor_config.json",
                _hf("Xenova/clip-vit-base-patch32", "preprocessor_config.json"),
                520,
            ),
            ModelFile("tokenizer.json", _hf("Xenova/clip-vit-base-patch32", "tokenizer.json"), 2_224_119),
            ModelFile(
                "tokenizer_config.json",
                _hf("Xenova/clip-vit-base-patch32", "tokenizer_config.json"),
                775,
            ),
            ModelFile("vocab.json", _hf("Xenova/clip-vit-base-patch32", "vocab.json"), 862_328),
        ),
    ),
    ModelSpec(
        id="llama-cpp-runtime",
        name="llama.cpp Windows CPU 推理运行时",
        category="运行时",
        capability="narration",
        description="在本机加载 GGUF 解说模型；无需显卡，安装后可完全离线运行。",
        version="b10622-win-cpu-x64",
        source_name="ggml-org/llama.cpp",
        source_url="https://github.com/ggml-org/llama.cpp/releases/tag/b10622",
        license_name="MIT（以来源仓库与压缩包内许可证为准）",
        files=(
            ModelFile(
                "llama-b10622-bin-win-cpu-x64.zip",
                "https://github.com/ggml-org/llama.cpp/releases/download/b10622/llama-b10622-bin-win-cpu-x64.zip",
                18_067_843,
                "0f016b001d00a0cc25b955a5ae5eb3ce57a0b16adaa9142f8a3c3269e83fce0a",
            ),
        ),
    ),
    ModelSpec(
        id="qwen2.5-3b-instruct",
        name="Qwen2.5 3B 智能解说（实验）",
        category="解说",
        capability="narration",
        description="依据字幕和镜头事实生成可编辑中文解说草稿；精华编排不依赖它。",
        version="qwen2.5-3b-instruct-q4_k_m",
        source_name="Qwen/Qwen2.5-3B-Instruct-GGUF",
        source_url="https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF",
        license_name="Apache-2.0（以来源仓库为准）",
        files=(
            ModelFile(
                "qwen2.5-3b-instruct-q4_k_m.gguf",
                _hf("Qwen/Qwen2.5-3B-Instruct-GGUF", "qwen2.5-3b-instruct-q4_k_m.gguf"),
                2_104_932_768,
                "626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d",
            ),
        ),
    ),
)


def format_bytes(size: int) -> str:
    value = float(max(0, size))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit in {"B", "KB"} else f"{value:.2f} {unit}"
        value /= 1024
    return f"{size} B"


def default_model_root() -> Path:
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    base = Path(location) if location else Path.home() / "AppData" / "Local" / "Streamlight"
    return base / "models"


class ModelManager:
    def __init__(self, root: str | Path | None = None, registry: tuple[ModelSpec, ...] = MODEL_REGISTRY) -> None:
        self.root = Path(root).resolve() if root else default_model_root().resolve()
        self.registry = registry
        self.root.mkdir(parents=True, exist_ok=True)

    def spec(self, model_id: str) -> ModelSpec:
        for item in self.registry:
            if item.id == model_id:
                return item
        raise KeyError(f"未知模型：{model_id}")

    def model_dir(self, spec: ModelSpec) -> Path:
        return self.root / spec.id

    def file_path(self, spec: ModelSpec, file: ModelFile) -> Path:
        return self.model_dir(spec) / Path(file.path)

    def _manifest_path(self, spec: ModelSpec) -> Path:
        return self.model_dir(spec) / ".streamlight-model.json"

    def _read_manifest(self, spec: ModelSpec) -> dict:
        path = self._manifest_path(spec)
        if not path.is_file():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):
            return {}

    def state(self, spec: ModelSpec) -> ModelState:
        present = 0
        partial = 0
        corrupt: list[str] = []
        missing: list[str] = []
        for file in spec.files:
            target = self.file_path(spec, file)
            part = target.with_name(target.name + ".part")
            invalid = target.with_name(target.name + ".corrupt")
            if invalid.is_file():
                corrupt.append(file.path)
            elif target.is_file():
                size = target.stat().st_size
                present += min(size, file.size)
                if size != file.size:
                    corrupt.append(file.path)
            elif part.is_file():
                part_size = part.stat().st_size
                partial += min(part_size, file.size)
                missing.append(file.path)
            else:
                missing.append(file.path)
        downloaded = present + partial
        if corrupt:
            return ModelState("corrupt", "文件异常", False, downloaded, spec.total_size, f"大小异常：{corrupt[0]}")
        if missing:
            if downloaded:
                return ModelState("partial", "未完成", False, downloaded, spec.total_size, "可继续下载")
            return ModelState("missing", "缺失", False, 0, spec.total_size, "尚未下载")

        manifest = self._read_manifest(spec)
        manifest_files = manifest.get("files") if isinstance(manifest.get("files"), dict) else {}
        if manifest.get("version") != spec.version or any(
            not isinstance(manifest_files.get(file.path), dict)
            or manifest_files[file.path].get("size") != file.size
            or not manifest_files[file.path].get("sha256")
            or (file.sha256 and manifest_files[file.path].get("sha256") != file.sha256)
            for file in spec.files
        ):
            return ModelState("unverified", "待校验", False, spec.total_size, spec.total_size, "文件存在但没有有效校验记录")
        return ModelState("installed", "已安装", True, spec.total_size, spec.total_size, "完整性记录有效")

    def capability_ready(self, capability: str) -> bool:
        required = [spec for spec in self.registry if spec.capability == capability]
        return bool(required) and all(self.state(spec).ready for spec in required)

    def capability_missing(self, capability: str) -> list[ModelSpec]:
        return [spec for spec in self.registry if spec.capability == capability and not self.state(spec).ready]

    def ensure_narration_runtime(self) -> Path:
        spec = self.spec("llama-cpp-runtime")
        if not self.state(spec).ready:
            raise RuntimeError("llama.cpp 推理运行时尚未安装并校验")
        archive = self.file_path(spec, spec.files[0])
        runtime_dir = self.model_dir(spec) / "runtime"
        executable = runtime_dir / "llama-completion.exe"
        required = (executable, runtime_dir / "llama-common.dll", runtime_dir / "llama.dll")
        if all(path.is_file() for path in required):
            return executable

        pending = self.model_dir(spec) / "runtime.pending"
        if pending.is_dir():
            shutil.rmtree(pending)
        pending.mkdir(parents=True, exist_ok=True)
        pending_root = pending.resolve()
        try:
            with zipfile.ZipFile(archive) as package:
                for entry in package.infolist():
                    target = (pending / entry.filename).resolve()
                    if target != pending_root and pending_root not in target.parents:
                        raise ModelIntegrityError("推理运行时压缩包包含不安全路径，已拒绝解压")
                    package.extract(entry, pending)
            pending_required = (
                pending / "llama-completion.exe",
                pending / "llama-common.dll",
                pending / "llama.dll",
            )
            if not all(path.is_file() and path.stat().st_size > 0 for path in pending_required):
                raise ModelIntegrityError("推理运行时压缩包缺少必要的 EXE 或 DLL")
            if runtime_dir.is_dir():
                shutil.rmtree(runtime_dir)
            pending.replace(runtime_dir)
        except BaseException:
            if pending.is_dir():
                shutil.rmtree(pending)
            raise
        return executable

    def summary(self) -> tuple[int, int]:
        ready = sum(self.state(spec).ready for spec in self.registry)
        return ready, len(self.registry)

    def verify_and_record(
        self,
        spec: ModelSpec,
        progress: Callable[[int, int, str], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> None:
        callback = progress or (lambda _done, _total, _name: None)
        total = spec.total_size
        processed = 0
        records: dict[str, dict[str, object]] = {}
        for file in spec.files:
            target = self.file_path(spec, file)
            if not target.is_file() or target.stat().st_size != file.size:
                raise RuntimeError(f"模型文件缺失或大小异常：{file.path}")
            digest = hashlib.sha256()
            with target.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    if cancel_check and cancel_check():
                        raise ModelDownloadCancelled("模型校验已取消，可稍后重新校验")
                    digest.update(chunk)
                    processed += len(chunk)
                    callback(processed, total, file.path)
            actual_sha256 = digest.hexdigest()
            if file.sha256 and not hmac.compare_digest(actual_sha256, file.sha256):
                invalid = target.with_name(target.name + ".corrupt")
                if invalid.exists():
                    invalid.unlink()
                target.replace(invalid)
                manifest_path = self._manifest_path(spec)
                if manifest_path.exists():
                    manifest_path.unlink()
                raise ModelIntegrityError(
                    f"模型完整性校验失败：{file.path}\n"
                    f"应为：{file.sha256}\n实际：{actual_sha256}\n"
                    "异常文件已保留为 .corrupt，请点击“修复”重新下载。"
                )
            records[file.path] = {"size": file.size, "sha256": actual_sha256}
        manifest = {
            "model_id": spec.id,
            "version": spec.version,
            "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "files": records,
        }
        path = self._manifest_path(spec)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)

    def remove(self, spec: ModelSpec) -> None:
        target = self.model_dir(spec).resolve()
        if target.parent != self.root or not target.name:
            raise RuntimeError("拒绝删除模型目录之外的路径")
        if target.is_dir():
            shutil.rmtree(target)


DownloadProgress = Callable[[int, int, str], None]


class ModelDownloader:
    RETRY_DELAYS = (1.0, 2.0, 4.0, 8.0)
    RETRYABLE_HTTP_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})

    def __init__(
        self,
        manager: ModelManager,
        progress: DownloadProgress | None = None,
        retry_delays: tuple[float, ...] | None = None,
    ) -> None:
        self.manager = manager
        self.progress = progress or (lambda _done, _total, _message: None)
        delays = self.RETRY_DELAYS if retry_delays is None else retry_delays
        self.retry_delays = tuple(max(0.0, float(delay)) for delay in delays)
        self._cancel = threading.Event()
        self._response_lock = threading.Lock()
        self._active_response: Any | None = None
        self._process_lock = threading.Lock()
        self._active_process: subprocess.Popen[str] | None = None

    def cancel(self) -> None:
        self._cancel.set()
        with self._response_lock:
            response = self._active_response
        if response is not None:
            try:
                response.close()
            except BaseException:
                pass
        with self._process_lock:
            process = self._active_process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except BaseException:
                pass

    def _set_active_response(self, response: Any | None) -> None:
        with self._response_lock:
            self._active_response = response

    def _check_cancelled(self) -> None:
        if self._cancel.is_set():
            raise ModelDownloadCancelled("模型下载已取消，可稍后继续")

    @staticmethod
    def _curl_path() -> str | None:
        return shutil.which("curl.exe" if os.name == "nt" else "curl")

    def _download_with_curl(
        self,
        spec: ModelSpec,
        file: ModelFile,
        part: Path,
        completed_before_file: int,
    ) -> None:
        curl = self._curl_path()
        if not curl:
            raise RuntimeError("系统缺少 curl，无法使用 GitHub 备用下载通道")
        curl_part = part.with_name(part.name + ".curl")
        if part.is_file() and not curl_part.exists():
            part.replace(curl_part)
        elif part.is_file() and curl_part.is_file():
            if part.stat().st_size > curl_part.stat().st_size:
                curl_part.unlink()
                part.replace(curl_part)
            else:
                part.unlink()
        command = [
            curl,
            "--location",
            "--fail",
            "--silent",
            "--show-error",
            "--connect-timeout",
            "10",
            "--retry",
            "3",
            "--retry-delay",
            "1",
            "--continue-at",
            "-",
            "--output",
            str(curl_part),
            file.url,
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
        )
        with self._process_lock:
            self._active_process = process
        try:
            while process.poll() is None:
                self._check_cancelled()
                current = curl_part.stat().st_size if curl_part.is_file() else 0
                self.progress(
                    completed_before_file + current,
                    spec.total_size,
                    f"备用通道下载 · {file.path}",
                )
                self._cancel.wait(0.1)
            stdout, stderr = process.communicate()
            self._check_cancelled()
            if process.returncode:
                detail = (stderr or stdout or "curl 未返回错误详情").strip().splitlines()
                raise ModelTransferInterrupted("GitHub 备用下载失败：" + "\n".join(detail[-4:]))
            actual_size = curl_part.stat().st_size if curl_part.is_file() else 0
            if actual_size != file.size:
                raise ModelTransferInterrupted(
                    f"{file.path} 仅收到 {format_bytes(actual_size)} / {format_bytes(file.size)}"
                )
            self.progress(
                completed_before_file + actual_size,
                spec.total_size,
                f"备用通道下载 · {file.path}",
            )
        finally:
            if process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
            with self._process_lock:
                self._active_process = None
            curl_part_ready = self._wait_for_part_release(curl_part)
            if curl_part_ready:
                deadline = time.monotonic() + 1.5
                while True:
                    try:
                        curl_part.replace(part)
                        break
                    except PermissionError:
                        if time.monotonic() >= deadline:
                            raise RuntimeError("curl 已结束，但下载临时文件仍被系统占用，请稍后继续")
                        time.sleep(0.02)

    @staticmethod
    def _wait_for_part_release(part: Path, timeout: float = 1.5) -> bool:
        """Do not return from Windows cancellation while curl still owns the part file."""
        if os.name != "nt":
            return part.is_file()
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = (
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        )
        create_file.restype = wintypes.HANDLE
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (wintypes.HANDLE,)
        close_handle.restype = wintypes.BOOL
        delete_access = 0x00010000
        share_read_write_delete = 0x00000001 | 0x00000002 | 0x00000004
        open_existing = 3
        normal_attribute = 0x00000080
        invalid_handle = wintypes.HANDLE(-1).value
        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            handle = create_file(
                str(part),
                delete_access,
                share_read_write_delete,
                None,
                open_existing,
                normal_attribute,
                None,
            )
            if handle != invalid_handle:
                close_handle(handle)
                return True
            error = ctypes.get_last_error()
            if error in {2, 3}:
                return False
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.02)

    @staticmethod
    def _error_reason(error: BaseException) -> BaseException | str:
        return error.reason if isinstance(error, urllib.error.URLError) else error

    @staticmethod
    def _proxy_hint() -> str:
        proxy = urllib.request.getproxies().get("https")
        if not proxy:
            return ""
        try:
            parsed = urllib.parse.urlsplit(proxy if "://" in proxy else f"//{proxy}")
            host = parsed.hostname
            if not host:
                return ""
            label = f"{host}:{parsed.port}" if parsed.port else host
        except (TypeError, ValueError):
            return ""
        return (
            f"\n检测到 HTTPS 代理：{label}。若持续出现 TLS EOF，请切换代理节点、"
            "重启代理程序，或改用可正常访问模型来源的网络。"
        )

    def _is_retryable(self, error: BaseException) -> bool:
        if isinstance(error, urllib.error.HTTPError):
            return error.code in self.RETRYABLE_HTTP_CODES
        reason = self._error_reason(error)
        if isinstance(reason, ssl.SSLCertVerificationError):
            return False
        return isinstance(
            reason,
            (
                ssl.SSLError,
                http.client.HTTPException,
                TimeoutError,
                ConnectionError,
                OSError,
                ValueError,
            ),
        )

    def _raise_transfer_error(
        self,
        spec: ModelSpec,
        error: BaseException,
        retries_used: int,
    ) -> None:
        reason = self._error_reason(error)
        if isinstance(reason, ssl.SSLCertVerificationError):
            raise RuntimeError(
                f"TLS 证书校验失败：{spec.name} · {reason}\n"
                "请检查系统时间，以及 HTTPS 代理或安全软件是否替换了网站证书。"
                f"{self._proxy_hint()}"
            ) from error
        if isinstance(error, urllib.error.HTTPError):
            raise RuntimeError(f"下载请求失败（HTTP {error.code}）：{spec.name}") from error
        retry_text = f"已自动重试 {retries_used} 次" if retries_used else "未执行自动重试"
        raise RuntimeError(
            f"下载连接持续中断：{spec.name} · {reason}\n"
            f"{retry_text}，已保留下载进度；请检查网络或代理后再次点击下载继续。"
            f"{self._proxy_hint()}"
        ) from error

    def _wait_for_retry(
        self,
        spec: ModelSpec,
        file: ModelFile,
        part: Path,
        completed_before_file: int,
        retry_index: int,
    ) -> None:
        retry_number = retry_index + 1
        saved = part.stat().st_size if part.is_file() else 0
        self.progress(
            completed_before_file + saved,
            spec.total_size,
            f"重试 {retry_number}/{len(self.retry_delays)} · {file.path}",
        )
        if self._cancel.wait(self.retry_delays[retry_index]):
            raise ModelDownloadCancelled("模型下载已取消，可稍后继续")

    def download(self, spec: ModelSpec) -> None:
        model_dir = self.manager.model_dir(spec)
        model_dir.mkdir(parents=True, exist_ok=True)
        completed_before = 0
        for file in spec.files:
            target = self.manager.file_path(spec, file)
            if target.is_file() and target.stat().st_size == file.size:
                completed_before += file.size

        downloaded_total = completed_before
        for file in spec.files:
            self._check_cancelled()
            target = self.manager.file_path(spec, file)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_file() and target.stat().st_size == file.size:
                continue
            if target.exists():
                target.unlink()
            part = target.with_name(target.name + ".part")
            existing = part.stat().st_size if part.is_file() else 0
            if existing > file.size:
                part.unlink()
                existing = 0
            retries_used = 0
            completed_from_range = False
            hostname = (urllib.parse.urlsplit(file.url).hostname or "").casefold()
            used_curl = hostname == "github.com" and self._curl_path() is not None
            if used_curl:
                self._download_with_curl(spec, file, part, downloaded_total)
            while not used_curl:
                self._check_cancelled()
                existing = part.stat().st_size if part.is_file() else 0
                request = urllib.request.Request(
                    file.url,
                    headers={
                        "User-Agent": "Streamlight/2 ModelManager",
                        "Accept-Encoding": "identity",
                    },
                )
                if existing:
                    request.add_header("Range", f"bytes={existing}-")
                transfer_error: BaseException | None = None
                try:
                    response = urllib.request.urlopen(
                        request,
                        timeout=8,
                        context=ssl.create_default_context(),
                    )
                    self._set_active_response(response)
                    status = getattr(response, "status", response.getcode())
                    append = existing > 0 and status == 206
                    if existing and not append:
                        existing = 0
                    mode = "ab" if append else "wb"
                    current = existing
                    with response, part.open(mode) as stream:
                        while True:
                            self._check_cancelled()
                            chunk = response.read(256 * 1024)
                            if not chunk:
                                break
                            stream.write(chunk)
                            current += len(chunk)
                            self.progress(
                                downloaded_total + current,
                                spec.total_size,
                                f"下载 · {file.path}",
                            )
                    actual_size = part.stat().st_size
                    if actual_size != file.size:
                        raise ModelTransferInterrupted(
                            f"{file.path} 仅收到 {format_bytes(actual_size)} / {format_bytes(file.size)}"
                        )
                    break
                except ModelDownloadCancelled:
                    raise
                except urllib.error.HTTPError as error:
                    self._check_cancelled()
                    if error.code == 416 and existing == file.size:
                        part.replace(target)
                        downloaded_total += file.size
                        completed_from_range = True
                        break
                    transfer_error = error
                except (
                    urllib.error.URLError,
                    ssl.SSLError,
                    http.client.HTTPException,
                    TimeoutError,
                    ConnectionError,
                    OSError,
                    ValueError,
                ) as error:
                    self._check_cancelled()
                    transfer_error = error
                finally:
                    self._set_active_response(None)

                if transfer_error is None:
                    raise RuntimeError(f"下载连接异常：{spec.name}")
                if not self._is_retryable(transfer_error) or retries_used >= len(self.retry_delays):
                    self._raise_transfer_error(spec, transfer_error, retries_used)
                self._wait_for_retry(spec, file, part, downloaded_total, retries_used)
                retries_used += 1

            if completed_from_range:
                continue
            part.replace(target)
            invalid = target.with_name(target.name + ".corrupt")
            if invalid.exists():
                invalid.unlink()
            downloaded_total += file.size
        self.manager.verify_and_record(
            spec,
            lambda done, total, name: self.progress(done, total, f"校验 · {name}"),
            self._cancel.is_set,
        )
