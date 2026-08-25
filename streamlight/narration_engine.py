from __future__ import annotations

import base64
import os
import subprocess
import tempfile
import threading
import re
from pathlib import Path
from typing import Callable

from .editor_engine import ExportCancelled, probe_media
from .editor_models import EditProject, MediaAsset
from .model_manager import ModelManager


def build_narration_draft(project: EditProject, style: str = "summary", max_chars: int = 420) -> str:
    seen: set[str] = set()
    transcript: list[str] = []
    for _index, _start, _end, cue in project.timeline_subtitle_instances():
        text = cue.text.strip()
        if text and text not in seen:
            seen.add(text)
            transcript.append(text)
    if transcript:
        source = transcript
    else:
        source = [
            f"{clip.name}，{clip.selection_reason or '呈现主要画面'}"
            for clip in project.clips
        ]
    if not source:
        return ""
    limit = max(80, int(max_chars))
    selected: list[str] = []
    if len(source) <= 8:
        selected = source
    else:
        for index in range(8):
            selected.append(source[round(index * (len(source) - 1) / 7)])
    body = "。".join(item.rstrip("。！？!? ") for item in selected if item.strip())
    prefixes = {
        "summary": "这段视频的重点是：",
        "story": "画面从这里开始。接下来，",
        "knowledge": "先看核心信息。",
    }
    ending = "。以上就是这段内容的主要脉络。"
    return (prefixes.get(style, prefixes["summary"]) + body + ending)[:limit].rstrip("，。") + "。"


def build_narration_facts(project: EditProject, max_chars: int = 6000) -> str:
    facts = [f"项目：{project.name}；成片时长约 {project.duration:.1f} 秒。"]
    seen_subtitles: set[str] = set()
    for _index, start, end, cue in project.timeline_subtitle_instances():
        text = cue.text.strip()
        if text and text not in seen_subtitles:
            seen_subtitles.add(text)
            facts.append(f"{start:.1f}-{end:.1f} 秒对白：{text}")
    for index, (clip, start, end) in enumerate(project.clip_timeline_ranges(), start=1):
        reason = clip.selection_reason.strip() or "人工保留镜头"
        facts.append(f"镜头 {index}（{start:.1f}-{end:.1f} 秒）：{clip.name}；依据：{reason}")
    value = "\n".join(facts)
    return value[: max(500, int(max_chars))]


class LocalNarrationGenerator:
    def __init__(
        self,
        model_manager: ModelManager,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> None:
        self.model_manager = model_manager
        self.progress_callback = progress_callback or (lambda _percent, _message: None)
        self._cancel_event = threading.Event()
        self._process: subprocess.Popen[str] | None = None

    def cancel(self) -> None:
        self._cancel_event.set()
        process = self._process
        if process and process.poll() is None:
            process.terminate()

    @staticmethod
    def _clean_generation(text: str, max_chars: int) -> str:
        value = str(text).replace("[end of text]", "").strip()
        value = re.sub(r"<\|(?:im_start|im_end|endoftext)\|>", "", value).strip()
        value = re.sub(r"^(?:assistant|助手)\s*[:：]\s*", "", value, flags=re.IGNORECASE)
        limit = max(80, int(max_chars))
        if len(value) > limit:
            shortened = value[:limit]
            sentence_end = max(shortened.rfind(mark) for mark in "。！？")
            value = shortened[: sentence_end + 1] if sentence_end >= limit // 2 else shortened.rstrip("，；： ") + "。"
        if not value:
            raise RuntimeError("本地模型没有生成有效的解说文字")
        return value

    def generate(self, project: EditProject, style: str, max_chars: int = 420) -> tuple[str, dict]:
        if not self.model_manager.capability_ready("narration"):
            missing = "、".join(spec.name for spec in self.model_manager.capability_missing("narration"))
            raise RuntimeError(f"智能解说组件尚未就绪：{missing}")
        self.progress_callback(5.0, "正在准备本地 Qwen 解说模型")
        executable = self.model_manager.ensure_narration_runtime()
        model_spec = self.model_manager.spec("qwen2.5-3b-instruct")
        model_path = self.model_manager.file_path(model_spec, model_spec.files[0])
        if self._cancel_event.is_set():
            raise ExportCancelled("解说草稿生成已取消")

        style_names = {"summary": "精华概述", "story": "剧情解说", "knowledge": "知识总结"}
        facts = build_narration_facts(project)
        system_prompt = (
            "你是专业的视频剪辑解说助手。只能依据用户提供的字幕、镜头名称和选择依据写作，"
            "不得补充未提供的人名、事件、因果、结局或背景。语言自然、紧凑、适合直接配音。"
            "只输出解说正文，不要标题、分析、列表、引号或说明。"
        )
        user_prompt = (
            f"解说风格：{style_names.get(style, '精华概述')}。\n"
            f"长度：不超过 {max(80, int(max_chars))} 个中文字符。\n"
            "素材事实如下：\n"
            f"{facts}\n"
            "请按时间顺序写成一段连贯解说。"
        )
        chat_prompt = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{user_prompt}<|im_end|>\n"
            "<|im_start|>assistant\n"
        )
        threads = max(2, min(8, max(2, (os.cpu_count() or 4) - 1)))
        predicted_tokens = max(128, min(768, round(max(80, int(max_chars)) * 1.6)))
        command = [
            str(executable),
            "--model",
            str(model_path),
            "--offline",
            "--device",
            "none",
            "--n-gpu-layers",
            "0",
            "--ctx-size",
            "4096",
            "--predict",
            str(predicted_tokens),
            "--threads",
            str(threads),
            "--batch-size",
            "512",
            "--temp",
            "0.35",
            "--top-p",
            "0.90",
            "--repeat-penalty",
            "1.10",
            "--seed",
            "42",
            "--prompt",
            chat_prompt,
            "--no-conversation",
            "--simple-io",
            "--no-display-prompt",
            "--log-verbosity",
            "1",
        ]
        self.progress_callback(20.0, "正在加载 Qwen2.5 3B（CPU）")
        self._process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
            cwd=str(executable.parent),
        )
        try:
            self.progress_callback(35.0, "Qwen 正在依据字幕和镜头生成解说草稿")
            stdout, stderr = self._process.communicate(timeout=300)
            return_code = self._process.returncode
        except subprocess.TimeoutExpired as error:
            self._process.kill()
            self._process.communicate()
            raise RuntimeError("本地模型生成超过 5 分钟，已停止；可缩短解说长度后重试") from error
        finally:
            self._process = None
        if self._cancel_event.is_set():
            raise ExportCancelled("解说草稿生成已取消")
        if return_code:
            detail = (stderr or stdout or "llama.cpp 未返回错误详情").strip().splitlines()
            raise RuntimeError("本地 Qwen 生成失败：" + "\n".join(detail[-8:]))
        value = self._clean_generation(stdout, max_chars)
        self.progress_callback(100.0, "本地 Qwen 解说草稿已生成")
        return value, {
            "provider": "llama.cpp",
            "runtime": "b10622-win-cpu-x64",
            "model": model_spec.version,
            "style": style,
            "max_chars": int(max_chars),
            "facts_chars": len(facts),
        }


class NarrationSynthesizer:
    def __init__(self) -> None:
        self._cancel_event = threading.Event()
        self._process: subprocess.Popen[str] | None = None

    def cancel(self) -> None:
        self._cancel_event.set()
        if self._process and self._process.poll() is None:
            self._process.terminate()

    def synthesize(self, text: str, output_path: str | Path, rate: int = 0) -> MediaAsset:
        value = str(text).strip()
        if not value:
            raise ValueError("解说文字不能为空")
        output = Path(output_path).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        script = (
            "$ErrorActionPreference='Stop';"
            "Add-Type -AssemblyName System.Speech;"
            "$InputPath=$env:STREAMLIGHT_NARRATION_INPUT;"
            "$OutputPath=$env:STREAMLIGHT_NARRATION_OUTPUT;"
            "$Rate=[int]$env:STREAMLIGHT_NARRATION_RATE;"
            "$Text=[IO.File]::ReadAllText($InputPath,[Text.Encoding]::UTF8);"
            "$Voice=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            "$Voice.Rate=$Rate;"
            "$Voice.SetOutputToWaveFile($OutputPath);"
            "$Voice.Speak($Text);"
            "$Voice.Dispose();"
        )
        with tempfile.TemporaryDirectory(prefix="streamlight-narration-") as directory:
            input_path = Path(directory) / "narration.txt"
            input_path.write_text(value, encoding="utf-8")
            encoded_script = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
            process_environment = os.environ.copy()
            process_environment["STREAMLIGHT_NARRATION_INPUT"] = str(input_path)
            process_environment["STREAMLIGHT_NARRATION_OUTPUT"] = str(output)
            process_environment["STREAMLIGHT_NARRATION_RATE"] = str(max(-10, min(10, int(rate))))
            command = [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-EncodedCommand",
                encoded_script,
            ]
            self._process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=process_environment,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
            )
            stdout, stderr = self._process.communicate()
            code = self._process.returncode
            self._process = None
            if self._cancel_event.is_set():
                raise ExportCancelled("解说生成已取消")
            if code:
                raise RuntimeError((stderr or stdout or "系统离线语音生成失败").strip())
        if not output.is_file() or output.stat().st_size <= 44:
            raise RuntimeError("系统没有生成有效的解说音频")
        return probe_media(output)
