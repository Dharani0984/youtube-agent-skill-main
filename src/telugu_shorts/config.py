"""Local paths and environment configuration; no secrets are stored here."""
import os
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPOSITORY_ROOT / "build" / "shorts"
DEFAULT_FONT = os.environ.get("TELUGU_SHORTS_FONT", "Nirmala UI")
DEFAULT_FONT_DIR = os.environ.get("TELUGU_SHORTS_FONT_DIR", r"C:\Windows\Fonts")
DEFAULT_OAUTH_TOKEN = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "TeluguDevotionalShorts" / "oauth.dpapi"


def _resolve_ffmpeg_tool(tool_name, environment_name):
    override = os.environ.get(environment_name)
    if override:
        return override
    suffix = ".exe" if os.name == "nt" else ""
    local_tools = REPOSITORY_ROOT / ".local-tools" / "ffmpeg"
    candidates = sorted(local_tools.glob(f"*/bin/{tool_name}{suffix}"), reverse=True)
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return tool_name


FFMPEG = _resolve_ffmpeg_tool("ffmpeg", "FFMPEG")
FFPROBE = _resolve_ffmpeg_tool("ffprobe", "FFPROBE")
