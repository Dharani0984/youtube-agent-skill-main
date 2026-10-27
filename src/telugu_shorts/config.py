"""Local paths and environment configuration; no secrets are stored here."""
import os
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPOSITORY_ROOT / "build" / "shorts"
DEFAULT_FONT = os.environ.get("TELUGU_SHORTS_FONT", "Nirmala UI")
DEFAULT_FONT_DIR = os.environ.get("TELUGU_SHORTS_FONT_DIR", r"C:\Windows\Fonts")
DEFAULT_OAUTH_TOKEN = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "TeluguDevotionalShorts" / "oauth.dpapi"
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE", "ffprobe")
