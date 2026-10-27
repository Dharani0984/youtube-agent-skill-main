---
name: yt-retention
description: Analyze a supplied YouTube Studio retention CSV and transcript to locate hook leaks, cliffs, and gradual slide.
---

# yt-retention

Run sibling `retention.py` on a supplied UTF-8 retention CSV, optionally with its transcript and duration. Validate that the selected CSV columns are position and audience retention before interpreting results. Report hook leak, cliffs, slide, and transcript excerpts only where time alignment is supported. No YouTube connection or publishing.
