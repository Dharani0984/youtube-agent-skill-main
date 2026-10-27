"""Render vertical MP4 locally through an installed FFmpeg executable."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .captions import make_srt, make_timed_srt
from . import config
from .tts import wav_duration
from .visuals import render_ppm


def _filter_path(path):
    return str(Path(path).resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def _scene_durations(scenes, total):
    weights = [max(1, len(s["narration"].split())) for s in scenes]
    if all(s.get("duration_seconds") for s in scenes):
        weights = [float(s["duration_seconds"]) for s in scenes]
    weight_sum = sum(weights)
    return [total * weight / weight_sum for weight in weights]


def preflight():
    ffmpeg, ffprobe = shutil.which(config.FFMPEG), shutil.which(config.FFPROBE)
    if not ffmpeg or not ffprobe:
        raise RuntimeError("స్థానిక MP4 render‌కు FFmpeg, ffprobe PATHలో అవసరం; auto-install చేయలేదు")
    return ffmpeg, ffprobe


def render_project(project_dir, manifest, voice_path, music_path=None, music_license=None,
                   width=1080, height=1920, fps=30, font_name=None):
    ffmpeg, ffprobe = preflight()
    project_dir = Path(project_dir).resolve()
    output = project_dir / "preview.mp4"
    if output.exists():
        raise FileExistsError("preview.mp4 ఇప్పటికే ఉంది; overwrite చేయలేదు")
    voice_path = Path(voice_path).resolve()
    if not voice_path.is_file():
        raise FileNotFoundError(f"Narration WAV లేదు: {voice_path}")
    if music_path and not (music_license and str(music_license).strip()):
        raise ValueError("Background music file ఉంటే license/ownership వివరణ తప్పనిసరి")
    duration = wav_duration(voice_path)
    srt_path = project_dir / "subtitles-timed.srt"
    if srt_path.exists() or (project_dir / "render-filter.txt").exists():
        raise FileExistsError("Render outputలో ఇప్పటికే ఉన్న ఫైల్‌ను overwrite చేయలేదు")
    timeline_path = project_dir / "narration-timeline.json"
    if timeline_path.exists():
        timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
        segments = timeline.get("segments", [])
        if [item.get("scene_id") for item in segments] != [scene["scene_id"] for scene in manifest["scenes"]]:
            raise ValueError("Narration timeline scene IDs manifestతో సరిపోలలేదు")
        starts = [float(item["start"]) for item in segments]
        durations = [starts[i + 1] - starts[i] for i in range(len(starts) - 1)]
        durations.append(duration - starts[-1])
        subtitle_text = make_timed_srt(segments, duration)
    else:
        durations = _scene_durations(manifest["scenes"], duration)
        subtitle_text = make_srt(manifest["script"], duration)
    srt_path.write_text(subtitle_text, encoding="utf-8")
    scene_dir = project_dir / "scenes"
    scene_dir.mkdir(exist_ok=True)
    scene_paths = []
    for index, scene in enumerate(manifest["scenes"]):
        target = scene_dir / f"{scene['scene_id']}.ppm"
        if not target.exists():
            render_ppm(target, variant=index, prompt=scene["visual_prompt"])
        scene_paths.append(target)
    args = [ffmpeg, "-hide_banner", "-loglevel", "error", "-n"]
    for path, seconds in zip(scene_paths, durations):
        args += ["-loop", "1", "-framerate", str(fps), "-t", f"{seconds:.3f}", "-i", str(path)]
    voice_index = len(scene_paths)
    args += ["-i", str(voice_path)]
    music_index = None
    if music_path:
        music_index = voice_index + 1
        args += ["-stream_loop", "-1", "-i", str(Path(music_path).resolve())]
    filters = []
    video_labels = []
    for i, seconds in enumerate(durations):
        label = f"scene{i}"
        filters.append(f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps},setsar=1,trim=duration={seconds:.3f},setpts=PTS-STARTPTS[{label}]")
        video_labels.append(f"[{label}]")
    if len(video_labels) == 1:
        base = "scene0"
        fade_total = 0.0
    else:
        fade_duration = min(0.35, min(durations) / 3)
        previous = "scene0"
        for index in range(1, len(video_labels)):
            offset = sum(durations[:index]) - index * fade_duration
            current = f"xfade{index}"
            filters.append(f"[{previous}][scene{index}]xfade=transition=fade:duration={fade_duration:.3f}:offset={offset:.3f}[{current}]")
            previous = current
        base = previous
        fade_total = fade_duration * (len(video_labels) - 1)
    srt = _filter_path(srt_path)
    fonts = _filter_path(config.DEFAULT_FONT_DIR)
    font_name = font_name or config.DEFAULT_FONT
    style = f"FontName={font_name},FontSize=48,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV=130"
    filters.append(f"[{base}]tpad=stop_mode=clone:stop_duration={fade_total:.3f},trim=duration={duration:.3f},subtitles=filename='{srt}':fontsdir='{fonts}':force_style='{style}'[vout]")
    if music_index is None:
        filters.append(f"[{voice_index}:a]aresample=48000,volume=1.0[aout]")
    else:
        filters.append(f"[{voice_index}:a]aresample=48000,volume=1.0[voice]")
        filters.append(f"[{music_index}:a]aresample=48000,volume=0.12[bg]")
        filters.append("[voice][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]")
    filter_script = project_dir / "render-filter.txt"
    filter_script.write_text(";\n".join(filters), encoding="utf-8")
    args += ["-filter_complex_script", str(filter_script), "-map", "[vout]", "-map", "[aout]",
             "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "160k", "-t", f"{duration:.3f}", "-movflags", "+faststart", str(output)]
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError("FFmpeg render విఫలమైంది: " + result.stderr[-3000:])
    probe = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(output)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    if probe.returncode:
        raise RuntimeError("ffprobe తనిఖీ విఫలమైంది: " + probe.stderr[-2000:])
    report = quality_report(json.loads(probe.stdout), width, height)
    report.update({"video": str(output), "subtitle_file": str(srt_path), "music_license": music_license})
    quality_path = project_dir / "quality-report.json"
    if quality_path.exists():
        raise FileExistsError("quality-report.json ఇప్పటికే ఉంది; overwrite చేయలేదు")
    quality_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not report["passed"]:
        raise RuntimeError("MP4 quality checks విఫలమయ్యాయి: " + "; ".join(report["issues"]))
    return report


def quality_report(probe_data, width=1080, height=1920):
    streams = probe_data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = float(probe_data.get("format", {}).get("duration", 0) or 0)
    issues = []
    if not video:
        issues.append("వీడియో stream లేదు")
    elif video.get("width") != width or video.get("height") != height:
        issues.append(f"Resolution {video.get('width')}x{video.get('height')} లక్ష్య {width}x{height} కాదు")
    elif video.get("codec_name") != "h264":
        issues.append("వీడియో codec H.264 కాదు")
    if not audio:
        issues.append("Narration/audio stream లేదు")
    elif audio.get("codec_name") != "aac":
        issues.append("ఆడియో codec AAC కాదు")
    if not 1 <= duration <= 180:
        issues.append(f"Shorts duration అనుమతించిన పరిధిలో లేదు: {duration:.2f}s")
    return {"passed": not issues, "issues": issues, "width": video.get("width") if video else None,
            "height": video.get("height") if video else None, "duration_seconds": duration,
            "video_codec": video.get("codec_name") if video else None,
            "audio_codec": audio.get("codec_name") if audio else None}
