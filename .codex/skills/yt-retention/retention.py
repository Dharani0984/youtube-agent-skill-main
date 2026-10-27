"""Analyze a supplied audience-retention CSV (stdlib only; no network access)."""
import argparse
import csv
import json
import os
import re
import sys


def _number(value):
    value = value.strip().replace("%", "").replace(",", "")
    if not value:
        return None
    match = re.fullmatch(r"(\d{1,2}:)?\d{1,2}:\d{1,2}(?:\.\d+)?", value)
    if match:
        parts = value.split(":")
        return sum(float(part) * (60 ** (len(parts) - idx - 1)) for idx, part in enumerate(parts))
    try:
        return float(value)
    except ValueError:
        return None


def load_csv(path):
    try:
        with open(path, newline="", encoding="utf-8-sig") as stream:
            rows = list(csv.reader(stream))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(f"CSV చదవలేకపోయాం: {exc}") from exc
    if not rows:
        raise ValueError("CSV ఖాళీగా ఉంది")
    header = [cell.strip().lower() for cell in rows[0]]
    pos_idx = next((i for i, name in enumerate(header) if any(x in name for x in ("elapsed", "position", "time", "percentage viewed"))), None)
    ret_idx = next((i for i, name in enumerate(header) if any(x in name for x in ("retention", "still watching", "audience"))), None)
    data_start = 1 if pos_idx is not None or ret_idx is not None else 0
    if pos_idx is None or ret_idx is None:
        pos_idx, ret_idx = 0, 1
    parsed = []
    for line_no, row in enumerate(rows[data_start:], data_start + 1):
        if max(pos_idx, ret_idx) >= len(row):
            continue
        x, y = _number(row[pos_idx]), _number(row[ret_idx])
        if x is None or y is None:
            continue
        if x < 0 or not 0 <= y <= 100:
            raise ValueError(f"CSV line {line_no}: సమయం/retention పరిధి తప్పుగా ఉంది")
        parsed.append((x, y))
    if len(parsed) < 8:
        raise ValueError(f"కనీసం 8 retention data points అవసరం; లభించినవి {len(parsed)}")
    if any(parsed[i][0] <= parsed[i - 1][0] for i in range(1, len(parsed))):
        raise ValueError("CSV time/position విలువలు పెరుగుతున్న క్రమంలో ఉండాలి")
    return parsed, " ".join(header)


def analyze(rows, duration=None, header=""):
    x_values, y_values = [r[0] for r in rows], [r[1] for r in rows]
    percent_axis = ("percent" in header or "percentage" in header) if header else max(x_values) <= 100.5
    if any(term in header for term in ("elapsed time", "seconds", "time in")):
        percent_axis = False
    if duration is not None and duration <= 0:
        raise ValueError("duration సున్నా కంటే ఎక్కువగా ఉండాలి")
    cutoff = 30.0 if not percent_axis else (30.0 / duration * 100 if duration else 10.0)
    first = y_values[0] or 100.0
    hook_end = min((y for x, y in rows if x <= cutoff), default=first)
    drops = []
    for index in range(1, len(rows)):
        delta = y_values[index - 1] - y_values[index]
        span = x_values[index] - x_values[index - 1]
        drops.append((delta / span if span else 0, x_values[index - 1], x_values[index], delta))
    drops.sort(reverse=True)
    cliffs = [{"from": round(a, 2), "to": round(b, 2), "lost": round(drop, 2),
               "at_seconds": round(a / 100 * duration, 1) if percent_axis and duration else None if percent_axis else round(a, 1)}
              for _, a, b, drop in drops[:5] if drop > 0.8]
    mid = [drop for _, start, _, drop in drops if start > cutoff]
    return {"points": len(rows), "start": first, "hook_leak": round(first - hook_end, 2),
            "end": y_values[-1], "cliffs": cliffs,
            "slide_per_unit": round(sum(mid) / len(mid), 3) if mid else 0,
            "axis_is_percent": percent_axis}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv")
    parser.add_argument("--duration", type=float)
    parser.add_argument("--transcript")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        rows, header = load_csv(args.csv)
        result = analyze(rows, args.duration, header)
        result["source"] = args.csv
        if args.transcript:
            if result["axis_is_percent"] and not args.duration:
                result["transcript_note"] = "శాతం అక్షానికి duration అవసరం; transcript సమయంతో పోల్చలేదు"
            else:
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "yt-edit"))
                from deadair import load as load_cues
                cues = load_cues(args.transcript)
                for cliff in result["cliffs"]:
                    t = cliff["at_seconds"]
                    nearby = [cue[2] for cue in cues if cue[0] <= t + 4 and cue[1] >= t - 4]
                    cliff["transcript"] = " ".join(nearby)[:140]
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Hook leak: {result['hook_leak']}% | end: {result['end']}% | cliffs: {len(result['cliffs'])} | slide: {result['slide_per_unit']}")
        for cliff in result["cliffs"]:
            print(f"drop {cliff['lost']}% near {cliff['at_seconds']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
