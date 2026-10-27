"""Unicode-preserving SRT cue generation."""
import re


def _stamp(seconds):
    value = max(0, round(seconds * 1000))
    hours, value = divmod(value, 3_600_000)
    minutes, value = divmod(value, 60_000)
    secs, millis = divmod(value, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def _caption_chunks(text, max_words, max_line_chars=20):
    words, chunks, lines, line = text.split(), [], [], ""
    count = 0
    for word in words:
        too_wide = bool(line) and len(line) + 1 + len(word) > max_line_chars
        if count >= max_words or (too_wide and len(lines) >= 1):
            if line: lines.append(line)
            chunks.append("\n".join(lines))
            lines, line, count = [], "", 0
            too_wide = False
        if too_wide:
            lines.append(line); line = word
        else:
            line = (line + " " + word).strip()
        count += 1
    if line: lines.append(line)
    if lines: chunks.append("\n".join(lines))
    return chunks


def make_srt(text, duration_seconds, max_words=6):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Subtitles‌కు script అవసరం")
    if duration_seconds <= 0 or max_words < 1:
        raise ValueError("Audio duration, max_words రెండూ సున్నా కంటే ఎక్కువ కావాలి")
    phrases = [x.strip() for x in re.split(r"(?<=[.!?。！？।])\s+|\n+", text.strip()) if x.strip()]
    chunks = []
    for phrase in phrases:
        chunks.extend(_caption_chunks(phrase, max_words))
    weights = [max(1, len(chunk.split())) for chunk in chunks]
    total, cursor, cues = sum(weights), 0.0, []
    for index, (chunk, weight) in enumerate(zip(chunks, weights), 1):
        end = duration_seconds if index == len(chunks) else cursor + duration_seconds * weight / total
        cues.extend((str(index), f"{_stamp(cursor)} --> {_stamp(end)}", chunk, ""))
        cursor = end
    return "\n".join(cues).rstrip() + "\n"


def make_timed_srt(segments, duration_seconds, max_words=5):
    """Place captions within exact scene-audio boundaries; word timing is estimated."""
    cues, cue_no, prior_end = [], 1, 0.0
    for segment in segments:
        text, start, end = segment["text"].strip(), float(segment["start"]), float(segment["end"])
        if not text or start < prior_end or end <= start or end > duration_seconds + .05:
            raise ValueError("Narration timeline segment తప్పుగా ఉంది")
        prior_end = end
        words = text.split()
        chunks = _caption_chunks(text, max_words)
        weights, total = [max(1, len(chunk.split())) for chunk in chunks], max(1, len(words))
        cursor = start
        for index, (chunk, weight) in enumerate(zip(chunks, weights)):
            cue_end = end if index == len(chunks) - 1 else cursor + (end - start) * weight / total
            cues.extend((str(cue_no), f"{_stamp(cursor)} --> {_stamp(cue_end)}", chunk, ""))
            cue_no += 1; cursor = cue_end
    return "\n".join(cues).rstrip() + "\n"
