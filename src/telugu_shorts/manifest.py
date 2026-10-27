"""UTF-8 manifest validation and project output helpers (Python stdlib only)."""
from __future__ import annotations

import json
import hashlib
import re
import unicodedata
from pathlib import Path

SCHEMA_VERSION = 1


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} తప్పనిసరి; ఖాళీగా ఉండకూడదు")
    return unicodedata.normalize("NFC", value.strip())


def _slug(value):
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(value)):
        return str(value)[:48]
    ascii_value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    base = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")[:40] or "telugu-devotional-short"
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:8]
    return f"{base}-{digest}"


def validate_manifest(data):
    if not isinstance(data, dict):
        raise ValueError("Manifest ఒక JSON object కావాలి")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version {SCHEMA_VERSION} కావాలి")
    topic, script = _text(data.get("topic"), "topic"), _text(data.get("script"), "script")
    hooks, scenes, metadata = data.get("hooks"), data.get("scenes"), data.get("metadata")
    if not isinstance(hooks, list) or not hooks:
        raise ValueError("కనీసం ఒక scored hook అవసరం")
    clean_hooks = []
    for i, hook in enumerate(hooks):
        if not isinstance(hook, dict):
            raise ValueError(f"hooks[{i}] object కావాలి")
        score = hook.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 100:
            raise ValueError(f"hooks[{i}].score 0–100 మధ్య ఉండాలి")
        clean_hooks.append({"text": _text(hook.get("text"), f"hooks[{i}].text"),
                            "score": round(score), "reason": str(hook.get("reason", "మానవ సమీక్ష అవసరం"))})
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("కనీసం ఒక scene అవసరం")
    clean_scenes, seen = [], set()
    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise ValueError(f"scenes[{i}] object కావాలి")
        scene_id = _text(scene.get("scene_id", f"scene-{i + 1:03}"), f"scenes[{i}].scene_id")
        if scene_id in seen:
            raise ValueError(f"scene_id పునరావృతమైంది: {scene_id}")
        seen.add(scene_id)
        duration = scene.get("duration_seconds")
        if duration is not None and (isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0):
            raise ValueError(f"{scene_id}.duration_seconds సున్నా కంటే ఎక్కువ కావాలి")
        clean_scenes.append({"scene_id": scene_id,
            "narration": _text(scene.get("narration"), f"{scene_id}.narration"),
            "visual_prompt": str(scene.get("visual_prompt", "స్వీయసృష్టి జ్యామితీయ భక్తి దృశ్యం")),
            "duration_seconds": float(duration) if duration is not None else None})
    fold_space = lambda value: " ".join(unicodedata.normalize("NFC", value).split())
    if fold_space(" ".join(scene["narration"] for scene in clean_scenes)) != fold_space(script):
        raise ValueError("Scenes narrationలను క్రమంగా కలిపితే పూర్తి script అచ్చంగా రావాలి")
    if not isinstance(metadata, dict):
        raise ValueError("metadata object అవసరం")
    clean_meta = {k: metadata.get(k) for k in ("title", "description", "hashtags")}
    clean_meta["title"] = _text(clean_meta["title"], "metadata.title")
    clean_meta["description"] = _text(clean_meta["description"], "metadata.description")
    if not isinstance(clean_meta["hashtags"], list) or any(not isinstance(x, str) or not x.strip() for x in clean_meta["hashtags"]):
        raise ValueError("metadata.hashtags ఖాళీ కాని stringల జాబితా కావాలి")
    language = data.get("language", "te-IN")
    if language != "te-IN":
        raise ValueError("Telugu devotional projectకు language te-IN కావాలి")
    if not isinstance(data.get("assets", {}), dict):
        raise ValueError("assets object కావాలి")
    return {"schema_version": SCHEMA_VERSION, "project_id": _slug(data.get("project_id") or topic),
        "topic": topic, "language": language, "script": script,
        "hooks": clean_hooks, "scenes": clean_scenes,
        "metadata": {"title": clean_meta["title"], "description": clean_meta["description"],
                     "hashtags": [x.strip() for x in clean_meta["hashtags"]]},
        "assets": data.get("assets", {}), "output_paths": data.get("output_paths", {})}


def load_manifest(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as stream:
            return validate_manifest(json.load(stream))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Manifest చదవడంలో లోపం: {exc}") from exc


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def project_directory(root, project_id):
    root = Path(root).resolve()
    target = (root / _slug(project_id)).resolve()
    if target == root or root not in target.parents:
        raise ValueError("Project folder build root లోపలే ఉండాలి")
    if target.exists():
        raise FileExistsError(f"ఇప్పటికే ఉన్న ఫోల్డర్‌ను overwrite చేయలేదు: {target}")
    return target
