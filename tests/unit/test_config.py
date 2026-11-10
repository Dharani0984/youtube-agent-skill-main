import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from telugu_shorts import config


class ConfigTests(unittest.TestCase):
    def test_discovers_repository_local_ffmpeg_and_ffprobe(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bin_dir = root / ".local-tools" / "ffmpeg" / "ffmpeg-test" / "bin"
            bin_dir.mkdir(parents=True)
            ffmpeg = bin_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
            ffprobe = bin_dir / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
            ffmpeg.write_bytes(b"test")
            ffprobe.write_bytes(b"test")
            with patch.object(config, "REPOSITORY_ROOT", root), patch.dict(os.environ, {"FFMPEG": "", "FFPROBE": ""}):
                self.assertEqual(config._resolve_ffmpeg_tool("ffmpeg", "FFMPEG"), str(ffmpeg))
                self.assertEqual(config._resolve_ffmpeg_tool("ffprobe", "FFPROBE"), str(ffprobe))

    def test_environment_override_takes_precedence(self):
        with patch.dict(os.environ, {"FFMPEG": "custom-ffmpeg"}):
            self.assertEqual(config._resolve_ffmpeg_tool("ffmpeg", "FFMPEG"), "custom-ffmpeg")

    def test_falls_back_to_path_command_when_local_binary_is_absent(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(config, "REPOSITORY_ROOT", Path(temp)), patch.dict(os.environ, {"FFMPEG": ""}):
            self.assertEqual(config._resolve_ffmpeg_tool("ffmpeg", "FFMPEG"), "ffmpeg")


if __name__ == "__main__":
    unittest.main()
