"""Load the non-personalized Telugu devotional defaults without guessing creator traits."""
import json
from pathlib import Path

DEFAULT_PROFILE = Path(__file__).resolve().parents[2] / ".codex" / "youtube" / "voice_defaults.json"
REQUIRED = ("language", "style", "dialect", "tone", "viewer_address", "tts_model",
            "tts_speaker_default", "tts_delivery", "guardrails")


def load_voice_defaults(path=None):
    path = Path(path or DEFAULT_PROFILE)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Telugu voice defaults చదవలేకపోయాం: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Voice defaults JSON object కావాలి")
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        raise ValueError("Voice defaultsలో తప్పనిసరి అంశాలు లేవు: " + ", ".join(missing))
    if data["language"] != "te-IN":
        raise ValueError("ఈ Telugu devotional pipelineకు language te-IN కావాలి")
    if not isinstance(data["guardrails"], list) or not data["guardrails"]:
        raise ValueError("Voice defaultsలో guardrails జాబితా అవసరం")
    return data
