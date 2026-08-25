from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from streamlight.editor_models import AnalysisEvidence, MediaAsset, SubtitleCue
from streamlight.model_manager import ModelManager
from streamlight.offline_intelligence import OfflineIntelligenceAnalyzer


class _FakeAnalyzer(OfflineIntelligenceAnalyzer):
    def _transcribe(self, asset):
        cue = SubtitleCue("subtitle_fake", asset.id, 0.0, 2.0, "重要对白", 0.9)
        evidence = AnalysisEvidence("speech_fake", "speech", asset.id, 0.0, 2.0, 0.9, cue.text)
        return [cue], [evidence]

    def _analyze_visual(self, asset, sample_times):
        evidence = [
            AnalysisEvidence(f"visual_{index}", "visual", asset.id, time, time + 0.01, score, "人物画面")
            for index, (time, score) in enumerate(zip(sample_times, (0.2, 0.8)))
        ]
        return evidence, dict(zip(sample_times, (0.2, 0.8)))

    def _analyze_semantic(self, asset, sample_times, subtitles):
        evidence = [
            AnalysisEvidence(f"semantic_{index}", "semantic", asset.id, time, time + 0.01, score, "语义证据")
            for index, (time, score) in enumerate(zip(sample_times, (0.7, 0.4)))
        ]
        return evidence, dict(zip(sample_times, (0.7, 0.4)))


class _FallbackAnalyzer(OfflineIntelligenceAnalyzer):
    def _analyze_visual(self, asset, sample_times):
        raise RuntimeError("测试运行时不可用")


class OfflineIntelligenceTests(unittest.TestCase):
    def _asset(self, directory: str) -> MediaAsset:
        path = Path(directory) / "sample.mp4"
        path.write_bytes(b"placeholder")
        return MediaAsset.create(path, kind="video", duration=10.0, width=320, height=180)

    def test_enabled_analyzers_contribute_scores_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            asset = self._asset(directory)
            analyzer = _FakeAnalyzer(ModelManager(Path(directory) / "models", registry=()))
            result = analyzer.analyze(
                asset,
                [2.0, 7.0],
                speech_enabled=True,
                face_enabled=True,
                semantic_enabled=True,
            )
            self.assertEqual(len(result.subtitles), 1)
            self.assertEqual(len(result.evidence), 5)
            self.assertAlmostEqual(result.sample_scores[2.0], 0.4)
            self.assertAlmostEqual(result.sample_scores[7.0], 0.64)
            self.assertEqual(result.warnings, [])

    def test_optional_failure_records_warning_and_keeps_deterministic_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            asset = self._asset(directory)
            analyzer = _FallbackAnalyzer(ModelManager(Path(directory) / "models", registry=()))
            result = analyzer.analyze(
                asset,
                [5.0],
                speech_enabled=False,
                face_enabled=True,
                semantic_enabled=False,
            )
            self.assertEqual(result.sample_scores, {5.0: 0.0})
            self.assertEqual(len(result.warnings), 1)
            self.assertIn("已回退", result.warnings[0])


if __name__ == "__main__":
    unittest.main()
