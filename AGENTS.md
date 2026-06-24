# AGENTS.md

## Project

`speech2text` is a local Python utility for batch transcription.

Main behavior:

* Read media files from `in/`.
* Read existing transcripts from `out/`.
* Match by stem/base name, ignoring extension.
* Transcribe only inputs without `out/<stem>.txt`.
* Save raw transcripts as `out/<stem>.txt`.
* Optionally save formatted Markdown as `out/<stem>.md`.
* Create `in/` and `out/` if missing.
* Running `python transcribe_new.py` should process only new files.

Expected structure:

```text
speech2text/
  AGENTS.md
  transcribe_new.py
  in/
  out/
```

Example:

```text
in/interview.mp3
in/lecture.m4a
out/interview.txt
```

Skip `interview.mp3`; transcribe `lecture.m4a`.

## Implementation rules

* Use Python.
* Keep logic simple and readable.
* Do not hardcode filenames.
* Keep config near the top.
* Never overwrite existing `.txt` outputs unless an explicit overwrite flag is added later.
* If Markdown formatting is enabled, write it to `.md`, not `.txt`.
* If `.md` already exists, ask before regenerating it.
* Handle errors per file so one failure does not stop the batch.
* Print concise progress:

  * inputs found
  * skipped files
  * transcribed files
  * output paths
  * formatting status

## Supported inputs

Use common audio/video extensions:

```python
SUPPORTED_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac",
    ".mp4", ".mkv", ".mov"
}
```

## Transcription backend

Prefer local transcription via `faster-whisper`.

```bash
pip install faster-whisper
```

Default model should be small and easy to change:

```python
MODEL_SIZE = "base"
```
