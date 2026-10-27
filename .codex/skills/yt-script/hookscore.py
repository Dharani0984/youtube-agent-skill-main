#!/usr/bin/env python3
"""Score Telugu or English YouTube hooks using only the Python stdlib.

This is a transparent heuristic for revision, not a predictor of performance.
Usage: python hookscore.py --hook "ఒక హుక్"
       python hookscore.py hooks.txt [--json]
"""
import argparse
import json
import os
import re
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "hooks.json"), encoding="utf-8") as f:
    FORMULAS = json.load(f)["hooks"]

TOKENS = re.compile(r"[\w]+(?:['’][\w]+)?", re.UNICODE)
TELUGU = re.compile(r"[\u0c00-\u0c7f]")
NUMBER = re.compile(r"(?:\d[\d,.]*\s?(?:%|k|m|x|s|h)?|\d+\s*(?:రోజు|వారాల?|నెలల?|సంవత్సరాల?))", re.I)
EN_VAGUE = {"amazing", "incredible", "insane", "crazy", "huge", "massive", "secret", "powerful", "ultimate", "best", "unbelievable"}
TE_VAGUE = {"అద్భుతమైన", "అద్భుతం", "గొప్ప", "అత్యుత్తమ", "అపూర్వమైన"}
EN_FILLER = {"basically", "actually", "literally", "just", "really", "very", "guys", "hey", "welcome", "subscribe"}
TE_FILLER = {"అంటే", "నిజానికి", "ఇప్పుడు", "మరి", "సరే"}
EN_YOU = re.compile(r"\b(you|your|you're|youre|yourself)\b", re.I)
TE_YOU = re.compile(r"(?:మీరు|మీకు|మీ|నీవు|నీకు|నీ)")
EN_STAKE = re.compile(r"\b(lose|lost|waste|quit|fail|cost|risk|before|stop|never|die|dead)\b", re.I)
TE_STAKE = re.compile(r"(?:కోల్పోతారు|కోల్పోయే|వృథా|ఆపండి|ముందే|ప్రమాదం|తప్పు|మిస్|నష్ట)")
EN_CURIOSITY = re.compile(r"\b(why|how|what|which|until|before|but|nobody|almost|except|reason)\b", re.I)
TE_CURIOSITY = re.compile(r"(?:ఎందుకు|ఎలా|ఏమిటి|ఏది|ఎప్పుడు|ఎక్కడ|కానీ|రహస్యం|కారణం|తెలుసా|చూద్దాం)")
EN_CLOSED = re.compile(r"\b(because|so that|which means)\b", re.I)
TE_CLOSED = re.compile(r"(?:ఎందుకంటే|కాబట్టి|అందువల్ల)")
TELUGU_HINTS = re.compile(r"(?:ఏడు|ఐదు|మూడు|రెండు|ఒకటి|మొదటి|రెండో|రోజు|వార|నెల|సంవత్సర|శ్లోక|పూజ|భక్తి|మంత్ర|పారాయణ|దేవాలయ)")


def words(text):
    return TOKENS.findall(text.lower())


def is_telugu(text):
    return bool(TELUGU.search(text))


def specificity(text, tokens, telugu):
    vague = TE_VAGUE if telugu else EN_VAGUE
    filler = TE_FILLER if telugu else EN_FILLER
    score = 34 + len(NUMBER.findall(text)) * 22
    score -= sum(token in vague for token in tokens) * 16
    score -= sum(token in filler for token in tokens) * 5
    return clamp(score)


def address(text, telugu):
    pattern = TE_YOU if telugu else EN_YOU
    count = len(pattern.findall(text))
    early = bool(pattern.search(" ".join(text.split()[:6])))
    return clamp(26 + count * 20 + (30 if early else 0))


def stakes(text, telugu):
    pattern = TE_STAKE if telugu else EN_STAKE
    count = len(pattern.findall(text))
    return clamp(22 + count * 26 + (14 if NUMBER.search(text) else 0))


def curiosity(text, telugu):
    pattern = TE_CURIOSITY if telugu else EN_CURIOSITY
    closed_pattern = TE_CLOSED if telugu else EN_CLOSED
    count = len(pattern.findall(text))
    question = text.rstrip().endswith(("?", "？"))
    closed = bool(closed_pattern.search(text))
    return clamp(24 + count * 17 + (18 if question else 0) - (18 if closed else 0))


def brevity(tokens):
    count = len(tokens)
    if count == 0:
        return 0
    # Approximate whitespace-delimited spoken words; Telugu suffixes make this rough.
    if 9 <= count <= 24:
        return 100
    if count < 9:
        return max(30, 100 - (9 - count) * 11)
    return max(10, 100 - (count - 24) * 7)


def clamp(value):
    return max(0, min(100, value))


def classify(text, telugu):
    best, hits = None, 0
    for formula in FORMULAS:
        patterns = formula.get("match_te", []) if telugu else formula.get("match", [])
        matched = sum(bool(re.search(pattern, text, re.I)) for pattern in patterns)
        if matched > hits:
            best, hits = formula, matched
    name = (best.get("name_te") or best["name"]) if best else "గుర్తించబడలేదు" if telugu else "Unclassified"
    return name, hits


def score(text):
    telugu = is_telugu(text)
    tokens = words(text)
    properties = {
        "నిర్దిష్టత" if telugu else "SPECIFICITY": specificity(text, tokens, telugu),
        "ప్రేక్షకుడిని సంబోధన" if telugu else "ADDRESS": address(text, telugu),
        "ప్రాముఖ్యత" if telugu else "STAKES": stakes(text, telugu),
        "ఆసక్తి" if telugu else "CURIOSITY": curiosity(text, telugu),
        "సంక్షిప్తత" if telugu else "BREVITY": brevity(tokens),
    }
    values = list(properties.values())
    verdict = round(0.6 * (sum(values) / len(values)) + 0.4 * min(values))
    formula, hits = classify(text, telugu)
    band = ("బలమైనది" if verdict >= 72 else "పరిగణించదగినది" if verdict >= 55 else "మళ్లీ చూడాలి") if telugu else ("STRONG" if verdict >= 72 else "WORKABLE" if verdict >= 55 else "WEAK")
    return {"hook": text.strip(), "properties": properties, "verdict": verdict,
            "band": band, "formula": formula, "matched": hits}


def main(argv=None):
    # Windows consoles may default to a legacy code page that cannot encode Telugu.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Telugu/English hook heuristic scorer")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--hook", help="Score one hook")
    source.add_argument("file", nargs="?", help="UTF-8 text file, one hook per line")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args(argv)
    if args.hook is None and args.file is None:
        parser.error("provide --hook or a UTF-8 text file")
    if args.hook is not None:
        lines = [args.hook]
    else:
        with open(args.file, encoding="utf-8-sig") as f:
            lines = [line.strip() for line in f if line.strip()]
    results = sorted((score(line) for line in lines), key=lambda row: -row["verdict"])
    if args.json:
        for row in results:
            row.pop("matched", None)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    for row in results:
        print(f"\n{row['hook']}\n{'-' * min(72, max(20, len(row['hook'])))}")
        for key, value in row["properties"].items():
            print(f"  {key:<20} {value:3d}")
        print(f"  {'మొత్తం' if is_telugu(row['hook']) else 'VERDICT':<20} {row['verdict']:3d}  {row['band']}")
        print(f"  {'Hook రకం' if is_telugu(row['hook']) else 'formula':<20} {row['formula']} ({row['matched']} patterns)")
    if len(results) > 1:
        print(f"\nముందున్న Hook: {results[0]['hook']} ({results[0]['verdict']})" if is_telugu(results[0]['hook']) else f"\nWinner: {results[0]['hook']} ({results[0]['verdict']})")
    return 0


sys.path.insert(0, HERE)
from hookscore_impl import (classify, classify_all, is_question, is_telugu, main,
                            score, words)

if __name__ == "__main__":
    sys.exit(main())
