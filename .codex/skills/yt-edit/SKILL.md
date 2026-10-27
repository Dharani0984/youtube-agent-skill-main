---
name: yt-edit
description: Turn a timestamped Telugu or English transcript into an edit decision list for dead air, filler, and repeated takes.
---

# yt-edit

Run sibling `deadair.py` on supplied SRT, VTT, or Whisper JSON. Use detected timecodes only; do not invent cuts. The tool reports dead-air gaps, filler-only cues, and restarted speech. Review cuts against the actual footage before editing; the tool never modifies media. Telugu filler and repeated phrases are supported. Nothing is published.
