import json
import tempfile
import unittest
import wave
import subprocess
from pathlib import Path
from unittest.mock import patch

from telugu_shorts.approval import require_current_approval, save_approval
from telugu_shorts.captions import make_srt, make_timed_srt
from telugu_shorts.pipeline import prepare_project
from telugu_shorts.render import preflight, quality_report, render_project
from telugu_shorts import render as render_module
from telugu_shorts.visuals import render_ppm
from telugu_shorts import tts, youtube
from telugu_shorts.voice import load_voice_defaults


def sample():
    return {"schema_version": 1, "topic": "తిరుమల శ్రీవారి దర్శనం",
        "script": "భక్తితో శ్రీవారిని స్మరించండి. దర్శన సంప్రదాయాన్ని తెలుసుకుందాం.",
        "hooks": [{"text": "ఈ సంప్రదాయం మీకు తెలుసా?", "score": 81, "reason": "ప్రశ్న"}],
        "scenes": [{"scene_id": "scene-a", "narration": "భక్తితో శ్రీవారిని స్మరించండి. దర్శన సంప్రదాయాన్ని తెలుసుకుందాం."}],
        "metadata": {"title": "తిరుమల దర్శనం", "description": "తెలుగు భక్తి Short", "hashtags": ["#తిరుమల"]}}


class LocalPipelineTests(unittest.TestCase):
    def test_telugu_subtitles_include_end_time(self):
        text = make_srt("శ్రీవారి దర్శనం పవిత్రం. భక్తితో స్మరించండి.", 8)
        self.assertIn("శ్రీవారి దర్శనం", text); self.assertIn("00:00:08,000", text)

    def test_telugu_caption_lines_are_short_and_two_lines_max(self):
        text = make_srt("తిరుమలలో వెంకటేశ్వర స్వామి దర్శన సంప్రదాయాన్ని తెలుసుకుందాం.", 8)
        caption = text.split("\n\n")[0].splitlines()[2:]
        self.assertLessEqual(len(caption), 2)
        self.assertTrue(all(len(line) <= 20 for line in caption))

    def test_subtitle_invalid_inputs_fail(self):
        with self.assertRaises(ValueError): make_srt("", 1)
        with self.assertRaises(ValueError): make_srt("భక్తి", 0)

    def test_timed_subtitles_stay_inside_scene_audio(self):
        result = make_timed_srt([{"scene_id": "s1", "text": "తిరుమల శ్రీవారి దర్శనం.", "start": 1.0, "end": 4.0}], 5.0)
        self.assertIn("00:00:01,000 --> 00:00:04,000", result)
        with self.assertRaises(ValueError):
            make_timed_srt([{"text": "భక్తి", "start": 1, "end": 6}], 5)

    def test_original_ppm_scene_created(self):
        with tempfile.TemporaryDirectory() as temp:
            path = render_ppm(Path(temp) / "scene.ppm", 90, 160)
            self.assertTrue(path.read_bytes().startswith(b"P6\n90 160\n255\n"))

    def test_scene_prompt_changes_generated_original_visual(self):
        with tempfile.TemporaryDirectory() as temp:
            temple = render_ppm(Path(temp) / "temple.ppm", 90, 160, prompt="తిరుమల గోపురం")
            lamp = render_ppm(Path(temp) / "lamp.ppm", 90, 160, prompt="దీప జ్యోతి వెలుగు")
            self.assertNotEqual(temple.read_bytes(), lamp.read_bytes())

    def test_prepare_writes_manifest_metadata_srt_and_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            project = prepare_project(sample(), Path(temp) / "shorts")
            manifest = json.loads((project / "project.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["language"], "te-IN")
            self.assertTrue(Path(manifest["output_paths"]["project_manifest"]).is_absolute())
            self.assertTrue((project / "metadata.json").exists())
            self.assertTrue((project / "subtitles.srt").exists())
            self.assertTrue((project / "scenes/scene-a.ppm").exists())

    def test_prepare_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            prepare_project(sample(), Path(temp) / "shorts")
            with self.assertRaises(FileExistsError): prepare_project(sample(), Path(temp) / "shorts")

    def test_approval_requires_phrase_and_binds_video_hash(self):
        metadata = {"title": "తిరుమల", "description": "భక్తి", "made_for_kids": False}
        with tempfile.TemporaryDirectory() as temp:
            video = Path(temp) / "preview.mp4"; video.write_bytes(b"local test video")
            approval = Path(temp) / "approval.json"
            with self.assertRaises(PermissionError): save_approval(approval, video, metadata, "UC123", "private", "yes")
            save_approval(approval, video, metadata, "UC123", "private", "UPLOAD UC123 private")
            require_current_approval(approval, video, metadata, "UC123", "private")
            changed_metadata = dict(metadata, title="మార్చిన శీర్షిక")
            with self.assertRaises(PermissionError): require_current_approval(approval, video, changed_metadata, "UC123", "private")
            with self.assertRaises(PermissionError): require_current_approval(approval, video, metadata, "UC999", "private")
            with self.assertRaises(PermissionError): require_current_approval(approval, video, metadata, "UC123", "public")
            video.write_bytes(b"changed video")
            with self.assertRaises(PermissionError): require_current_approval(approval, video, metadata, "UC123", "private")

    def test_approval_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            video = Path(temp) / "v.mp4"; video.write_bytes(b"v")
            target = Path(temp) / "approval.json"
            save_approval(target, video, {"title": "t"}, "UC1", "unlisted", "UPLOAD UC1 unlisted")
            with self.assertRaises(FileExistsError): save_approval(target, video, {"title": "t"}, "UC1", "unlisted", "UPLOAD UC1 unlisted")

    def test_quality_report_checks_codecs_dimensions_and_duration(self):
        good = {"streams": [{"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920},
                            {"codec_type": "audio", "codec_name": "aac"}], "format": {"duration": "45"}}
        self.assertTrue(quality_report(good)["passed"])
        self.assertFalse(quality_report({"streams": [], "format": {"duration": "181"}})["passed"])

    def test_mocked_render_command_contains_vertical_fades_and_telugu_subtitles(self):
        data = sample()
        data["scenes"] = [
            {"scene_id": "scene-a", "narration": "భక్తితో శ్రీవారిని స్మరించండి.", "visual_prompt": "తిరుమల కొండలు"},
            {"scene_id": "scene-b", "narration": "దర్శన సంప్రదాయాన్ని తెలుసుకుందాం.", "visual_prompt": "దీప జ్యోతి"}]
        with tempfile.TemporaryDirectory() as temp:
            project = prepare_project(data, Path(temp) / "shorts")
            voice = project / "voice.wav"
            with wave.open(str(voice), "wb") as stream:
                stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(8000)
                stream.writeframes(b"\0\0" * 8000 * 4)
            probe = {"streams": [{"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920},
                                 {"codec_type": "audio", "codec_name": "aac"}],
                     "format": {"duration": "4.0"}}
            captured = []
            def fake_run(args, **_kwargs):
                captured.append(args)
                if args[0] == "fake-ffmpeg":
                    Path(args[-1]).write_bytes(b"mock-only-not-a-real-mp4")
                    return subprocess.CompletedProcess(args, 0, "", "")
                return subprocess.CompletedProcess(args, 0, json.dumps(probe), "")
            with patch.object(render_module.shutil, "which", side_effect=lambda name: "fake-" + name), \
                 patch.object(render_module.subprocess, "run", side_effect=fake_run):
                result = render_project(project, data, voice)
            self.assertTrue(result["passed"])
            filter_graph = (project / "render-filter.txt").read_text(encoding="utf-8")
            self.assertIn("xfade=transition=fade", filter_graph)
            self.assertIn("subtitles=filename=", filter_graph)
            self.assertIn("-filter_complex_script", captured[0])
            self.assertIn("-n", captured[0])
            self.assertTrue((project / "subtitles-timed.srt").is_file())

    def test_ffmpeg_absence_is_reported_not_hidden(self):
        import shutil
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            with self.assertRaisesRegex(RuntimeError, "FFmpeg"): preflight()
        else:
            ffmpeg, ffprobe = preflight()
            self.assertTrue(Path(ffmpeg).is_file()); self.assertTrue(Path(ffprobe).is_file())

    def test_missing_tts_dependencies_are_reported_without_installing(self):
        with patch.object(tts, "dependencies_available", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "auto-install"):
                tts.synthesize_telugu("తెలుగు భక్తి కథనం", "never-created.wav")

    def test_telugu_voice_defaults_load_and_validate(self):
        profile = load_voice_defaults()
        self.assertEqual(profile["language"], "te-IN")
        self.assertEqual(profile["tts_speaker_default"], "Prakash")
        self.assertTrue(profile["guardrails"])

    def test_upload_refuses_missing_approval_before_oauth_or_network(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            (project / "preview.mp4").write_bytes(b"test-only")
            (project / "upload-metadata.json").write_text(json.dumps({
                "title": "తిరుమల", "description": "భక్తి", "category_id": "22",
                "made_for_kids": False, "contains_synthetic_media": False}), encoding="utf-8")
            with patch.object(youtube, "access_token") as get_token:
                with self.assertRaises(PermissionError):
                    youtube.upload_approved(project, "UC123", "private", "unused-client.json", "unused-token")
                get_token.assert_not_called()

    def test_requesting_tts_without_dependencies_creates_no_partial_project(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "shorts"
            with patch.object(tts, "dependencies_available", return_value=False):
                with self.assertRaisesRegex(RuntimeError, "auto-install"):
                    prepare_project(sample(), output, make_voice=True)
            self.assertFalse(output.exists())


if __name__ == "__main__": unittest.main()
