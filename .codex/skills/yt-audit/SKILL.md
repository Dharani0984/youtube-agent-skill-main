---
name: yt-audit
description: Audit a YouTube channel using supplied titles, thumbnails, scripts, and analytics; identify the single highest-priority fix.
---

# yt-audit

Use only material supplied by the user. Do not access YouTube, infer analytics, or invent results. Validate `.codex/youtube/voice.md` with `.codex/youtube/voice_profile.py`; treat blank fields as unknown. Review packaging, opening hooks, upload consistency, then retention data if supplied. Run sibling `title.py` and `hookscore.py` only when appropriate. Return one priority fix, evidence, what is working, and what to defer. This skill drafts analysis only; it does not publish.
