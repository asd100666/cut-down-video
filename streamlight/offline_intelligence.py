from __future__ import annotations

import math
import os
import subprocess
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .dependencies import locate_ffmpeg
from .editor_engine import ExportCancelled
from .editor_models import AnalysisEvidence, MediaAsset, SubtitleCue, new_id
from .model_manager import ModelManager


IntelligenceProgress = Callable[[float, str], None]


@dataclass(slots=True)
class IntelligenceAnalysis:
    evidence: list[AnalysisEvidence] = field(default_factory=list)
    subtitles: list[SubtitleCue] = field(default_factory=list)
    sample_scores: dict[float, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class OfflineIntelligenceAnalyzer:
    """Runs optional local models and returns evidence without changing source media."""

    def __init__(
        self,
        model_manager: ModelManager,
        progress_callback: IntelligenceProgress | None = None,
    ) -> None:
        self.model_manager = model_manager
        self.progress_callback = progress_callback or (lambda _percent, _message: None)
        self._cancel_event = threading.Event()
        self._process: subprocess.Popen[bytes] | None = None

    def cancel(self) -> None:
        self._cancel_event.set()
        if self._process and self._process.poll() is None:
            self._process.terminate()

    def _check_cancelled(self) -> None:
        if self._cancel_event.is_set():
            raise ExportCancelled("本地智能分析已取消")

    @staticmethod
    def _creation_flags() -> int:
        return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

    def analyze(
        self,
        asset: MediaAsset,
        sample_times: list[float],
        *,
        speech_enabled: bool,
        face_enabled: bool,
        semantic_enabled: bool,
    ) -> IntelligenceAnalysis:
        result = IntelligenceAnalysis(sample_scores={time: 0.0 for time in sample_times})
        if speech_enabled:
            try:
                self.progress_callback(0.0, f"正在识别语音：{asset.name}")
                result.subtitles, speech_evidence = self._transcribe(asset)
                result.evidence.extend(speech_evidence)
            except ExportCancelled:
                raise
            except BaseException as error:
                result.warnings.append(f"语音识别已回退：{error}")

        if face_enabled:
            try:
                self.progress_callback(35.0, f"正在分析人脸、人物与画质：{asset.name}")
                visual_evidence, visual_scores = self._analyze_visual(asset, sample_times)
                result.evidence.extend(visual_evidence)
                for time, score in visual_scores.items():
                    result.sample_scores[time] = result.sample_scores.get(time, 0.0) + score * 0.6
            except ExportCancelled:
                raise
            except BaseException as error:
                result.warnings.append(f"人物视觉分析已回退：{error}")

        if semantic_enabled:
            try:
                self.progress_callback(68.0, f"正在计算语义与画面多样性：{asset.name}")
                semantic_evidence, semantic_scores = self._analyze_semantic(
                    asset,
                    sample_times,
                    result.subtitles,
                )
                result.evidence.extend(semantic_evidence)
                for time, score in semantic_scores.items():
                    result.sample_scores[time] = result.sample_scores.get(time, 0.0) + score * 0.4
            except ExportCancelled:
                raise
            except BaseException as error:
                result.warnings.append(f"语义分析已回退：{error}")
        elif result.subtitles:
            for time in sample_times:
                activity = self._speech_activity(time, result.subtitles)
                result.sample_scores[time] = min(1.0, result.sample_scores.get(time, 0.0) + activity * 0.25)

        result.sample_scores = {time: max(0.0, min(1.0, score)) for time, score in result.sample_scores.items()}
        return result

    def _transcribe(self, asset: MediaAsset) -> tuple[list[SubtitleCue], list[AnalysisEvidence]]:
        self._check_cancelled()
        spec = self.model_manager.spec("whisper-small")
        if not self.model_manager.state(spec).ready:
            raise RuntimeError("Whisper Small 模型未安装或未校验")
        model_path = self.model_manager.file_path(spec, spec.files[0])
        ffmpeg, _source = locate_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("未找到 FFmpeg，无法提取识别音频")

        with tempfile.TemporaryDirectory(prefix="streamlight-asr-") as directory:
            wav_path = Path(directory) / "audio.wav"
            command = [
                ffmpeg,
                "-y",
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                asset.path,
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(wav_path),
            ]
            self._process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=self._creation_flags(),
            )
            _stdout, stderr = self._process.communicate()
            code = self._process.returncode
            self._process = None
            self._check_cancelled()
            if code:
                raise RuntimeError(stderr.decode("utf-8", errors="replace").strip() or "音频提取失败")
            if not wav_path.is_file() or wav_path.stat().st_size <= 44:
                raise RuntimeError("素材不包含可识别的音频")

            try:
                from pywhispercpp.model import Model
            except ImportError as error:
                raise RuntimeError("缺少 pywhispercpp 离线推理运行时") from error
            model = Model(model=str(model_path), redirect_whispercpp_logs_to=False)
            segments = model.transcribe(
                str(wav_path),
                abort_callback=self._cancel_event.is_set,
                extract_probability=True,
                language="",
                detect_language=True,
                print_progress=False,
            )

        subtitles: list[SubtitleCue] = []
        evidence: list[AnalysisEvidence] = []
        for segment in segments:
            text = str(segment.text).strip()
            if not text:
                continue
            start = max(0.0, float(segment.t0) * 0.01)
            end = min(asset.duration, max(start + 0.01, float(segment.t1) * 0.01))
            probability = float(segment.probability)
            confidence = probability if math.isfinite(probability) else 0.0
            cue = SubtitleCue(new_id("subtitle"), asset.id, start, end, text, confidence)
            subtitles.append(cue)
            evidence.append(
                AnalysisEvidence(
                    id=new_id("evidence"),
                    kind="speech",
                    asset_id=asset.id,
                    start=start,
                    end=end,
                    score=max(0.0, min(1.0, confidence)),
                    label=text,
                    details={"subtitle_id": cue.id, "model": spec.id},
                )
            )
        return subtitles, evidence

    def transcribe(self, asset: MediaAsset) -> tuple[list[SubtitleCue], list[AnalysisEvidence]]:
        """Public cancellable ASR entry point for the subtitle-track workflow."""
        return self._transcribe(asset)

    @staticmethod
    def _read_frame(capture, time: float):
        import cv2

        capture.set(cv2.CAP_PROP_POS_MSEC, max(0.0, time) * 1000.0)
        ok, frame = capture.read()
        return frame if ok else None

    def _analyze_visual(
        self,
        asset: MediaAsset,
        sample_times: list[float],
    ) -> tuple[list[AnalysisEvidence], dict[float, float]]:
        try:
            import cv2
            import numpy as np
        except ImportError as error:
            raise RuntimeError("缺少 OpenCV/Numpy 离线视觉运行时") from error
        face_spec = self.model_manager.spec("face-yunet")
        person_spec = self.model_manager.spec("person-mediapipe")
        if not self.model_manager.state(face_spec).ready or not self.model_manager.state(person_spec).ready:
            raise RuntimeError("YuNet 或 MediaPipe 人物模型未安装并校验")
        face_path = str(self.model_manager.file_path(face_spec, face_spec.files[0]))
        person_path = str(self.model_manager.file_path(person_spec, person_spec.files[0]))
        face_detector = cv2.FaceDetectorYN.create(face_path, "", (320, 320), 0.65, 0.3, 50)
        person_net = cv2.dnn.readNet(person_path)
        capture = cv2.VideoCapture(asset.path)
        if not capture.isOpened():
            raise RuntimeError("无法打开视频画面")

        evidence: list[AnalysisEvidence] = []
        scores: dict[float, float] = {}
        try:
            for index, time in enumerate(sample_times):
                self._check_cancelled()
                frame = self._read_frame(capture, time)
                if frame is None:
                    continue
                height, width = frame.shape[:2]
                face_detector.setInputSize((width, height))
                _retval, faces = face_detector.detect(frame)
                face_count = 0 if faces is None else len(faces)
                face_area = 0.0
                if faces is not None:
                    face_area = float(sum(max(0.0, row[2]) * max(0.0, row[3]) for row in faces)) / max(1, width * height)
                face_score = min(1.0, face_count * 0.35 + face_area * 3.0)

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
                rgb = (rgb - 0.5) * 2.0
                ratio = min(224.0 / height, 224.0 / width)
                resized = cv2.resize(rgb, (max(1, round(width * ratio)), max(1, round(height * ratio))))
                pad_y = 224 - resized.shape[0]
                pad_x = 224 - resized.shape[1]
                blob = cv2.copyMakeBorder(
                    resized,
                    pad_y // 2,
                    pad_y - pad_y // 2,
                    pad_x // 2,
                    pad_x - pad_x // 2,
                    cv2.BORDER_CONSTANT,
                    value=(0, 0, 0),
                ).transpose(2, 0, 1)[None, ...]
                person_net.setInput(blob)
                outputs = person_net.forward(person_net.getUnconnectedOutLayersNames())
                logits = np.asarray(outputs[1])[0, :, 0].astype(np.float64)
                logits = np.clip(logits, -50.0, 50.0)
                person_score = float(np.max(1.0 / (1.0 + np.exp(-logits)))) if logits.size else 0.0

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                sharpness = min(1.0, math.log1p(float(cv2.Laplacian(gray, cv2.CV_64F).var())) / math.log1p(1200.0))
                exposure = max(0.0, 1.0 - abs(float(gray.mean()) - 127.5) / 127.5)
                contrast = min(1.0, float(gray.std()) / 64.0)
                quality = sharpness * 0.5 + exposure * 0.25 + contrast * 0.25
                combined = face_score * 0.45 + person_score * 0.35 + quality * 0.20
                scores[time] = combined
                evidence.append(
                    AnalysisEvidence(
                        id=new_id("evidence"),
                        kind="visual",
                        asset_id=asset.id,
                        start=time,
                        end=min(asset.duration, time + 0.01),
                        score=combined,
                        label=f"人脸 {face_count} · 人物 {person_score:.2f} · 画质 {quality:.2f}",
                        details={
                            "face_count": face_count,
                            "face_area_ratio": round(face_area, 6),
                            "person_score": round(person_score, 6),
                            "quality_score": round(quality, 6),
                            "models": [face_spec.id, person_spec.id],
                        },
                    )
                )
                self.progress_callback(35.0 + 30.0 * (index + 1) / max(1, len(sample_times)), f"视觉采样 {index + 1}/{len(sample_times)}")
        finally:
            capture.release()
        return evidence, scores

    @staticmethod
    def _normalize_rows(values):
        import numpy as np

        array = np.asarray(values, dtype=np.float32)
        norms = np.linalg.norm(array, axis=1, keepdims=True)
        return array / np.maximum(norms, 1e-12)

    def _text_embeddings(self, texts: list[str]):
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer

        spec = self.model_manager.spec("bge-small-zh")
        if not self.model_manager.state(spec).ready:
            raise RuntimeError("BGE 中文语义模型未安装并校验")
        tokenizer = Tokenizer.from_file(str(self.model_manager.model_dir(spec) / "tokenizer.json"))
        tokenizer.enable_truncation(max_length=512)
        tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        encodings = tokenizer.encode_batch(texts)
        ids = np.asarray([item.ids for item in encodings], dtype=np.int64)
        masks = np.asarray([item.attention_mask for item in encodings], dtype=np.int64)
        type_ids = np.asarray([item.type_ids for item in encodings], dtype=np.int64)
        session = ort.InferenceSession(
            str(self.model_manager.model_dir(spec) / "onnx" / "model_quantized.onnx"),
            providers=["CPUExecutionProvider"],
        )
        feeds = {}
        for input_meta in session.get_inputs():
            if input_meta.name == "input_ids":
                feeds[input_meta.name] = ids
            elif input_meta.name == "attention_mask":
                feeds[input_meta.name] = masks
            elif input_meta.name == "token_type_ids":
                feeds[input_meta.name] = type_ids
        outputs = session.run(None, feeds)
        tensor = next((np.asarray(item) for item in outputs if np.asarray(item).ndim == 3), np.asarray(outputs[0]))
        if tensor.ndim == 3:
            weighted = tensor * masks[:, :, None]
            tensor = weighted.sum(axis=1) / np.maximum(masks.sum(axis=1, keepdims=True), 1)
        return self._normalize_rows(tensor)

    def _vision_embeddings(self, asset: MediaAsset, sample_times: list[float]):
        import cv2
        import numpy as np
        import onnxruntime as ort

        spec = self.model_manager.spec("clip-vit-base-patch32")
        if not self.model_manager.state(spec).ready:
            raise RuntimeError("CLIP 画面语义模型未安装并校验")
        capture = cv2.VideoCapture(asset.path)
        frames = []
        valid_times = []
        mean = np.asarray([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
        std = np.asarray([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)
        try:
            for time in sample_times:
                self._check_cancelled()
                frame = self._read_frame(capture, time)
                if frame is None:
                    continue
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb = cv2.resize(rgb, (224, 224), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
                frames.append(((rgb - mean) / std).transpose(2, 0, 1))
                valid_times.append(time)
        finally:
            capture.release()
        if not frames:
            return [], np.empty((0, 1), dtype=np.float32)
        session = ort.InferenceSession(
            str(self.model_manager.model_dir(spec) / "onnx" / "vision_model_quantized.onnx"),
            providers=["CPUExecutionProvider"],
        )
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: np.stack(frames).astype(np.float32)})
        arrays = [np.asarray(item) for item in outputs]
        tensor = next((item for item in arrays if item.ndim == 2), arrays[0])
        if tensor.ndim == 3:
            tensor = tensor.mean(axis=1)
        return valid_times, self._normalize_rows(tensor)

    @staticmethod
    def _speech_text(time: float, subtitles: list[SubtitleCue]) -> str:
        nearby = [cue.text for cue in subtitles if cue.start - 1.0 <= time <= cue.end + 1.0]
        return " ".join(nearby).strip()

    @staticmethod
    def _speech_activity(time: float, subtitles: list[SubtitleCue]) -> float:
        matches = [cue for cue in subtitles if cue.start - 0.5 <= time <= cue.end + 0.5]
        if not matches:
            return 0.0
        length_score = min(1.0, sum(len(cue.text) for cue in matches) / 36.0)
        confidence = sum(max(0.0, cue.confidence) for cue in matches) / len(matches)
        return min(1.0, length_score * 0.65 + confidence * 0.35)

    def _analyze_semantic(
        self,
        asset: MediaAsset,
        sample_times: list[float],
        subtitles: list[SubtitleCue],
    ) -> tuple[list[AnalysisEvidence], dict[float, float]]:
        import numpy as np

        texts = [self._speech_text(time, subtitles) or "无对白画面" for time in sample_times]
        text_vectors = self._text_embeddings(texts)
        vision_times, vision_vectors = self._vision_embeddings(asset, sample_times)
        vision_by_time = {time: vision_vectors[index] for index, time in enumerate(vision_times)}
        evidence: list[AnalysisEvidence] = []
        scores: dict[float, float] = {}
        previous_text = []
        previous_vision = []
        for index, time in enumerate(sample_times):
            self._check_cancelled()
            text_vector = text_vectors[index]
            text_novelty = 1.0 if not previous_text else 1.0 - max(float(np.dot(text_vector, item)) for item in previous_text)
            previous_text.append(text_vector)
            vision_vector = vision_by_time.get(time)
            if vision_vector is None:
                vision_novelty = 0.0
            else:
                vision_novelty = 1.0 if not previous_vision else 1.0 - max(
                    float(np.dot(vision_vector, item)) for item in previous_vision
                )
                previous_vision.append(vision_vector)
            speech_activity = self._speech_activity(time, subtitles)
            score = max(0.0, min(1.0, text_novelty * 0.35 + vision_novelty * 0.35 + speech_activity * 0.30))
            scores[time] = score
            evidence.append(
                AnalysisEvidence(
                    id=new_id("evidence"),
                    kind="semantic",
                    asset_id=asset.id,
                    start=time,
                    end=min(asset.duration, time + 0.01),
                    score=score,
                    label=f"语义新颖度 {text_novelty:.2f} · 画面多样性 {vision_novelty:.2f}",
                    details={
                        "text": texts[index],
                        "text_novelty": round(text_novelty, 6),
                        "vision_novelty": round(vision_novelty, 6),
                        "speech_activity": round(speech_activity, 6),
                        "models": ["bge-small-zh", "clip-vit-base-patch32"],
                    },
                )
            )
        return evidence, scores
