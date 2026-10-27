---
name: yt-script
description: >-
  Telugu-first YouTube scriptwriting for devotional videos. Use when the user
  wants Telugu hooks, an opening, or a complete spoken script for a devotional
  channel. Can also write in another language when the user asks.
---

# yt-script (Codex edition)

Turn one video idea into a truthful, natural spoken script. Telugu is the
default for this channel. Check `.codex/youtube/voice.md` with
`.codex/youtube/voice_profile.py`; if the profile is incomplete, ask about its
missing fields. Never fill in the creator's voice or tradition by guessing.
Do not assume a specific sampradaya, scripture, deity, ritual, or belief.

## Hook workflow

1. Ask for the topic, intended viewer, video format, and any source or factual
   claims that must appear if the user has not supplied them.
2. Draft five distinct Telugu hooks using the 21 patterns in `hooks.json`.
   Keep each claim supportable. Do not invent dates, counts, miracle claims,
   scriptural quotations, personal experiences, or promised outcomes.
3. Score the five hooks with the sibling `hookscore.py`, then present the best
   two, their Telugu score panels, and a brief explanation of the formula used.
   Scores are rough writing prompts, not predictions of views or retention.
4. Write the spoken script in Telugu, beat by beat. Include `[తెరపై: ...]` for
   every beat, deliver the hook's promised value, estimate runtime using about
   150 spoken words per minute, and end with one appropriate call to action.
5. Use respectful, non-coercive language. Do not imply that a ritual guarantees
   health, wealth, safety, or another result. Attribute religious claims to a
   source when supplied; otherwise ask or phrase them as tradition/belief
   without presenting them as verified fact.

## Running the scorer

The scorer uses only Python's standard library. From the repository root, run:

```powershell
python .codex/skills/yt-script/hookscore.py --hook "మీకు ఈ కథలోని ముఖ్యమైన సందేశం తెలుసా?"
```

For multiple hooks, save one hook per line to a UTF-8 text file and pass its
path. For machine-readable output, add `--json`. Do not assume the current
directory is the skill directory; use the path above or the installed skill's
absolute path. If Python is unavailable, continue with qualitative review and
say that numeric scoring was not run.

## Telugu scoring notes

The scorer uses Unicode word tokens and Telugu cue lists and patterns in
`hooks.json`. Telugu is morphologically rich, so cue matching is approximate;
it may miss inflected forms and dialectal wording. Formula labels identify a
text pattern, not religious correctness, audience response, or video quality.
Read hooks aloud and revise them for the creator's natural speech.

The workflow only drafts text. It does not access YouTube or publish.
