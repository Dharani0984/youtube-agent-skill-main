"""Unicode-aware title/thumbnail linter. Uses Python standard library only."""
import argparse
import json
import re
import sys
import unicodedata

VAGUE_EN = {"amazing", "incredible", "insane", "crazy", "huge", "massive", "ultimate", "best", "secret"}
VAGUE_TE = {"అద్భుతం", "గొప్ప", "అత్యుత్తమ", "రహస్యం"}
STOP = {"the", "a", "an", "of", "for", "to", "in", "on", "and", "or", "is", "are", "with", "your", "you"}


def words(text):
    text = unicodedata.normalize("NFC", text).lower()
    result, current = [], []
    for char in text:
        cat = unicodedata.category(char)[0]
        if cat in {"L", "N"} or (cat == "M" and current):
            current.append(char)
        elif char in {"\u200c", "\u200d"} and current:
            current.append(char)
        elif current:
            result.append("".join(current)); current = []
    if current:
        result.append("".join(current))
    return result


def visible_characters(text):
    text = unicodedata.normalize("NFC", text)
    return sum(1 for char in text if unicodedata.category(char)[0] != "M" and char not in {"\u200c", "\u200d"})


def check(title, thumb=None):
    title = unicodedata.normalize("NFC", title).strip()
    issues, good = [], []
    n = visible_characters(title)
    if n > 100:
        issues.append(("length", f"{n} Unicode code points; above the 100-character hard ceiling"))
    elif n > 60:
        issues.append(("length", f"{n} characters; may truncate in search"))
    else:
        good.append(f"{n} characters; within the 60-character review target")
    tokens = words(title)
    vague = VAGUE_TE if any("\u0c00" <= c <= "\u0c7f" for c in title) else VAGUE_EN
    vague_hits = [w for w in tokens if w in vague]
    if vague_hits:
        issues.append(("vague", "Replace broad adjectives with a truthful, specific subject"))
    if title.endswith(("?", "？")):
        good.append("title is phrased as a question")
    if thumb is not None:
        thumb = unicodedata.normalize("NFC", thumb).strip()
        stop = STOP if not any("\u0c00" <= c <= "\u0c7f" for c in title) else set()
        shared = (set(tokens) - stop) & (set(words(thumb)) - stop)
        if shared:
            issues.append(("duplicate", "Thumbnail repeats title words: " + ", ".join(sorted(shared))))
        else:
            good.append("title and thumbnail use distinct wording")
        if len(words(thumb)) > 3:
            issues.append(("thumb-length", f"thumbnail has {len(words(thumb))} words; keep it to three or fewer"))
    score = max(0, min(100, 100 - 16 * len(issues) + 4 * len(good)))
    return {"title": title, "chars": n, "word_count": len(tokens), "score": score,
            "issues": issues, "good": good}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?")
    parser.add_argument("--title")
    parser.add_argument("--thumb")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        if args.title is not None:
            rows = [check(args.title, args.thumb)]
        elif args.file:
            with open(args.file, encoding="utf-8-sig") as stream:
                rows = [check(line.strip(), args.thumb) for line in stream if line.strip()]
        else:
            parser.error("provide --title or a UTF-8 title file")
    except (OSError, UnicodeError) as exc:
        parser.error(str(exc))
    rows.sort(key=lambda r: -r["score"])
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        for row in rows:
            print(f"\n{row['title']}\n{row['chars']} chars | {row['word_count']} words | score {row['score']}/100")
            for kind, reason in row["issues"]:
                print(f"  CHECK {kind}: {reason}")
            for reason in row["good"]:
                print(f"  OK: {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
