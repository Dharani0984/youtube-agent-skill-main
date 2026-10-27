"""Rank a user-provided public-video JSON collection by own-channel median."""
import argparse
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "yt-script"))
from hookscore_impl import classify_all


def load_rows(path):
    try:
        with open(path, encoding="utf-8-sig") as stream:
            payload = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"JSON సమాహారాన్ని చదవలేకపోయాం: {exc}") from exc
    rows = payload.get("videos") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("JSON root video జాబితా లేదా videos జాబితా ఉన్న object కావాలి")
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("title"), str):
            raise ValueError(f"video #{index + 1}: title అవసరం")
        try:
            views = float(row.get("views", 0) or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"video #{index + 1}: views సంఖ్య కావాలి") from exc
        if views < 0:
            raise ValueError(f"video #{index + 1}: views ప్రతికూలంగా ఉండకూడదు")
    return rows


def classify(title):
    return classify_all(title)[0]


def rank(rows, threshold=1.5):
    if threshold < 0:
        raise ValueError("threshold ప్రతికూలంగా ఉండకూడదు")
    by_channel = {}
    for row in rows:
        channel = str(row.get("channel") or "?")
        by_channel.setdefault(channel, []).append(row)
    out, thin = [], []
    for channel, videos in by_channel.items():
        if len(videos) < 4:
            thin.append({"channel": channel, "count": len(videos)})
            continue
        views = [float(v.get("views", 0) or 0) for v in videos]
        median = statistics.median(views)
        for video, count in zip(videos, views):
            multiple = count / median if median else 0
            if multiple >= threshold:
                out.append({"channel": channel, "title": video["title"], "views": int(count),
                            "median": int(median), "multiple": round(multiple, 2),
                            "formula": classify(video["title"]), "url": video.get("url", "")})
    out.sort(key=lambda item: -item["multiple"])
    return {"outliers": out, "skipped_thin_channels": thin}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file")
    parser.add_argument("--min", type=float, default=1.5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        result = rank(load_rows(args.file), args.min)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for item in result["outliers"][:25]:
            print(f"{item['multiple']:.2f}x | {item['views']:,} vs median {item['median']:,} | {item['channel']} | {item['title']} | {item['formula']}")
        if not result["outliers"]:
            print("ఏ వీడియో కూడా ఎంచుకున్న threshold దాటలేదు")
        for item in result["skipped_thin_channels"]:
            print(f"వదిలివేసింది: {item['channel']} — {item['count']} వీడియోలు; కనీసం 4 అవసరం")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
