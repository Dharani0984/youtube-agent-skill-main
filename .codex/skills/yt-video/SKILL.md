---
name: yt-video
description: >-
  Prepare a Telugu devotional YouTube Short locally from a topic using the
  existing channel Skills, hook scorer, Telugu narration, subtitles, visuals,
  FFmpeg preview, quality checks, and a separate upload approval gate.
---

# Telugu Devotional Shorts

Prepare the video locally. Never connect to YouTube or upload unless the user
explicitly approves after reviewing the final preview, channel, metadata, and
visibility. Never ask for passwords, OAuth secrets, or tokens in chat.

## Topic-only workflow

1. Use `.codex/youtube/voice_defaults.json` when `.codex/youtube/voice.md` is
   still an unfilled template. Do not block topic-only generation on optional
   preferences. Ask only when a tradition, scripture, factual claim, or
   pronunciation cannot safely be inferred. Do not invent sources or promises.
2. Use existing `yt-script` for five Telugu hooks and a spoken script. Score
   each hook by calling the sibling `hookscore.py --hook "..." --json`; use its
   actual score and reasons, never invent them.
3. Use `yt-package` and `yt-seo` for Telugu title, description, and hashtags.
   Other Skills are used when relevant: edit needs a transcript; retention
   needs an export; viral needs a local dataset; plan/comment/audit/shorts
   repurposing do not add value to a single new Short without their inputs.
4. Divide the script into ordered scene narrations and original, license-safe
   visual prompts. Do not imply generated visuals document real events.
5. Produce UTF-8 JSON matching `docs/PROJECT_MANIFEST.md`. Include topic,
   script, scored hooks, scenes, Telugu metadata. Do not guess made-for-kids or
   synthetic-media declarations; the creator decides those at approval.
6. Check local prerequisites. The topic-to-text manifest can still be prepared
   without render tools, but complete MP4 generation requires both FFmpeg and
   the optional local Telugu TTS dependencies/model or a local narration WAV.
   Run the read-only check:

   ```powershell
   $env:PYTHONPATH = "src"
   python -m telugu_shorts.cli doctor
   python -m telugu_shorts.cli prepare project-manifest.json --tts
   python -m telugu_shorts.cli render build/shorts/<project-id> --voice build/shorts/<project-id>/narration.wav
   python -m telugu_shorts.cli preview build/shorts/<project-id>
   ```

7. If the local TTS stack is not installed, use an authorized local WAV and do
   not claim voice automation is ready. First model use downloads the Telugu
   checkpoint from Hugging Face; it is local inference, with no paid API.
   Scene-level TTS durations drive scene transitions and caption boundaries;
   individual cue positions within a scene are estimated by word count and
   should be reviewed.
8. For audio, use the optional local Telugu model or an authorized local WAV.
   Music is optional and requires an ownership/license note. No paid API is
   used. FFmpeg and model dependencies are external local prerequisites; this
   Skill never installs them.
9. Only after the user reviews the final preview and upload details, use
   `approve-upload`. It requires a confirmation phrase and binds approval to
   video and metadata hashes. `upload` is separate and refuses if anything
   changed.
