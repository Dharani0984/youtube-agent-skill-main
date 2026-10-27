"""Unicode-aware transcript edit-decision-list generator (stdlib only)."""
import argparse
import json
import os
import re
import unicodedata

FILLERS = {
    ("um",), ("uh",), ("er",), ("ah",), ("so",), ("okay",), ("ok",), ("right",),
    ("yeah",), ("like",), ("anyway",), ("basically",), ("actually",), ("you", "know"),
    ("అం",), ("మ్",), ("అంటే",), ("సరే",), ("ఇప్పుడు",),
}


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


def parse_ts(value):
    value = value.strip().replace(",", ".")
    parts = value.split(":")
    try:
        if len(parts) == 3:
            result = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            result = int(parts[0]) * 60 + float(parts[1])
        else:
            raise ValueError
    except ValueError as exc:
        raise ValueError(f"తప్పు timestamp: {value}") from exc
    if result < 0:
        raise ValueError(f"timestamp ప్రతికూలంగా ఉండకూడదు: {value}")
    return result


def load(path):
    try:
        with open(path, encoding="utf-8-sig") as stream:
            raw = stream.read()
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"transcript చదవలేకపోయాం: {exc}") from exc
    if path.lower().endswith(".json"):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Whisper JSON తప్పుగా ఉంది: {exc}") from exc
        segments = data if isinstance(data, list) else data.get("segments") if isinstance(data, dict) else None
        if not isinstance(segments, list):
            raise ValueError("Whisper JSONలో segments జాబితా అవసరం")
        cues = []
        for item in segments:
            try:
                start, end = float(item["start"]), float(item["end"])
                text = str(item.get("text") or "").strip()
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("ప్రతి Whisper segmentకు start/end/text అవసరం") from exc
            if start < 0 or end < start:
                raise ValueError("Whisper segment సమయ పరిధి తప్పుగా ఉంది")
            if text:
                cues.append((start, end, text))
        return cues
    cues, current = [], None
    for line in raw.splitlines():
        match = re.match(r"\s*(\d[\d:.,]+)\s*-->\s*(\d[\d:.,]+)", line)
        if match:
            start, end = parse_ts(match.group(1)), parse_ts(match.group(2))
            if end < start:
                raise ValueError("SRT/VTT cue ముగింపు ప్రారంభానికి ముందు ఉంది")
            current = [start, end, []]
            cues.append(current)
        elif current is not None and line.strip() and not line.strip().isdigit() and not line.startswith("WEBVTT"):
            current[2].append(re.sub(r"<[^>]+>", "", line.strip()))
    return [(a, b, " ".join(text)) for a, b, text in cues if text]


def filler_only(text):
    return tuple(words(re.sub(r"[.,!?;:।॥…-]", " ", text))) in FILLERS


def _merged_duration(cuts):
    intervals = sorted((max(0, c["start"]), max(0, c["end"])) for c in cuts if c["end"] > c["start"])
    total = 0.0
    if not intervals:
        return 0.0
    start, end = intervals[0]
    for a, b in intervals[1:]:
        if a <= end:
            end = max(end, b)
        else:
            total += end - start
            start, end = a, b
    return total + end - start


def analyze(cues, floor=0.45):
    if floor < 0:
        raise ValueError("dead-air కనిష్ఠ విరామం ప్రతికూలంగా ఉండకూడదు")
    if not cues:
        raise ValueError("transcriptలో cue లేదు")
    cuts = []
    for index, (start, end, text) in enumerate(cues):
        if filler_only(text):
            cuts.append({"kind": "FILLER", "start": start, "end": end, "why": text[:48]})
        if index:
            gap = start - cues[index - 1][1]
            if gap > floor:
                half = floor / 2
                cuts.append({"kind": "DEAD", "start": round(cues[index - 1][1] + half, 3),
                             "end": round(start - half, 3), "why": f"{gap:.2f}s gap"})
            prior = next((words(cues[j][2]) for j in range(index - 1, -1, -1)
                          if words(cues[j][2]) and not filler_only(cues[j][2])), [])
            current = words(text)
            if len(prior) >= 3 and prior[:5] == current[:5]:
                old_start, old_end, _ = next(c for c in reversed(cues[:index]) if words(c[2]) and not filler_only(c[2]))
                cuts.append({"kind": "REPEAT", "start": old_start, "end": old_end,
                             "why": "మునుపటి మాట మళ్లీ మొదలవుతోంది"})
    return {"cuts": sorted(cuts, key=lambda item: item["start"]),
            "removed": round(_merged_duration(cuts), 3), "duration": cues[-1][1]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript")
    parser.add_argument("--floor", type=float, default=0.45)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        cues = load(args.transcript)
        result = analyze(cues, args.floor)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    result.update({"source": args.transcript, "out": round(result["duration"] - result["removed"], 3)})
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for cut in result["cuts"]:
            print(f"{cut['kind']} {cut['start']:.2f}-{cut['end']:.2f}s: {cut['why']}")
        print(f"{len(result['cuts'])} cuts; {result['removed']:.2f}s removable; {result['out']:.2f}s estimated output")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
