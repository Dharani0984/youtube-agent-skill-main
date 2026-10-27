"""Read-only validation for the creator's Markdown voice profile."""
import os
import re
import json

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice.md")
REQUIRED_HEADINGS = ("నా ఛానల్, ప్రేక్షకులు", "నా సహజమైన మాటతీరు", "భక్తి, సంప్రదాయం, ఆధారాలు", "వీడియో రూపం", "తప్పనిసరి పరిమితులు")


def load_voice_profile(path=None):
    path = path or DEFAULT_PATH
    if not os.path.isfile(path):
        return {"path": path, "exists": False, "ready": False,
                "missing": ["voice.md ఫైల్ కనిపించలేదు"], "content": ""}
    try:
        with open(path, encoding="utf-8-sig") as stream:
            content = stream.read()
    except (OSError, UnicodeError) as exc:
        return {"path": path, "exists": True, "ready": False,
                "missing": [f"profile చదవలేకపోయాం: {exc}"], "content": ""}
    blanks = re.findall(r"(?m)^-\s*([^:\n]+):\s*$", content)
    transcript_prompt = all(marker in content for marker in ("నా వీడియోల నుంచి", "ఉదాహరణలు", "చేర్చండి"))
    required_missing = [heading for heading in REQUIRED_HEADINGS if heading not in content]
    missing = list(blanks)
    if transcript_prompt:
        missing.append("మీ స్వంత వీడియో transcript ఉదాహరణలు")
    missing.extend(f"ఈ విభాగం లేదు: {heading}" for heading in required_missing)
    ready = not missing and bool(content.strip())
    return {"path": path, "exists": True, "ready": ready,
            "missing": missing, "content": content}


if __name__ == "__main__":
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default=DEFAULT_PATH)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    result = load_voice_profile(args.path)
    result.pop("content", None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["ready"] else 2)
