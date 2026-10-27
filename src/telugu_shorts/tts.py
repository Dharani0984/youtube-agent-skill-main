"""Optional offline Telugu TTS adapter; does not auto-install or call paid APIs."""
import importlib.util
import json
from pathlib import Path
import wave

MODEL_ID = "ai4bharat/indic-parler-tts"


def dependencies_available():
    return all(importlib.util.find_spec(name) is not None for name in ("torch", "transformers", "parler_tts"))


def synthesize_scenes(scenes, output_path, timeline_path, speaker=None, model_id=None,
                      device="cpu", profile_path=None):
    if not scenes or any(not str(scene.get("narration", "")).strip() for scene in scenes):
        raise ValueError("ప్రతి scene‌కు narration అవసరం")
    from .voice import load_voice_defaults
    profile = load_voice_defaults(profile_path)
    speaker = speaker or profile["tts_speaker_default"]
    model_id = model_id or profile["tts_model"]
    if not dependencies_available():
        raise RuntimeError("Offline Telugu TTS‌కు torch, transformers, parler_tts అవసరం; ఏ package auto-install చేయలేదు")
    import numpy as np
    import torch
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer
    model = ParlerTTSForConditionalGeneration.from_pretrained(model_id).to(device)
    tokenizer = AutoTokenizer.from_pretrained(model_id, padding_side="left")
    description = f"{speaker} speaks Telugu. {profile['tts_delivery']}"
    desc = tokenizer(description, return_tensors="pt").to(device)
    rate, cursor, chunks, segments = int(model.config.sampling_rate), 0.0, [], []
    for index, scene in enumerate(scenes):
        text = scene["narration"].strip()
        prompt = tokenizer(text, return_tensors="pt").to(device)
        with torch.no_grad():
            generated = model.generate(input_ids=desc.input_ids, attention_mask=desc.attention_mask,
                prompt_input_ids=prompt.input_ids, prompt_attention_mask=prompt.attention_mask)
        samples = np.asarray(generated.cpu().numpy().squeeze(), dtype="float32").reshape(-1)
        end = cursor + len(samples) / rate
        segments.append({"scene_id": scene["scene_id"], "text": text, "start": cursor, "end": end})
        chunks.append(samples); cursor = end
        if index < len(scenes) - 1:
            pause = np.zeros(round(rate * .18), dtype="float32")
            chunks.append(pause); cursor += len(pause) / rate
    pcm = (np.clip(np.concatenate(chunks), -1.0, 1.0) * 32767).astype("<i2").tobytes()
    output_path, timeline_path = Path(output_path), Path(timeline_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(rate); stream.writeframes(pcm)
    timeline_path.write_text(json.dumps({"sample_rate": rate, "duration_seconds": cursor,
        "segments": segments}, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def synthesize_telugu(text, output_path, speaker=None, model_id=None, device="cpu", profile_path=None):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("TTS input ఖాళీగా ఉండకూడదు")
    output_path = Path(output_path)
    timeline = output_path.with_name("narration-timeline.json")
    return synthesize_scenes([{"scene_id": "scene-001", "narration": text}], output_path,
        timeline, speaker, model_id, device, profile_path)


def wav_duration(path):
    with wave.open(str(path), "rb") as stream:
        if stream.getnframes() <= 0 or stream.getframerate() <= 0:
            raise ValueError("WAVలో audio frames లేవు")
        return stream.getnframes() / stream.getframerate()
