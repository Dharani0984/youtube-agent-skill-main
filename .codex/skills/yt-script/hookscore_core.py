"""Unicode-aware hook scoring core; Python standard library only."""
import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))


def load_config(path=None):
    path = path or os.path.join(HERE, "hooks.json")
    try:
        with open(path, encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"hooks.json could not be read: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("hooks"), list):
        raise ValueError("hooks.json must contain a hooks list")
    rules = data.get("telugu_rules")
    if not isinstance(rules, dict):
        raise ValueError("hooks.json is missing telugu_rules")
    for formula in data["hooks"]:
        if not isinstance(formula, dict) or not formula.get("id") or not formula.get("name"):
            raise ValueError("every hooks.json item needs id and name")
        for pattern in formula.get("match", []) + formula.get("match_te", []):
            try:
                re.compile(pattern, re.I)
            except re.error as exc:
                raise ValueError(f"invalid regex in {formula.get('id')}: {exc}") from exc
    return data


CONFIG = load_config()
FORMULAS = CONFIG["hooks"]
RULES = CONFIG["telugu_rules"]
TELUGU_RANGE = re.compile(r"[\u0c00-\u0c7f]")
TELUGU_ADDRESS = {"మీరు", "మీకు", "మీ", "నీవు", "నీకు", "నీ", "భక్తులారా"}
TELUGU_RECOMMENDATIONS = {"కేటాయించండి", "చదవండి", "జపించండి", "చూడండి", "వినండి", "ప్రయత్నించండి"}
TELUGU_DIGITS = re.compile(r"\d+(?:[,.]\d+)?")


def normalize(text):
    return unicodedata.normalize("NFC", str(text)).strip()


def words(text):
    """Return Unicode orthographic tokens, keeping combining marks with letters."""
    text = normalize(text).lower()
    result, current = [], []
    for char in text:
        category = unicodedata.category(char)
        if category[0] in {"L", "N"} or (category[0] == "M" and current):
            current.append(char)
        elif char in {"\u200c", "\u200d"} and current:
            current.append(char)
        elif char in {"'", "’"} and current:
            current.append(char)
        elif current:
            token = "".join(current).strip("'’")
            if token:
                result.append(token)
            current = []
    if current:
        token = "".join(current).strip("'’")
        if token:
            result.append(token)
    return result


def is_telugu(text):
    return bool(TELUGU_RANGE.search(text))


def _question_endings():
    return tuple(normalize(item) for item in RULES.get("question_endings", []))


def _question_starts():
    return {normalize(item) for item in RULES.get("question_starts", [])}


def is_question(text):
    """Detect question syntax per clause; punctuation alone is never sufficient."""
    normalized = normalize(text)
    for clause in re.split(r"(?<=[?？.!।])|[\r\n]+", normalized):
        clause = clause.strip()
        if not clause:
            continue
        has_question_mark = clause.endswith(("?", "？"))
        tokens = words(clause.rstrip("?？.!। "))
        if not tokens:
            continue
        has_wh_word = any(token in _question_starts() for token in tokens)
        last = tokens[-1]
        has_question_ending = any(last == end or last.endswith(end) for end in _question_endings())
        # A wh-word plus an interrogative verb frame can be a question without '?'.
        if has_wh_word and has_question_ending:
            return True
        # A question mark is accepted only when supported by a question word or ending.
        if has_question_mark and (has_wh_word or has_question_ending):
            return True
        # Telugu yes/no questions commonly use an interrogative verb ending without punctuation.
        if has_question_ending:
            return True
    return False


def _is_recommendation(tokens):
    return any(token in TELUGU_RECOMMENDATIONS for token in tokens)


def _has_supported_statistic(text, tokens):
    if _is_recommendation(tokens):
        return False
    number_words = set(RULES.get("number_words", []))
    units = tuple(RULES.get("statistic_units", []))
    has_number = bool(TELUGU_DIGITS.search(text)) or any(token in number_words for token in tokens)
    has_unit = any(unit in text for unit in units) or "%" in text or "శాతం" in text
    return has_number and has_unit


def classify_all(text):
    telugu = is_telugu(text)
    tokens = words(text)
    found = []
    if telugu:
        if is_question(text):
            found.append("ప్రశ్న")
        if any(token in TELUGU_ADDRESS for token in tokens[:6]):
            found.append("ప్రేక్షకుడిని నేరుగా సంబోధించడం")
    for formula in FORMULAS:
        fid = formula["id"]
        if fid in {"the-question", "the-direct-address"}:
            continue
        if fid == "the-statistic" and telugu and not _has_supported_statistic(text, tokens):
            continue
        patterns = formula.get("match_te", []) if telugu else formula.get("match", [])
        if any(re.search(pattern, text, re.I) for pattern in patterns):
            name = formula.get("name_te") if telugu else formula["name"]
            if name and name not in found:
                found.append(name)
    return found or (["వర్గం గుర్తించబడలేదు"] if telugu else ["Unclassified"])


def classify(text, telugu=None):
    kinds = classify_all(text)
    primary = kinds[0]
    return primary, len(kinds)


def _reasons(text, tokens, telugu, question, kinds):
    count = len(tokens)
    devotional = bool(re.search(r"(?:శ్రీవారి|దేవాలయ|దేవుడు|దేవి|భక్తి|శ్లోక|మంత్ర|పూజ|పారాయణ|తిరుమల)", text))
    risky = [cue for cue in RULES.get("review_cues", []) if cue in text]
    fact_claim = bool(re.search(r"(?:చరిత్ర|పురాతనమైనది|మూలం|శాస్త్రం చెబుతుంది)", text))
    number_present = bool(TELUGU_DIGITS.search(text)) or any(w in set(RULES.get("number_words", [])) for w in tokens)
    quality = 80 if len(kinds) > 1 or any(k != "వర్గం గుర్తించబడలేదు" for k in kinds) else 55
    quality_reason = "స్పష్టమైన Hook నిర్మాణం/వర్గం గుర్తించబడింది." if quality > 55 else "Hook నిర్మాణం స్పష్టంగా లేదు."
    natural = 80 if telugu and not re.search(r"[A-Za-z]{3,}", text) else 68
    natural_reason = "Telugu எழுத்து நடை ஒரேமையாக உள்ளது; இயல்புத்தன்மையை గట్టిగా చదివి உறுதிப்படுத்தவும்." if telugu else "உள்ளீடு Telugu அல்ல; அதன் மொழியில் இயல்புத்தன்மையை மதிப்பிடவும்."
    clarity = 90 if 4 <= count <= 16 else 70 if count <= 22 else 45
    clarity_reason = f"Unicode சொல் எண்ணிக்கை {count}; கருத்தின் எளிமையை உரையாளர் இறுதியாக மதிப்பிட வேண்டும்."
    interest = 85 if question else 70 if len(kinds) > 1 else 55
    interest_reason = "வாக்கிய அமைப்பில் உண்மையான கேள்வி கண்டறியப்பட்டது." if question else "கேள்வி அமைப்பு இல்லை; வெளிப்படையான திறந்த வாக்குறுதியும் குறைவு."
    unverified_number = number_present and not _is_recommendation(tokens) and _has_supported_statistic(text, tokens)
    trust = 15 if risky else 55 if fact_claim or unverified_number else 90 if devotional else 80
    trust_reason = ("உறுதியான பலன் கூற்று உள்ளது; ஆதாரம் இல்லாமல் பயன்படுத்த வேண்டாம்." if risky else
                    "உண்மை/எண் கூற்றுக்கு ஆதாரம் வழங்கப்படவில்லை; சரிபார்ப்பு தேவை." if fact_claim or unverified_number else
                    "உறுதியான சமய அல்லது பலன் கூற்று இல்லை; மரியாதையான மொழியை மனிதர் சரிபார்க்கவும்.")
    return {
        "ஹుక్ தரம்": {"score": quality, "reason": quality_reason},
        "తెలుగు సహజత్వం": {"score": natural, "reason": natural_reason},
        "தெளிவு": {"score": clarity, "reason": clarity_reason},
        "பார்வையாளர் ஆர்வம்": {"score": interest, "reason": interest_reason},
        "భక్తి నమ్మకత్వం": {"score": trust, "reason": trust_reason},
    }, risky, fact_claim


def score(text):
    text = normalize(text)
    telugu = is_telugu(text)
    tokens = words(text)
    question = is_question(text) if telugu else text.rstrip().endswith("?")
    kinds = classify_all(text)
    dimensions, risky, fact_claim = _reasons(text, tokens, telugu, question, kinds)
    verdict = round(sum(item["score"] for item in dimensions.values()) / len(dimensions))
    flags = []
    if risky:
        flags.append("ఆధారంలేని ఫలిత హామీ: " + ", ".join(risky))
    if fact_claim or (TELUGU_DIGITS.search(text) and not _has_supported_statistic(text, tokens)):
        flags.append("సంఖ్య లేదా వాస్తవ వాదనకు మూలాన్ని ధృవీకరించండి")
    if telugu:
        band = "బలమైనది" if verdict >= 80 else "పరిశీలించండి" if verdict >= 65 else "మళ్లీ రాయండి"
        legacy = {"నిర్దిష్టత": dimensions["Hook தரம்"]["score"],
                  "ప్రేక్షకుడిని సంబోధన": 80 if any(w in TELUGU_ADDRESS for w in tokens[:6]) else 25,
                  "ప్రాముఖ్యత": trust, "ఆసక్తి": interest_score(dimensions),
                  "సంక్షిప్తత": clarity}
    else:
        band = "STRONG" if verdict >= 80 else "WORKABLE" if verdict >= 65 else "REVISE"
        legacy = {"SPECIFICITY": dimensions["Hook தரம்"]["score"], "ADDRESS": 50,
                  "STAKES": trust, "CURIOSITY": dimensions["பார்வையாளர் ஆர்வம்"]["score"],
                  "BREVITY": clarity}
    return {"hook": text, "properties": legacy, "dimensions": dimensions,
            "verdict": verdict, "band": band, "formula": kinds[0],
            "hook_types": kinds, "is_question": question,
            "word_count": len(tokens), "review_flags": flags}


def interest_score(dimensions):
    return dimensions["பார்வையாளர் ஆர்வம்"]["score"]


def main(argv=None):
    import argparse
    import sys
    parser = argparse.ArgumentParser(description="Telugu devotional / English hook scorer")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--hook", help="Score one hook")
    source.add_argument("file", nargs="?", help="UTF-8 text file, one hook per line")
    parser.add_argument("--json", action="store_true", help="Print UTF-8 JSON")
    args = parser.parse_args(argv)
    try:
        if args.hook is not None:
            lines = [args.hook]
        else:
            with open(args.file, encoding="utf-8-sig") as handle:
                lines = [line.strip() for line in handle if line.strip()]
        rows = sorted((score(line) for line in lines), key=lambda row: -row["verdict"])
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for row in rows:
        print(f"\n{row['hook']}\nమార్కులు {row['verdict']}/100 — {row['band']}")
        print(f"పదాలు: {row['word_count']} | ప్రశ్న: {'అవును' if row['is_question'] else 'కాదు'} | రకాలు: {', '.join(row['hook_types'])}")
        for name, detail in row["dimensions"].items():
            print(f"  {name}: {detail['score']} — {detail['reason']}")
        for flag in row["review_flags"]:
            print(f"  ధృవీకరణ: {flag}")
    return 0


# Keep this intermediate module name compatible while routing every public
# operation through the maintained UTF-8 implementation.
import sys as _sys
_sys.path.insert(0, HERE)
from hookscore_impl import classify, classify_all, is_question, is_telugu, main, score, words
