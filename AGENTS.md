# AGENTS.md

## Project

`speech2text` is a local Python batch transcription utility.

## Current behavior

- Read supported media files from `in/`.
- Treat `out/<stem>.txt` as the raw transcript artifact.
- Only transcribe inputs that do not already have `out/<stem>.txt`.
- Optionally generate `out/<stem>.md` from the raw `.txt` using Ollama.
- Never overwrite existing `.txt` files.
- If `.md` already exists, ask before regenerating it.
- Create `in/` and `out/` if missing.

## Implementation guardrails

- Use Python.
- Keep config near the top of `transcribe_new.py`.
- Keep logic simple and readable.
- Match files by stem, ignoring extension.
- Handle errors per file so one failure does not stop the batch.
- Keep console output concise.

## Defaults

- Supported inputs: `.mp3`, `.wav`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.mp4`, `.mkv`, `.mov`
- Transcription backend: `faster-whisper`
- Default Whisper model: `base`
- Default formatting: enabled, but only runs when Ollama and the configured model are available
