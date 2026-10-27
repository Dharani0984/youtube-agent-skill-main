"""Unicode-aware, Telugu devotional hook scoring implementation (stdlib only)."""
import argparse
import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))


def _config(path=None):
    try:
        with open(path or os.path.join(HERE, "hooks.json"), encoding="utf-8-sig") as stream:
            data = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"hooks.json చదవడంలో లోపం: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("hooks"), list) or not data["hooks"]:
        raise ValueError("hooks.json-ல் hooks பட்டியல் లేదు அல்லது నిర్మాణம் తప్పు")
    rules = data.get("telugu_rules")
    if not isinstance(rules, dict):
        raise ValueError("hooks.json-ல் telugu_rules அமைப்பு இல்லை")
    for key in ("question_starts", "question_endings", "number_words", "review_cues", "statistic_units"):
        if not isinstance(rules.get(key), list) or not all(isinstance(value, str) for value in rules[key]):
            raise ValueError(f"hooks.jsonలో telugu_rules.{key} సరైన జాబితా కావాలి")
    band = rules.get("shorts_word_band")
    if not isinstance(band, list) or len(band) != 2 or not all(isinstance(value, int) for value in band) or band[0] < 1 or band[1] < band[0]:
        raise ValueError("hooks.jsonలో shorts_word_band తప్పుగా ఉంది")
    for item in data["hooks"]:
        if not isinstance(item, dict) or not item.get("id") or not item.get("name"):
            raise ValueError("ప్రతి Hook నిర్వచనానికి id, name అవసరం")
        for field in ("match", "match_te"):
            patterns = item.get(field, [])
            if not isinstance(patterns, list) or not all(isinstance(pattern, str) for pattern in patterns):
                raise ValueError(f"{item.get('id')} {field} regex జాబితా తప్పుగా ఉంది")
            for pattern in patterns:
                try:
                    re.compile(pattern, re.I)
                except re.error as exc:
                    raise ValueError(f"{item.get('id')} regex తప్పు: {exc}") from exc
    return data


CONFIG = _config()
FORMULAS = CONFIG["hooks"]
RULES = CONFIG["telugu_rules"]
TELUGU_RANGE = re.compile(r"[\u0c00-\u0c7f]")
TELUGU_DIGITS = re.compile(r"\d+(?:[,.]\d+)?")
ADDRESS_WORDS = {"మీరు", "మీకు", "మీ", "నీవు", "నీకు", "నీ", "భక్తులారా"}
RECOMMENDATION_ENDINGS = ("కేటాయించండి", "చదవండి", "జపించండి", "చూడండి", "వినండి", "ప్రయత్నించండి")


def normalize(text):
    return unicodedata.normalize("NFC", str(text)).strip()


def words(text):
    """Count Unicode words while retaining combining marks and Indic joiners."""
    text = normalize(text).lower()
    result, current = [], []
    for char in text:
        category = unicodedata.category(char)[0]
        if category in {"L", "N"} or (category == "M" and current):
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


def is_question(text):
    """Use clause punctuation plus Telugu interrogative syntax, never '?' alone."""
    starts = {normalize(x) for x in RULES.get("question_starts", [])}
    endings = tuple(normalize(x) for x in RULES.get("question_endings", []))
    for clause in re.split(r"(?<=[?？.!।])|[\r\n]+", normalize(text)):
        clause = clause.strip()
        if not clause:
            continue
        marked = clause.endswith(("?", "？"))
        tokens = words(clause.rstrip("?？.!। "))
        if not tokens:
            continue
        wh = any(token in starts for token in tokens)
        terminal = any(tokens[-1] == ending or tokens[-1].endswith(ending) for ending in endings)
        if terminal or (marked and wh):
            return True
    return False


def _is_recommendation(tokens):
    return any(token.endswith(RECOMMENDATION_ENDINGS) for token in tokens)


def _statistic(text, tokens):
    if _is_recommendation(tokens):
        return False
    values = set(RULES.get("number_words", []))
    units = RULES.get("statistic_units", [])
    has_number = bool(TELUGU_DIGITS.search(text)) or any(token in values for token in tokens)
    has_unit = any(unit in text for unit in units) or "%" in text or "శాతం" in text
    return has_number and has_unit


def classify_all(text):
    telugu = is_telugu(text)
    tokens = words(text)
    kinds = []
    if telugu and is_question(text):
        kinds.append("ప్రశ్న")
    if telugu and any(token in ADDRESS_WORDS for token in tokens[:6]):
        kinds.append("ప్రేక్షకుడిని నేరుగా సంబోధించడం")
    for formula in FORMULAS:
        fid = formula["id"]
        if fid in {"the-question", "the-direct-address"}:
            continue
        if telugu and fid == "the-statistic" and not _statistic(text, tokens):
            continue
        patterns = formula.get("match_te", []) if telugu else formula.get("match", [])
        if any(re.search(pattern, text, re.I) for pattern in patterns):
            label = formula.get("name_te") if telugu else formula["name"]
            if label and label not in kinds:
                kinds.append(label)
    return kinds or (["వర్గం గుర్తించబడలేదు"] if telugu else ["Unclassified"])


def classify(text, telugu=None):
    kinds = classify_all(text)
    return kinds[0], len(kinds)


def _risk(text):
    cues = RULES.get("review_cues", [])
    return [cue for cue in cues if cue in text]


def score(text):
    text = normalize(text)
    telugu = is_telugu(text)
    tokens = words(text)
    kinds = classify_all(text)
    question = is_question(text) if telugu else text.rstrip().endswith("?")
    lo, hi = RULES.get("shorts_word_band", [4, 14])
    word_count = len(tokens)
    recognized = any(kind not in {"వర్గం గుర్తించబడలేదు", "Unclassified"} for kind in kinds)
    hook_quality = 82 if recognized else 58
    hook_reason = "గుర్తించదగిన Hook నిర్మాణం ఉంది." if recognized else "గుర్తించదగిన Hook నిర్మాణం లేదు."
    naturalness = 80 if telugu and not re.search(r"[A-Za-z]{3,}", text) else 65
    natural_reason = "తెలుగు లిపి గుర్తించబడింది; పలికి చూసి సహజత్వాన్ని నిర్ధారించండి." if telugu else "భాష సహజత్వాన్ని మాట్లాడేవారు సమీక్షించాలి."
    clarity = 90 if lo <= word_count <= hi else 72 if word_count <= hi + 6 else 48
    clarity_reason = f"Unicode పదాల లెక్క {word_count}; సూచించిన పరిధి {lo}–{hi}."
    interest = 86 if question else 72 if len(kinds) > 1 else 58
    interest_reason = "ప్రశ్న వాక్య నిర్మాణం గుర్తించబడింది." if question else "ప్రశ్న నిర్మాణం లేదు; ప్రేక్షకుల ఆసక్తిని మానవ సమీక్షతో అంచనా వేయండి."
    risky = _risk(text)
    fact_claim = bool(re.search(r"(?:చరిత్ర|పురాతనమైనది|మూలం|శాస్త్రం చెబుతుంది)", text))
    statistic = _statistic(text, tokens)
    devotional = bool(re.search(r"(?:శ్రీవారి|దేవాలయ|దేవుడు|దేవి|భక్తి|శ్లోక|మంత్ర|పూజ|పారాయణ|తిరుమల)", text))
    trust = 15 if risky else 55 if fact_claim or statistic else 90 if devotional else 80
    trust_reason = ("ఫలితం ఖాయమని చెప్పే వాదన ఉంది; ఆధారం లేకుండా ఉపయోగించవద్దు." if risky else
                    "చారిత్రక లేదా సంఖ్యా వాదనకు మూలం అవసరం." if fact_claim or statistic else
                    "ఖచ్చితమైన మతపరమైన ఫలిత వాదన లేదు; గౌరవప్రదమైన భాషను మానవ సమీక్షతో నిర్ధారించండి.")
    dimensions = {
        "హుక్ నాణ్యత": {"score": hook_quality, "reason": hook_reason},
        "తెలుగు సహజత్వం": {"score": naturalness, "reason": natural_reason},
        "స్పష్టత": {"score": clarity, "reason": clarity_reason},
        "ప్రేక్షకుల ఆసక్తి": {"score": interest, "reason": interest_reason},
        "భక్తి నమ్మకత్వం": {"score": trust, "reason": trust_reason},
    }
    verdict = round(sum(d["score"] for d in dimensions.values()) / 5)
    flags = []
    if risky:
        flags.append("ధృవీకరించని ఫలిత హామీ")
    if fact_claim or statistic:
        flags.append("మూలం/ఆధారాన్ని పరిశీలించండి")
    band = "బలమైనది" if verdict >= 80 else "పరిశీలించండి" if verdict >= 65 else "మళ్లీ రాయండి"
    legacy = {"నిర్దిష్టత": hook_quality, "ప్రేక్షకుడిని సంబోధన": 80 if any(t in ADDRESS_WORDS for t in tokens[:6]) else 25,
              "ప్రాముఖ్యత": trust, "ఆసక్తి": interest, "సంక్షిప్తత": clarity} if telugu else {
              "SPECIFICITY": hook_quality, "ADDRESS": 50, "STAKES": trust, "CURIOSITY": interest, "BREVITY": clarity}
    return {"hook": text, "properties": legacy, "dimensions": dimensions, "verdict": verdict,
            "band": band, "formula": kinds[0], "hook_types": kinds, "is_question": question,
            "word_count": word_count, "review_flags": flags}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Telugu devotional / English hook scorer")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--hook", help="Score one hook")
    source.add_argument("file", nargs="?", help="UTF-8 text file, one hook per line")
    parser.add_argument("--json", action="store_true", help="Print UTF-8 JSON")
    args = parser.parse_args(argv)
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        if args.hook is not None:
            lines = [args.hook]
        else:
            with open(args.file, encoding="utf-8-sig") as stream:
                lines = [line.strip() for line in stream if line.strip()]
        rows = sorted((score(line) for line in lines), key=lambda row: -row["verdict"])
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    for row in rows:
        print(f"\n{row['hook']}\nస్కోరు {row['verdict']}/100 — {row['band']}")
        print(f"పదాలు {row['word_count']} | ప్రశ్న: {'అవును' if row['is_question'] else 'కాదు'} | రకాలు: {', '.join(row['hook_types'])}")
        for name, data in row["dimensions"].items():
            print(f"  {name}: {data['score']} — {data['reason']}")
        for flag in row["review_flags"]:
            print(f"  சரிபார்ப்பு: {flag}")
    return 0
