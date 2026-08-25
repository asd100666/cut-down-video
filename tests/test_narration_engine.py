from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from streamlight.editor_models import EditProject, MediaAsset, SubtitleCue
from streamlight.narration_engine import LocalNarrationGenerator, build_narration_facts


class NarrationEngineTests(unittest.TestCase):
    def test_facts_use_subtitles_and_editable_clip_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            source.write_bytes(b"fixture")
            project = EditProject(name="解说测试")
            asset = project.add_asset(
                MediaAsset.create(source, kind="video", duration=8.0, has_audio=True)
            )
            clip = project.append_video_asset(asset.id)
            clip.selection_reason = "人物正在演示核心功能"
            project.subtitle_cues.append(
                SubtitleCue("subtitle_test", asset.id, 1.0, 2.0, "现在开始智能分镜", 0.9)
            )
            facts = build_narration_facts(project)
            self.assertIn("现在开始智能分镜", facts)
            self.assertIn("人物正在演示核心功能", facts)
            self.assertIn("成片时长约 8.0 秒", facts)

    def test_generation_cleanup_removes_runtime_markers_and_caps_length(self) -> None:
        cleaned = LocalNarrationGenerator._clean_generation(
            "assistant：这是第一句。这是第二句。[end of text]",
            80,
        )
        self.assertEqual(cleaned, "这是第一句。这是第二句。")
        long_text = "这是内容。" * 40
        self.assertLessEqual(len(LocalNarrationGenerator._clean_generation(long_text, 90)), 90)


if __name__ == "__main__":
    unittest.main()
