"""Generate draft chapters from SRT/VTT/Whisper JSON using only stdlib."""
import argparse
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "yt-edit"))
from deadair import load
from unicodedata import normalize

STOP = set("the a an of for to in on and or is are was were be been with this that it as at by from you your i my we our they them he she but so if then than there here what which who how when where why not no yes do does did just really very like about into over out up down can could will would should have has had get got make made go going went one two".split())
STOP_TE = set("ఈ అది ఇది మరియు కోసం ముందు తర్వాత మీరు మీ మనం నాకు మా లోకి నుండి అని అయితే ఒక ఈయొక్క అనే".split())


def words(text):
    text = normalize("NFC", text).lower()
    result, current = [], []
    import unicodedata
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


def keywords(text):
    return {w for w in words(text) if len(w) >= 2 and w not in STOP and w not in STOP_TE}


def mmss(seconds):
    total = int(seconds)
    hours, minutes, secs = total // 3600, total % 3600 // 60, total % 60
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def generate(cues, target=7, minimum=10):
    if target < 3:
        raise ValueError("కనీసం 3 chapters లక్ష్యంగా ఉండాలి")
    if len(cues) < 3:
        raise ValueError("chapters రూపొందించడానికి transcriptలో కనీసం 3 cues అవసరం")
    duration = cues[-1][1]
    if duration < minimum * 3:
        return {"valid": False, "chapters": [], "error": "వీడియో నిడివి మూడు chaptersకు సరిపోదు"}
    candidates = []
    for index in range(1, len(cues)):
        gap = cues[index][0] - cues[index - 1][1]
        before = " ".join(c[2] for c in cues[max(0, index - 12):index])
        after = " ".join(c[2] for c in cues[index:index + 12])
        kb, ka = keywords(before), keywords(after)
        union = kb | ka
        shift = 1 - len(kb & ka) / len(union) if union else 0
        candidates.append((gap * 1.6 + shift * 3.2, cues[index][0]))
    picked = [0.0]
    for _, point in sorted(candidates, reverse=True):
        if len(picked) >= target:
            break
        if all(abs(point - existing) >= minimum for existing in picked) and duration - point >= minimum:
            picked.append(point)
    picked.sort()
    chapters = []
    for idx, start in enumerate(picked):
        end = picked[idx + 1] if idx + 1 < len(picked) else duration
        body = " ".join(c[2] for c in cues if c[0] < end and c[1] > start)
        freq = {}
        for token in words(body):
            if token in keywords(token):
                freq[token] = freq.get(token, 0) + 1
        title_words = sorted(freq, key=lambda word: (-freq[word], word))[:3]
        default_title = "విభాగం" if any("\u0c00" <= c <= "\u0c7f" for c in body) else "Section"
        title = " ".join(title_words) or default_title
        chapters.append({"start": round(start, 2), "label": mmss(start), "draft_title": title,
                         "seconds": round(end - start, 2)})
    valid = len(chapters) >= 3 and chapters[0]["start"] == 0 and all(c["seconds"] >= minimum for c in chapters)
    return {"valid": valid, "chapters": chapters}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript")
    parser.add_argument("--target", type=int, default=7)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        result = generate(load(args.transcript), args.target)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        for chapter in result["chapters"]:
            print(f"{chapter['label']} {chapter['draft_title']}")
        print("valid" if result["valid"] else "INVALID: first 00:00, 3+ chapters, 10s minimum each")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
