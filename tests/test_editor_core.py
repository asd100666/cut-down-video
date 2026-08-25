from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from streamlight.editor_models import (
    AnalysisEvidence,
    EditProject,
    MediaAsset,
    SnapshotHistory,
    SubtitleCue,
    format_timecode,
)
from streamlight.highlight_engine import SceneBoundary, plan_highlight_ranges


class EditorCoreTests(unittest.TestCase):
    def _project_with_assets(self, directory: str) -> EditProject:
        video_path = Path(directory) / "video.mp4"
        audio_path = Path(directory) / "music.wav"
        video_path.write_bytes(b"video-placeholder")
        audio_path.write_bytes(b"audio-placeholder")
        project = EditProject(name="测试剪辑")
        video = project.add_asset(
            MediaAsset.create(
                video_path,
                kind="video",
                duration=12.0,
                width=1920,
                height=1080,
                fps=30,
                has_audio=True,
            )
        )
        audio = project.add_asset(MediaAsset.create(audio_path, kind="audio", duration=20.0, has_audio=True))
        project.append_video_asset(video.id)
        project.add_audio_asset(audio.id)
        return project

    def test_manual_clip_operations_remain_non_destructive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project_with_assets(directory)
            source_path = project.asset(project.clips[0].asset_id).path

            left, right = project.split_clip(0, 5.0)
            self.assertAlmostEqual(left.duration, 5.0)
            self.assertAlmostEqual(right.duration, 7.0)
            self.assertEqual(len(project.clips), 2)
            project.move_clip(1, 0)
            self.assertEqual(project.clips[0].id, right.id)
            project.update_clip(0, in_point=6.0, out_point=11.5, volume=0.4, muted=True)
            self.assertAlmostEqual(project.clips[0].duration, 5.5)
            self.assertTrue(project.clips[0].muted)
            self.assertEqual(project.asset(project.clips[0].asset_id).path, source_path)
            self.assertTrue(Path(source_path).is_file())
            project.validate()

    def test_project_round_trip_and_edit_plan_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project_with_assets(directory)
            project.source_recipe = "long_video_highlight"
            project.generation_settings = {"target_duration": 60, "speech": True}
            clip = project.clips[0]
            evidence = AnalysisEvidence(
                "evidence_test",
                "speech",
                clip.asset_id,
                0.0,
                1.0,
                0.8,
                "测试对白",
            )
            project.analysis_evidence.append(evidence)
            project.subtitle_cues.append(SubtitleCue("subtitle_test", clip.asset_id, 0.0, 1.0, "测试对白", 0.8))
            clip.selection_reason = "语音证据"
            clip.selection_score = 0.8
            clip.evidence_ids = [evidence.id]
            target = Path(directory) / "sample.slproj"
            project.save(target)
            loaded = EditProject.load(target)

            self.assertEqual(loaded.name, "测试剪辑")
            self.assertEqual(loaded.source_recipe, "long_video_highlight")
            self.assertEqual(loaded.generation_settings["target_duration"], 60)
            self.assertEqual(len(loaded.clips), 1)
            self.assertEqual(len(loaded.audio_tracks), 1)
            self.assertEqual(loaded.schema_version, 3)
            self.assertEqual(loaded.subtitle_cues[0].text, "测试对白")
            self.assertEqual(loaded.analysis_evidence[0].id, "evidence_test")
            self.assertEqual(loaded.clips[0].evidence_ids, ["evidence_test"])
            loaded.validate()

    def test_snapshot_history_undo_and_redo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project_with_assets(directory)
            history = SnapshotHistory()
            history.record(project)
            project.split_clip(0, 4.0)
            self.assertEqual(len(project.clips), 2)
            project = history.undo(project)
            self.assertEqual(len(project.clips), 1)
            self.assertTrue(history.can_redo)
            project = history.redo(project)
            self.assertEqual(len(project.clips), 2)

    def test_transition_duration_scene_split_and_subtitle_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project_with_assets(directory)
            project.split_clip_at_scenes(0, [3.0, 7.0])
            self.assertEqual([(clip.in_point, clip.out_point) for clip in project.clips], [(0.0, 3.0), (3.0, 7.0), (7.0, 12.0)])
            project.set_clip_transition(1, "dissolve", 0.5)
            project.set_clip_transition(2, "fade", 0.25)
            self.assertAlmostEqual(project.duration, 11.25)

            asset_id = project.clips[0].asset_id
            project.subtitle_cues.extend(
                [
                    SubtitleCue("subtitle_a", asset_id, 2.5, 3.5, "跨越分镜", 0.9),
                    SubtitleCue("subtitle_b", asset_id, 8.0, 9.0, "第三镜头", 0.8),
                ]
            )
            instances = project.timeline_subtitle_instances()
            mapped = [(index, round(start, 2), round(end, 2)) for index, start, end, _cue in instances]
            self.assertEqual(mapped, [(0, 2.5, 3.0), (1, 7.25, 8.25)])

    def test_schema_two_project_migrates_with_default_transition_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project_with_assets(directory)
            payload = project.to_dict()
            payload["schema_version"] = 2
            for clip in payload["clips"]:
                clip.pop("transition", None)
                clip.pop("transition_duration", None)
            payload.pop("subtitle_cues", None)
            loaded = EditProject.from_dict(payload)
            self.assertEqual(loaded.schema_version, 3)
            self.assertEqual(loaded.clips[0].transition, "cut")
            self.assertEqual(loaded.clips[0].transition_duration, 0.0)
            self.assertEqual(loaded.subtitle_cues, [])

    def test_format_timecode(self) -> None:
        self.assertEqual(format_timecode(65.432), "01:05.432")
        self.assertEqual(format_timecode(3661.25), "01:01:01.250")

    def test_highlight_planner_hits_target_and_covers_timeline(self) -> None:
        ranges = plan_highlight_ranges(
            120.0,
            [
                SceneBoundary(8.0, 0.4),
                SceneBoundary(28.0, 0.9),
                SceneBoundary(52.0, 0.5),
                SceneBoundary(89.0, 0.8),
                SceneBoundary(110.0, 0.6),
            ],
            target_duration=30.0,
            max_clip_duration=6.0,
        )
        self.assertEqual(len(ranges), 5)
        self.assertAlmostEqual(sum(item.duration for item in ranges), 30.0, places=4)
        self.assertTrue(all(item.duration <= 6.0 for item in ranges))
        self.assertEqual(ranges, sorted(ranges, key=lambda item: item.start))
        self.assertLess(ranges[0].start, 24.0)
        self.assertGreater(ranges[-1].end, 96.0)

    def test_highlight_planner_uses_evidence_reason(self) -> None:
        ranges = plan_highlight_ranges(
            10.0,
            [
                SceneBoundary(2.0, 0.2, "场景切换"),
                SceneBoundary(7.0, 0.9, "智能证据"),
            ],
            target_duration=2.0,
            max_clip_duration=2.0,
        )
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0].reason, "智能证据")
        self.assertAlmostEqual(ranges[0].start, 7.0)


if __name__ == "__main__":
    unittest.main()
