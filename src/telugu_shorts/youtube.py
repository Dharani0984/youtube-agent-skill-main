"""Official YouTube Data API OAuth/upload using Python stdlib only."""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import secrets
import socketserver
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

from . import secure_store
from .approval import require_current_approval

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API_BASE = "https://www.googleapis.com/youtube/v3"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"


def _read_client(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data.get("installed"), dict):
            raise ValueError("OAuth client type desktop/installed కావాలి")
        return data["installed"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError("Google OAuth desktop client JSON చదవలేకపోయాం") from exc


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        self.server.oauth_result = {key: values[0] for key, values in query.items() if values}
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<h2>Authentication received. You may close this window.</h2>".encode())

    def log_message(self, *_args):
        return


def authorize(client_file, token_file, timeout=180):
    client = _read_client(client_file)
    state, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    server = socketserver.TCPServer(("127.0.0.1", 0), _CallbackHandler)
    server.timeout = timeout
    redirect_uri = f"http://127.0.0.1:{server.server_address[1]}/"
    params = {"client_id": client["client_id"], "redirect_uri": redirect_uri, "response_type": "code",
              "scope": SCOPES, "access_type": "offline", "prompt": "consent", "state": state,
              "code_challenge": challenge, "code_challenge_method": "S256"}
    auth_uri = AUTH_URL + "?" + urllib.parse.urlencode(params)
    print("Google sign-in browserలో తెరుస్తున్నాం; password/token ఈ terminalలో అడగము.")
    webbrowser.open(auth_uri)
    try:
        server.handle_request()
        result = getattr(server, "oauth_result", {})
    finally:
        server.server_close()
    if result.get("state") != state or not result.get("code"):
        raise PermissionError("OAuth callback ధృవీకరణ కాలేదు లేదా సమయం ముగిసింది")
    payload = urllib.parse.urlencode({"client_id": client["client_id"], "client_secret": client.get("client_secret", ""),
        "code": result["code"], "code_verifier": verifier, "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"}).encode()
    token = _post_form(TOKEN_URL, payload)
    if not token.get("refresh_token"):
        raise PermissionError("Google refresh token ఇవ్వలేదు; consent screen/configuration చూడండి")
    token["expires_at"] = int(time.time()) + int(token.get("expires_in", 3600))
    secure_store.save(token_file, json.dumps(token).encode("utf-8"))
    return True


def _post_form(url, body):
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError("Google OAuth token request విఫలమైంది; రహస్య వివరాలు ముద్రించలేదు") from exc


def access_token(client_file, token_file):
    client = _read_client(client_file)
    try:
        token = json.loads(secure_store.load(token_file).decode("utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise PermissionError("DPAPIలో OAuth consent లేదు; ముందుగా authorize చేయండి") from exc
    if token.get("access_token") and token.get("expires_at", 0) > time.time() + 60:
        return token["access_token"]
    body = urllib.parse.urlencode({"client_id": client["client_id"], "client_secret": client.get("client_secret", ""),
        "refresh_token": token["refresh_token"], "grant_type": "refresh_token"}).encode()
    refreshed = _post_form(TOKEN_URL, body)
    token.update(refreshed); token["expires_at"] = int(time.time()) + int(token.get("expires_in", 3600))
    secure_store.save(token_file, json.dumps(token).encode("utf-8"))
    return token["access_token"]


def _api_json(url, token):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError("YouTube API request విఫలమైంది; OAuth tokenను చూపలేదు") from exc


def _verify_channel(channel_id, token):
    query = urllib.parse.urlencode({"part": "id,snippet", "mine": "true"})
    result = _api_json(API_BASE + "/channels?" + query, token)
    channels = result.get("items", [])
    if not any(channel.get("id") == channel_id for channel in channels):
        raise PermissionError("OAuthలో ఉన్న channel ID మీరు ఆమోదించిన channelతో సరిపోలలేదు")


def _upload_resumable(video_path, metadata, token, chunk_size=8 * 1024 * 1024):
    path = Path(video_path)
    total = path.stat().st_size
    if total <= 0:
        raise ValueError("ఖాళీ MP4 upload చేయలేం")
    tags = metadata.get("tags") or [tag.lstrip("#") for tag in metadata.get("hashtags", [])]
    body = {"snippet": {"title": metadata["title"], "description": metadata["description"],
             "tags": tags, "categoryId": metadata["category_id"],
             "defaultLanguage": "te"},
            "status": {"privacyStatus": metadata["privacy_status"],
             "selfDeclaredMadeForKids": metadata["made_for_kids"]}}
    if "contains_synthetic_media" in metadata:
        body["status"]["containsSyntheticMedia"] = metadata["contains_synthetic_media"]
    query = urllib.parse.urlencode({"uploadType": "resumable", "part": "snippet,status"})
    request = urllib.request.Request(UPLOAD_URL + "?" + query, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(total)}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            session = response.headers.get("Location")
    except urllib.error.URLError as exc:
        raise RuntimeError("YouTube upload session ప్రారంభం విఫలమైంది") from exc
    if not session:
        raise RuntimeError("YouTube resumable upload URL ఇవ్వలేదు")
    offset = 0
    with path.open("rb") as media:
        while offset < total:
            chunk = media.read(min(chunk_size, total - offset))
            end = offset + len(chunk) - 1
            put = urllib.request.Request(session, data=chunk,
                headers={"Authorization": "Bearer " + token, "Content-Type": "video/mp4",
                         "Content-Length": str(len(chunk)), "Content-Range": f"bytes {offset}-{end}/{total}"}, method="PUT")
            try:
                with urllib.request.urlopen(put, timeout=180) as response:
                    if response.status in (200, 201):
                        return json.loads(response.read().decode("utf-8"))
                    if response.status == 308:
                        offset += len(chunk)
                        continue
            except urllib.error.HTTPError as exc:
                if exc.code == 308:
                    offset += len(chunk)
                    continue
                raise RuntimeError(f"YouTube resumable upload HTTP {exc.code}") from exc
            offset += len(chunk)
    raise RuntimeError("Upload పూర్తి response రాలేదు")


def upload_approved(project_dir, channel_id, privacy_status, client_file, token_file):
    project = Path(project_dir)
    video = project / "preview.mp4"
    metadata = json.loads((project / "upload-metadata.json").read_text(encoding="utf-8"))
    if not isinstance(metadata.get("made_for_kids"), bool):
        raise ValueError("Upload metadataలో made_for_kids true/false స్పష్టంగా నిర్ణయించాలి")
    if not isinstance(metadata.get("category_id"), str) or not metadata["category_id"].isdigit():
        raise ValueError("Upload metadataలో creator ఎంచుకున్న numeric category_id అవసరం")
    if not isinstance(metadata.get("contains_synthetic_media"), bool):
        raise ValueError("Upload metadataలో contains_synthetic_media true/false స్పష్టంగా నిర్ణయించాలి")
    require_current_approval(project / "upload-approval.json", video, metadata, channel_id, privacy_status)
    metadata = dict(metadata, privacy_status=privacy_status)
    token = access_token(client_file, token_file)
    _verify_channel(channel_id, token)
    response = _upload_resumable(video, metadata, token)
    video_id = response.get("id")
    if not video_id:
        raise RuntimeError("Upload responseలో video ID లేదు")
    return {"video_id": video_id, "url": "https://www.youtube.com/watch?v=" + video_id,
            "privacy_status": privacy_status, "channel_id": response.get("snippet", {}).get("channelId")}
