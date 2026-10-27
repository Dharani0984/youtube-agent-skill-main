import json
import tempfile
import unittest
from pathlib import Path

from telugu_shorts.manifest import load_manifest, project_directory, validate_manifest, write_json


def sample():
    return {"schema_version": 1, "topic": "తిరుమల శ్రీవారి వైభవం",
        "script": "శ్రీవారి దర్శనం భక్తులకు పవిత్రమైన అనుభవం.",
        "hooks": [{"text": "ఈ సంప్రదాయం మీకు తెలుసా?", "score": 84, "reason": "ప్రశ్న"}],
        "scenes": [{"scene_id": "s1", "narration": "శ్రీవారి దర్శనం భక్తులకు పవిత్రమైన అనుభవం.", "visual_prompt": "స్వీయసృష్టి దృశ్యం"}],
        "metadata": {"title": "తిరుమల దర్శనం", "description": "తెలుగు భక్తి కథనం", "hashtags": ["#తిరుమల"]}}


class ManifestTests(unittest.TestCase):
    def test_telugu_utf8_roundtrip(self):
        data = validate_manifest(sample())
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "project.json"
            write_json(path, data)
            self.assertEqual(load_manifest(path)["script"], data["script"])

    def test_hook_score_range(self):
        data = sample(); data["hooks"][0]["score"] = 101
        with self.assertRaisesRegex(ValueError, "0–100"):
            validate_manifest(data)

    def test_empty_script_and_no_scenes_rejected(self):
        data = sample(); data["script"] = " "
        with self.assertRaises(ValueError): validate_manifest(data)
        data = sample(); data["scenes"] = []
        with self.assertRaisesRegex(ValueError, "scene"): validate_manifest(data)

    def test_duplicate_scene_ids_rejected(self):
        data = sample(); data["scenes"].append(dict(data["scenes"][0]))
        with self.assertRaisesRegex(ValueError, "పునరావృతమైంది"): validate_manifest(data)

    def test_scene_narration_must_cover_script_in_order(self):
        data = sample(); data["scenes"][0]["narration"] = "మార్చిన వాక్యం."
        with self.assertRaisesRegex(ValueError, "పూర్తి script"): validate_manifest(data)

    def test_non_telugu_language_rejected(self):
        data = sample(); data["language"] = "en-US"
        with self.assertRaisesRegex(ValueError, "te-IN"): validate_manifest(data)

    def test_distinct_telugu_topics_get_distinct_safe_ids(self):
        left, right = sample(), sample(); right["topic"] = "శ్రీవారి ఆలయ వైభవం"
        self.assertNotEqual(validate_manifest(left)["project_id"], validate_manifest(right)["project_id"])

    def test_existing_project_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "project").mkdir()
            with self.assertRaises(FileExistsError): project_directory(temp, "project")

    def test_malformed_json_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"; path.write_text("{oops", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Manifest"): load_manifest(path)


if __name__ == "__main__": unittest.main()
