# speech2text

`speech2text` is a small local Python utility for batch transcription.

It scans the `in/` folder for audio and video files, checks `out/` for existing transcripts with the same filename stem, and only transcribes files that do not already have an `out/<stem>.txt` file.

After transcription, it can optionally run a second local formatting step through [Ollama](https://ollama.com/) to produce a separate Markdown version of the transcript. Formatting is enabled by default, but it is only used when Ollama and the configured local model are available. No paid APIs are used.

## What it does

- Creates `in/` and `out/` if they do not exist.
- Finds supported media files in `in/`.
- Skips files that already have a matching transcript in `out/`.
- Transcribes new files locally with `faster-whisper`.
- Saves the raw transcript as `out/<stem>.txt`.
- Optionally formats the raw transcript locally with an Ollama model into `out/<stem>.md`.
- Optionally saves per-chunk formatted Markdown artifacts in `out/chunks/`.
- Handles errors per file so one failure does not stop the batch.

## Project structure

```text
speech2text/
  AGENTS.md
  README.md
  transcribe_new.py
  .env.example
  in/
  out/
```

Example:

```text
in/interview.mp3
in/lecture.m4a
out/interview.txt
```

In that case:

- `interview.mp3` is skipped
- `lecture.m4a` is transcribed

## Supported input formats

The script currently supports:

- `.mp3`
- `.wav`
- `.m4a`
- `.aac`
- `.ogg`
- `.flac`
- `.mp4`
- `.mkv`
- `.mov`

## Requirements

You need:

- Python 3.11+ recommended
- `faster-whisper`
- `ollama` Python package if you want transcript auto-formatting
- Ollama installed locally if you want transcript auto-formatting

Install the Python dependencies:

```bash
pip install faster-whisper ollama
```

If you want formatting enabled, install Ollama and pull a local model. The current recommended default is:

```bash
ollama pull qwen3.5:9b
```

## Getting started

1. Clone the repository.
2. Install Python dependencies.
3. Copy `.env.example` to `.env`.
4. Adjust settings if needed.
5. Put media files into `in/`.
6. Run the script.

### Windows PowerShell example

```powershell
pip install faster-whisper ollama
Copy-Item .env.example .env
python transcribe_new.py
```

## Configuration

Runtime settings are read from `.env` if the file exists. If a setting is missing, the script uses its built-in default.

Example `.env`:

```env
MODEL_SIZE=base
WHISPER_LANGUAGE=en
ENABLE_LLM_FORMATTING=true
OLLAMA_MODEL=qwen3.5:9b
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_THINK=false
FORMAT_CHUNK_MAX_CHARS=3000
FORMAT_SAVE_CHUNKS=true
```

### Settings

- `MODEL_SIZE`: Whisper model size used by `faster-whisper`
  - Default: `base`
- `WHISPER_LANGUAGE`: language code passed to the transcription model
  - Default: `en`
- `ENABLE_LLM_FORMATTING`: enables or disables the Ollama formatting step
  - Default: `true`
- `OLLAMA_MODEL`: local Ollama model used for transcript cleanup
  - Default: `qwen3.5:9b`
- `OLLAMA_TIMEOUT_SECONDS`: timeout for the formatting step
  - Default: `120`
- `OLLAMA_THINK`: Ollama thinking mode for formatting
  - Allowed values: `false`, `true`, `low`, `medium`, `high`
  - Default: `false`
- `FORMAT_CHUNK_MAX_CHARS`: target chunk size for transcript formatting requests
  - Default: `3000`
- `FORMAT_SAVE_CHUNKS`: saves formatted chunk artifacts under `out/chunks/`
  - Default: `true`

## How to use it

Put source files into `in/`:

```text
in/
  meeting.mp3
  demo.mp4
```

Run:

```bash
python transcribe_new.py
```

Outputs are written here:

```text
out/
  meeting.txt
  meeting.md
  chunks/
    meeting_001.md
  demo.txt
  demo.md
```

If `out/meeting.txt` already exists, `meeting.mp3` will be skipped on the next run.

## Output behavior

- The script never overwrites an existing `out/<stem>.txt`.
- Each new transcription produces a raw `.txt` file.
- If formatting is enabled and Ollama plus the configured model are available, the script writes a formatted `.md` file from each available raw transcript.
- Formatting now preprocesses and splits long transcripts into stateless chunks before sending them to Ollama, then merges the chunk results deterministically.
- When `FORMAT_SAVE_CHUNKS=true`, formatted runs also refresh `out/chunks/<stem>_NNN.md` files for the same transcript.
- If a matching `.md` already exists, the script asks whether you want to regenerate it.
- If several `.md` files already exist, the script shows a checklist-style numbered prompt so you can choose which ones to regenerate.
- If Ollama or the configured model is missing, transcription still runs and the script tells you what to install.
- If any formatting chunk fails, the script skips the final `.md` for that file, leaves the raw `.txt` untouched, and continues with the next file.
- Existing raw `.txt` files can still be formatted on later runs even if no new transcription is needed.

This means transcription still works even if the local formatting step is skipped or fails.

## Console output

The script prints concise progress information, including:

- number of inputs found
- skipped files
- files being transcribed
- formatting status
- chunk count when formatting runs
- raw output path
- markdown output path when formatting runs

## Typical workflow

1. Drop new recordings into `in/`.
2. Run `python transcribe_new.py`.
3. Collect raw `.txt` files and optional formatted `.md` files from `out/`.
4. Repeat later with more files; previously transcribed items are skipped automatically, and existing `.md` files can be selectively regenerated.

## Troubleshooting

### `Failed to load faster-whisper model`

Install the dependency:

```bash
pip install faster-whisper
```

### `python package 'ollama' is not installed`

Install the Python client:

```bash
pip install ollama
```

### Ollama is not reachable

Make sure Ollama is installed and running locally, then pull the configured model:

```bash
ollama serve
ollama pull qwen3.5:9b
```

Or disable formatting in `.env`:

```env
ENABLE_LLM_FORMATTING=false
```

### `ollama model '...' unavailable`

Pull the configured model:

```bash
ollama pull qwen3.5:9b
```

Or change `OLLAMA_MODEL` in `.env` to a model you already have installed.

### Formatting was skipped

Formatting only runs when all of the following are true:

- `ENABLE_LLM_FORMATTING=true`
- Python package `ollama` is installed
- Ollama is installed and reachable
- the configured `OLLAMA_MODEL` is already pulled locally

If one of those is missing, the script still saves the raw `.txt` transcript and prints what to install or configure.

## Notes

- This project is designed for local use.
- It does not depend on paid LLM APIs.
- The formatting step is intentionally conservative: it is meant to improve readability in Markdown, not rewrite the transcript into notes or summaries.
