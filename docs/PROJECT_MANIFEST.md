# Project manifest schema 1

Codex Skills generate the spoken content; Python validates and prepares local
assets. Input is UTF-8 JSON:

```json
{
  "schema_version": 1,
  "project_id": "tirumala-venkateswara",
  "topic": "తిరుమలలో వెంకటేశ్వర స్వామి వైభవం",
  "language": "te-IN",
  "script": "పూర్తి తెలుగు narration...",
  "hooks": [{"text": "శ్రీవారి దర్శన సంప్రదాయం తెలుసా?", "score": 82,
              "reason": "ప్రశ్న ఆసక్తిని రేకెత్తిస్తుంది; వాస్తవ వాదనైతే మూలం చూపాలి."}],
  "scenes": [{"scene_id": "scene-001", "narration": "పూర్తి scriptలోని narration...",
               "visual_prompt": "అసలు జ్యామితీయ గోపురం, ఉదయపు వెలుగు",
               "duration_seconds": null}],
  "metadata": {"title": "తిరుమల శ్రీవారి దర్శనం | భక్తి కథనం",
               "description": "తెలుగులో భక్తి కథనం.",
               "hashtags": ["#తిరుమల", "#భక్తి"]}
}
```

Hook scores must be 0–100, scene IDs unique, and required text nonempty. Scene
narrations joined in order must reproduce the full script exactly (apart from
whitespace normalization); this lets scene changes follow actual TTS segments.
pipeline writes absolute output paths into `project.json` and refuses to reuse
an existing project folder. `made_for_kids` and synthetic-media status are not
guessed; upload approval asks the creator. Output goes under
`build/shorts/<unique-project-id>/` and includes manifest, script, hook scores,
metadata, SRT subtitles, and original geometric PPM visuals. Rendering adds
timed SRT, MP4, and a ffprobe quality report.
