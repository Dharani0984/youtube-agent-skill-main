"""Cross-feature regression tests; Python standard library only."""
import json
import os
import sys
import unicodedata
import unittest
from unittest.mock import mock_open, patch

sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures")
sys.path.insert(0, os.path.join(ROOT, "youtube"))
for module_dir in ("yt-script", "yt-package", "yt-edit", "yt-chapters", "yt-retention", "yt-viral"):
    sys.path.insert(0, os.path.join(ROOT, "skills", module_dir))

import hookscore_impl
import title as title_tool
import deadair
import chapters
import retention
import swipe
import voice_profile


class TeluguHookRegressionTests(unittest.TestCase):
    CASES = [
        ("మీరు తిరుమల శ్రీవారి దర్శనానికి బయలుదేరే ముందు, ఈ మూడు విషయాలు చూసుకున్నారా?", True, "ప్రశ్న", "సంఖ్యతో కూడిన జాబితా"),
        ("ఏమి తీసుకెళ్లాలి? తిరుమల శ్రీవారి దర్శనానికి బయలుదేరే ముందు ఈ చిన్న జాబితా చూడండి.", True, "ప్రశ్న", "వర్గం గుర్తించబడలేదు"),
        ("శ్రీవారి దర్శనానికి వెళ్లే ముందు మనసును భక్తితో ఎలా సిద్ధం చేసుకోవాలి?", True, "ప్రశ్న", "వర్గం గుర్తించబడలేదు"),
        ("మీరు కుటుంబంతో తిరుమలకు వెళ్తున్నారా? ప్రయాణానికి ముందు ఈ విషయాలు చర్చించుకోండి.", True, "ప్రశ్న", "ప్రేక్షకుడిని నేరుగా సంబోధించడం"),
        ("భక్తులారా, తిరుమల యాత్రలో వేచి ఉండే సమయంలో మనసును భక్తిలో నిలిపేందుకు ఏమి చేయొచ్చు?", True, "ప్రశ్న", "ప్రేక్షకుడిని నేరుగా సంబోధించడం"),
        ("తిరుమల ప్రయాణానికి ముందు అవసరమైన వివరాలు సిద్ధం చేసుకోండి?", False, "వర్గం గుర్తించబడలేదు", "వర్గం గుర్తించబడలేదు"),
        ("ఈ శ్లోకంలోని భావాన్ని ఇప్పుడు కలిసి చూద్దాం.", False, "వెలికితీత", "వర్గం గుర్తించబడలేదు"),
        ("తిరుమల యాత్రకు ముందు ఏమేమి సిద్ధం చేసుకోవాలి", True, "ప్రశ్న", "వర్గం గుర్తించబడలేదు"),
        ("శ్రీవారి దర్శనం", False, "వర్గం గుర్తించబడలేదు", "వర్గం గుర్తించబడలేదు"),
        ("శ్రీ", False, "వర్గం గుర్తించబడలేదు", "వర్గం గుర్తించబడలేదు"),
        ("ఈ శ్లోకం గురించి మీకు తెలుసా?", True, "ప్రశ్న", "ప్రేక్షకుడిని నేరుగా సంబోధించడం"),
        ("ఈ మంత్రాన్ని జపిస్తే మీ కోరిక తప్పక నెరవేరుతుంది!", False, "వర్గం గుర్తించబడలేదు", "వర్గం గుర్తించబడలేదు"),
        ("రోజుకు 5 నిమిషాలు ప్రార్థనకు కేటాయించండి.", False, "వర్గం గుర్తించబడలేదు", "వర్గం గుర్తించబడలేదు"),
        ("రోజుకు ఐదు నిమిషాలు ప్రార్థనకు కేటాయించండి.", False, "వర్గం గుర్తించబడలేదు", "వర్గం గుర్తించబడలేదు"),
        ("మీమాంసా పద్ధతిలో ఈ శ్లోకాన్ని పరిశీలిద్దాం.", False, "వర్గం గుర్తించబడలేదు", "వర్గం గుర్తించబడలేదు"),
        ("అద్భుతమైన దర్శనం?", False, "వర్గం గుర్తించబడలేదు", "వర్గం గుర్తించబడలేదు"),
        ("ఈసారి తిరుమలకు వెళ్లారా", True, "ప్రశ్న", "వర్గం గుర్తించబడలేదు"),
        ("శ్రీవారి ఆలయం ఎలా నిర్మించబడిందో ఈ కథ చెబుతుంది.", False, "వర్గం గుర్తించబడలేదు", "వర్గం గుర్తించబడలేదు"),
        ("కలియుగ వైకుంఠంలో స్వామివారిని దర్శించారా", True, "ప్రశ్న", "వర్గం గుర్తించబడలేదు"),
        ("తిరుమలలో పూజకు సంబంధించిన ఈ సంప్రదాయం పురాతనమైనది.", False, "వర్గం గుర్తించబడలేదు", "వర్గం గుర్తించబడలేదు"),
    ]

    def test_twenty_prior_hooks_have_expected_question_and_categories(self):
        for index, (text, expected_question, expected_primary, secondary) in enumerate(self.CASES, 1):
            with self.subTest(case=index, hook=text):
                result = hookscore_impl.score(text)
                self.assertEqual(result["is_question"], expected_question)
                if expected_primary != "వర్గం గుర్తించబడలేదు":
                    self.assertIn(expected_primary, result["hook_types"])
                if secondary != "వర్గం గుర్తించబడలేదు":
                    self.assertIn(secondary, result["hook_types"])

    def test_unicode_tokens_keep_combining_marks(self):
        self.assertEqual(hookscore_impl.words("శ్రీవారి దర్శనం"), ["శ్రీవారి", "దర్శనం"])
        self.assertEqual(hookscore_impl.words("శ్రీ"), ["శ్రీ"])
        self.assertEqual(hookscore_impl.words("మీకు ఈ శ్లోకం తెలుసా?"), ["మీకు", "ఈ", "శ్లోకం", "తెలుసా"])
        decomposed = unicodedata.normalize("NFD", "శ్రీవారి దర్శనం")
        self.assertEqual(hookscore_impl.words(decomposed), ["శ్రీవారి", "దర్శనం"])

    def test_punctuation_and_verb_questions_use_sentence_structure(self):
        self.assertTrue(hookscore_impl.is_question("మీరు ఈ మంత్రాన్ని జపిస్తున్నారా"))
        self.assertTrue(hookscore_impl.is_question("ఏమి తీసుకెళ్లాలి? ఈ జాబితా చూడండి."))
        self.assertFalse(hookscore_impl.is_question("దర్శనం?"))
        self.assertFalse(hookscore_impl.is_question("అతను ఎలా వచ్చాడో ఈ కథ చెబుతుంది."))

    def test_scoring_aggregation_is_the_mean_of_explained_dimensions(self):
        result = hookscore_impl.score("మీకు ఈ శ్లోకం గురించి తెలుసా?")
        expected = round(sum(d["score"] for d in result["dimensions"].values()) / 5)
        self.assertEqual(result["verdict"], expected)

    def test_invalid_hook_configuration_fails_clearly(self):
        with patch("builtins.open", mock_open(read_data='{"hooks": [{"id": "x", "name": "x"}], "telugu_rules": []}')):
            with self.assertRaisesRegex(ValueError, "telugu_rules"):
                hookscore_impl._config("in-memory-invalid.json")

    def test_false_address_and_recommendation_statistics(self):
        self.assertNotIn("ప్రేక్షకుడిని నేరుగా సంబోధించడం", hookscore_impl.classify_all("మీమాంసా పద్ధతిలో శ్లోకాన్ని పరిశీలిద్దాం."))
        self.assertNotIn("గణాంక హుక్", hookscore_impl.classify_all("రోజుకు 5 నిమిషాలు ప్రార్థనకు కేటాయించండి."))
        self.assertNotIn("గణాంక హుక్", hookscore_impl.classify_all("రోజుకు ఐదు నిమిషాలు ప్రార్థనకు కేటాయించండి."))

    def test_unsupported_boon_and_historical_claims_are_flagged(self):
        boon = hookscore_impl.score("ఈ మంత్రాన్ని జపిస్తే మీ కోరిక తప్పక నెరవేరుతుంది!")
        history = hookscore_impl.score("తిరుమలలో ఈ సంప్రదాయం పురాతనమైనది.")
        self.assertTrue(boon["review_flags"])
        self.assertTrue(history["review_flags"])

    def test_score_breakdown_explains_each_dimension(self):
        result = hookscore_impl.score("మీకు ఈ శ్లోకం గురించి తెలుసా?")
        self.assertEqual(len(result["dimensions"]), 5)
        self.assertTrue(all(item["reason"] for item in result["dimensions"].values()))


class OtherFeatureRegressionTests(unittest.TestCase):
    def test_package_finds_telugu_thumbnail_duplication(self):
        result = title_tool.check("తిరుమల శ్రీవారి దర్శనం", "శ్రీవారి దర్శనం")
        self.assertTrue(any(kind == "duplicate" for kind, _ in result["issues"]))
        self.assertEqual(title_tool.words("శ్రీవారి దర్శనం"), ["శ్రీవారి", "దర్శనం"])

    def test_edit_reads_telugu_srt_filler_repeat_and_gaps(self):
        cues = deadair.load(os.path.join(FIX, "telugu-transcript.srt"))
        result = deadair.analyze(cues, 0.45)
        kinds = {cut["kind"] for cut in result["cuts"]}
        self.assertEqual(kinds, {"FILLER", "DEAD", "REPEAT"})

    def test_chapters_make_telugu_keywords_and_validate(self):
        result = chapters.generate(deadair.load(os.path.join(FIX, "telugu-transcript.srt")), target=4)
        self.assertTrue(result["valid"])
        self.assertEqual(result["chapters"][0]["label"], "0:00")
        self.assertNotEqual(result["chapters"][0]["draft_title"], "Section")

    def test_retention_reads_headered_csv_and_finds_cliffs(self):
        rows, header = retention.load_csv(os.path.join(FIX, "retention.csv"))
        result = retention.analyze(rows, duration=70, header=header)
        self.assertEqual(result["points"], 8)
        self.assertTrue(result["cliffs"])

    def test_viral_ranks_against_channel_median_and_skips_thin_sample(self):
        result = swipe.rank(swipe.load_rows(os.path.join(FIX, "videos.json")), threshold=2.0)
        self.assertEqual(result["outliers"][0]["multiple"], 4.0)
        self.assertEqual(result["skipped_thin_channels"][0]["count"], 1)
        self.assertEqual(result["outliers"][0]["title"], "పూజ సంప్రదాయం")
        self.assertEqual(swipe.classify("శ్రీవారి దర్శనం గురించి తెలుసా?"), "ప్రశ్న")

    def test_voice_profile_reports_blank_fields_without_writing(self):
        result = voice_profile.load_voice_profile()
        self.assertTrue(result["exists"])
        self.assertFalse(result["ready"])
        self.assertTrue(result["missing"])

    def test_malformed_or_missing_inputs_fail_explicitly(self):
        with self.assertRaises(ValueError):
            deadair.load(os.path.join(FIX, "missing.json"))
        with self.assertRaises(ValueError):
            retention.load_csv(os.path.join(FIX, "missing.csv"))
        with self.assertRaises(ValueError):
            swipe.load_rows(os.path.join(FIX, "missing.json"))
        with self.assertRaises(ValueError):
            chapters.generate([], target=2)

    def test_all_eleven_skill_manifests_exist(self):
        expected = {"yt-audit", "yt-chapters", "yt-comment", "yt-edit", "yt-package", "yt-plan",
                    "yt-retention", "yt-script", "yt-seo", "yt-shorts", "yt-viral"}
        actual = set()
        for name in expected:
            path = os.path.join(ROOT, "skills", name, "SKILL.md")
            self.assertTrue(os.path.isfile(path), name)
            with open(path, encoding="utf-8") as stream:
                self.assertIn("name: " + name, stream.read())
            codex = os.path.join(ROOT, "skills", name, "SKILL.md")
            self.assertTrue(os.path.isfile(codex), name)
            actual.add(name)
        self.assertEqual(actual, expected)

    def test_instruction_only_features_define_their_expected_workflow(self):
        required = {
            "yt-comment": ("questions", "corrections", "praise", "bait", "pin"),
            "yt-plan": ("available hours", "schedule", "estimated effort"),
            "yt-seo": ("description", "tags", "three plausible search queries"),
            "yt-shorts": ("20–55 second moments", "timecodes", "hookscore.py"),
            "yt-audit": ("one priority fix", "evidence", "retention data"),
        }
        for name, phrases in required.items():
            with self.subTest(skill=name):
                path = os.path.join(ROOT, "skills", name, "SKILL.md")
                with open(path, encoding="utf-8") as stream:
                    content = stream.read().lower()
                for phrase in phrases:
                    self.assertIn(phrase.lower(), content)


if __name__ == "__main__":
    unittest.main()
