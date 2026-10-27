"""Offline regression checks for the Codex yt-script scorer (stdlib only)."""
import importlib.util
import json
import os
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(SKILL_DIR, "hookscore.py")
SPEC = importlib.util.spec_from_file_location("telugu_hookscore", SCRIPT)
hookscore = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hookscore)


class HookscoreTests(unittest.TestCase):
    def test_python_files_compile_in_memory(self):
        for path in (SCRIPT, os.path.abspath(__file__)):
            with open(path, encoding="utf-8") as source_file:
                compile(source_file.read(), path, "exec")

    def test_telugu_tokens_are_counted(self):
        self.assertEqual(hookscore.words("శ్రీవారి దర్శనం"), ["శ్రీవారి", "దర్శనం"])
        self.assertEqual(hookscore.words("శ్రీ"), ["శ్రీ"])

    def test_telugu_question_is_recognized(self):
        result = hookscore.score("మీరు ఈ కథలోని ముఖ్యమైన సందేశం తెలుసా?")
        self.assertGreater(result["properties"]["ఆసక్తి"], 24)

    def test_telugu_formula_is_classified(self):
        result = hookscore.score("మీరు రోజూ ఈ మంత్రాన్ని జపిస్తున్నారా?")
        self.assertTrue(result["is_question"])
        self.assertIn("ప్రేక్షకుడిని నేరుగా సంబోధించడం", result["hook_types"])

    def test_telugu_question_formula_is_classified(self):
        result = hookscore.score("మీకు ఈ శ్లోకంలోని ముఖ్యమైన సందేశం తెలుసా?")
        self.assertTrue(result["is_question"])
        self.assertIn("ప్రశ్న", result["hook_types"])

    def test_english_scoring_still_works(self):
        result = hookscore.score("Why do you lose time before the first prayer?")
        self.assertIn("CURIOSITY", result["properties"])
        self.assertGreater(result["verdict"], 0)

    def test_cli_json_preserves_telugu(self):
        result = subprocess.run(
            [sys.executable, SCRIPT, "--hook", "మీరు ఈ కథ తెలుసా?", "--json"],
            check=True, capture_output=True, text=True, encoding="utf-8",
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload[0]["hook"], "మీరు ఈ కథ తెలుసా?")

    def test_cli_requires_hook_or_file(self):
        result = subprocess.run(
            [sys.executable, SCRIPT], capture_output=True, text=True, encoding="utf-8",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--hook", result.stderr)

    def test_utf8_file_with_multiple_hooks(self):
        path = os.path.join(os.path.dirname(__file__), "telugu-hooks.txt")
        result = subprocess.run(
            [sys.executable, SCRIPT, path, "--json"],
            check=True, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(len(json.loads(result.stdout)), 2)

    def test_every_dimension_has_a_reason(self):
        result = hookscore.score("మీకు ఈ శ్లోకం గురించి తెలుసా?")
        self.assertEqual(len(result["dimensions"]), 5)
        self.assertTrue(all(value["reason"] for value in result["dimensions"].values()))

    def test_question_mark_alone_is_not_a_question(self):
        self.assertFalse(hookscore.is_question("అద్భుతమైన దర్శనం?"))

    def test_embedded_indirect_question_is_not_a_question(self):
        self.assertFalse(hookscore.is_question("శ్రీవారి ఆలయం ఎలా నిర్మించబడిందో ఈ కథ చెబుతుంది."))

    def test_question_suffix_without_punctuation(self):
        self.assertTrue(hookscore.is_question("ఈసారి తిరుమలకు వెళ్లారా"))

    def test_multisentence_hook_detects_first_question(self):
        self.assertTrue(hookscore.is_question("ఏమి తీసుకెళ్లాలి? తిరుమల యాత్రకు ఈ జాబితా చూడండి."))

    def test_false_address_substring_is_not_counted(self):
        result = hookscore.score("మీమాంసా పద్ధతిలో ఈ శ్లోకాన్ని పరిశీలిద్దాం.")
        self.assertNotIn("ప్రేక్షకుడిని నేరుగా సంబోధించడం", result["hook_types"])

    def test_numbered_recommendation_is_not_statistic(self):
        result = hookscore.score("రోజుకు 5 నిమిషాలు ప్రార్థనకు కేటాయించండి.")
        self.assertNotIn("గణాంక హుక్", result["hook_types"])

    def test_unsupported_boon_claim_is_flagged(self):
        result = hookscore.score("ఈ మంత్రాన్ని జపిస్తే మీ కోరిక తప్పక నెరవేరుతుంది!")
        self.assertTrue(result["review_flags"])


if __name__ == "__main__":
    unittest.main()
