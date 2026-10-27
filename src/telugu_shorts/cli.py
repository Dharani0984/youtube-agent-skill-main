"""Command line interface for local Telugu devotional video projects."""
import argparse
import json
import os
import sys
import webbrowser
import shutil
import platform
from pathlib import Path

from .approval import save_approval
from .manifest import load_manifest
from .pipeline import prepare_project, read_project
from .render import render_project
from .youtube import authorize, upload_approved
from . import config
from .tts import dependencies_available
from .voice import load_voice_defaults


def main(argv=None):
    parser = argparse.ArgumentParser(prog="telugu-shorts", description="స్థానిక తెలుగు భక్తి Shorts pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", help="Codex Skills manifest నుంచి project సిద్ధం చేయి")
    prep.add_argument("manifest", help="UTF-8 project-manifest.json")
    prep.add_argument("--output-root", default=str(config.DEFAULT_OUTPUT_ROOT))
    prep.add_argument("--tts", action="store_true", help="స్థానిక Indic Parler TTS ప్రయత్నించు; dependencies తప్పనిసరి")
    prep.add_argument("--speaker", default=None)
    render = sub.add_parser("render", help="Voice WAVతో vertical preview MP4 render చేయి")
    render.add_argument("project_dir")
    render.add_argument("--voice", required=True)
    render.add_argument("--music")
    render.add_argument("--music-license")
    preview = sub.add_parser("preview", help="స్థానిక MP4 preview తెరువు")
    preview.add_argument("project_dir")
    approve = sub.add_parser("approve-upload", help="చివరి previewకు upload approval నమోదు చేయి")
    approve.add_argument("project_dir"); approve.add_argument("--channel-id", required=True)
    approve.add_argument("--privacy", required=True, choices=("private", "unlisted", "public"))
    approve.add_argument("--category-id", required=True, help="Creator-selected YouTube category ID")
    approve.add_argument("--made-for-kids", required=True, choices=("yes", "no"))
    approve.add_argument("--synthetic-media", required=True, choices=("yes", "no"))
    auth = sub.add_parser("authorize", help="Google OAuth స్థానిక browser flow ప్రారంభించు")
    auth.add_argument("--client", required=True, help="స్థానిక OAuth desktop client JSON path")
    auth.add_argument("--token", default=str(config.DEFAULT_OAUTH_TOKEN))
    upload = sub.add_parser("upload", help="ఆమోదించిన preview మాత్రమే అధికారిక APIతో upload చేయి")
    upload.add_argument("project_dir"); upload.add_argument("--channel-id", required=True)
    upload.add_argument("--privacy", required=True, choices=("private", "unlisted", "public"))
    upload.add_argument("--client", required=True); upload.add_argument("--token", default=str(config.DEFAULT_OAUTH_TOKEN))
    sub.add_parser("doctor", help="స్థానిక FFmpeg, TTS, voice defaults readiness తనిఖీ చేయి")
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            try:
                ffmpeg_ok = bool(shutil.which(config.FFMPEG) and shutil.which(config.FFPROBE))
            except OSError:
                ffmpeg_ok = False
            try:
                profile_ok = bool(load_voice_defaults())
            except ValueError as exc:
                profile_ok = False; print("Voice profile: సమస్య — " + str(exc))
            print(json.dumps({"python": platform.python_version(), "ffmpeg_ffprobe": ffmpeg_ok,
                "local_telugu_tts_dependencies": dependencies_available(), "voice_defaults": profile_ok,
                "first_tts_use_downloads_model": True}, ensure_ascii=False, indent=2))
        elif args.command == "prepare":
            target = prepare_project(load_manifest(args.manifest), args.output_root, args.tts, args.speaker)
            print(f"Project సిద్ధమైంది: {target}")
            print("స్థితి: " + ("స్థానిక narration సిద్ధం; render చేయండి" if args.tts else "TTS WAV అవసరం; FFmpeg render ఇంకా చేయలేదు"))
        elif args.command == "render":
            data = read_project(args.project_dir)
            report = render_project(args.project_dir, data, args.voice, args.music, args.music_license)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            print("Preview: " + report["video"])
        elif args.command == "preview":
            video = (Path(args.project_dir) / "preview.mp4").resolve()
            if not video.is_file():
                raise FileNotFoundError("preview.mp4 లేదు; ముందుగా render చేయండి")
            if os.name == "nt":
                os.startfile(str(video))
            else:
                webbrowser.open(video.as_uri())
            print(f"స్థానిక Preview తెరిచాం: {video}")
        elif args.command == "approve-upload":
            project = Path(args.project_dir)
            data = read_project(project)
            video = project / "preview.mp4"
            if not video.is_file():
                raise FileNotFoundError("Approvalకు ముందు preview.mp4 render కావాలి")
            metadata = dict(data["metadata"], category_id=args.category_id,
                            made_for_kids=args.made_for_kids == "yes",
                            contains_synthetic_media=args.synthetic_media == "yes")
            if not args.category_id.isdigit():
                raise ValueError("YouTube category ID సంఖ్యగా ఇవ్వాలి")
            upload_metadata_path = project / "upload-metadata.json"
            if upload_metadata_path.exists():
                raise FileExistsError("upload-metadata.json ఇప్పటికే ఉంది; దాన్ని overwrite చేయలేదు")
            if (project / "upload-approval.json").exists():
                raise FileExistsError("పాత upload approval ఉంది; దాన్ని overwrite చేయలేదు. కొత్త project తయారు చేయండి")
            print(f"Channel: {args.channel_id}\nVisibility: {args.privacy}\nCategory: {args.category_id}\nTitle: {metadata['title']}\nVideo: {video.resolve()}")
            print("YouTube షరతులు: Upload చేస్తే వీడియో YouTube Terms, Community Guidelines‌కు అనుగుణమని, ఇతరుల copyright/ప్రైవసీ హక్కులను ఉల్లంఘించదని ధృవీకరిస్తారు.")
            print("By clicking 'upload,' you certify that the content you are uploading complies with the YouTube Terms of Service (including the YouTube Community Guidelines) at https://www.youtube.com/t/terms. Please be sure not to violate others' copyright or privacy rights.")
            phrase = input(f"అప్‌లోడ్‌కు స్పష్టంగా ఆమోదించాలంటే `UPLOAD {args.channel_id} {args.privacy}` టైప్ చేయండి: ")
            if phrase.strip() != f"UPLOAD {args.channel_id} {args.privacy}":
                raise PermissionError("స్పష్టమైన approval phrase సరిపోలలేదు; upload-metadata file సృష్టించలేదు")
            with upload_metadata_path.open("x", encoding="utf-8") as stream:
                json.dump(metadata, stream, ensure_ascii=False, indent=2)
            saved = save_approval(project / "upload-approval.json", video, metadata, args.channel_id, args.privacy, phrase)
            print("ఈ video, metadata, channel, visibilityకే approval నమోదు అయింది. ఈ tool upload చేయలేదు.")
            print("Video SHA-256: " + saved["video_sha256"])
        elif args.command == "authorize":
            authorize(args.client, args.token)
            print("OAuth token Windows DPAPIతో స్థానికంగా రక్షించబడింది.")
        elif args.command == "upload":
            project = Path(args.project_dir)
            metadata = json.loads((project / "upload-metadata.json").read_text(encoding="utf-8"))
            print(f"Channel: {args.channel_id}\nVisibility: {args.privacy}\nCategory: {metadata.get('category_id')}\nTitle: {metadata.get('title')}\nDescription: {metadata.get('description')}\nMade for kids: {metadata.get('made_for_kids')}\nSynthetic media: {metadata.get('contains_synthetic_media')}")
            print("YouTube షరతులు: Upload చేస్తే వీడియో YouTube Terms, Community Guidelines‌కు అనుగుణమని, ఇతరుల copyright/ప్రైవసీ హక్కులను ఉల్లంఘించదని ధృవీకరిస్తారు.")
            print("By clicking 'upload,' you certify that the content you are uploading complies with the YouTube Terms of Service (including the YouTube Community Guidelines) at https://www.youtube.com/t/terms. Please be sure not to violate others' copyright or privacy rights.")
            print("YouTube API upload starts only if the stored approval hash still matches.")
            result = upload_approved(args.project_dir, args.channel_id, args.privacy, args.client, args.token)
            print("Upload విజయవంతం: " + json.dumps(result, ensure_ascii=False))
    except (OSError, ValueError, RuntimeError, PermissionError) as exc:
        print(f"లోపం: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
