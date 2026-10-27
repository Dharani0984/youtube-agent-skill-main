"""Bind upload approval to exact media, metadata, channel, and visibility."""
import hashlib
import json
from pathlib import Path


def approval_payload(video_path, metadata, channel_id, privacy_status):
    if privacy_status not in {"private", "unlisted", "public"}:
        raise ValueError("privacy_status private/unlisted/public కావాలి")
    digest = hashlib.sha256()
    with Path(video_path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    video_hash = digest.hexdigest()
    metadata_hash = hashlib.sha256(json.dumps(metadata, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return {"video_sha256": video_hash, "metadata_sha256": metadata_hash,
            "channel_id": channel_id, "privacy_status": privacy_status}


def save_approval(path, video_path, metadata, channel_id, privacy_status, confirmation):
    expected = f"UPLOAD {channel_id} {privacy_status}"
    if confirmation.strip() != expected:
        raise PermissionError(f"ఖచ్చితమైన నిర్ధారణ అవసరం: {expected}")
    payload = approval_payload(video_path, metadata, channel_id, privacy_status)
    payload["approved"] = True
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
    return payload


def require_current_approval(path, video_path, metadata, channel_id, privacy_status):
    try:
        saved = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PermissionError("చెల్లుబాటు అయ్యే upload approval లేదు") from exc
    current = approval_payload(video_path, metadata, channel_id, privacy_status)
    if not saved.get("approved") or any(saved.get(key) != value for key, value in current.items()):
        raise PermissionError("వీడియో/వివరాలు/channel/privacy మారాయి; కొత్త explicit approval కావాలి")
    return current
