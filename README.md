# speech2text

`speech2text` is a small local Python utility for batch transcription.

It scans the `in/` folder for audio and video files, checks `out/` for existing transcripts with the same filename stem, and only transcribes files that do not already have an `out/<stem>.txt` file.

After transcription, it can optionally run a second local formatting step through [Ollama](https://ollama.com/) to clean up punctuation, capitalization, spacing, and paragraph breaks. No paid APIs are used.

## What it does

- Creates `in/` and `out/` if they do not exist.
- Finds supported media files in `in/`.
- Skips files that already have a matching transcript in `out/`.
- Transcribes new files locally with `faster-whisper`.
- Optionally formats the raw transcript locally with an Ollama model.
- Saves the final result as `out/<stem>.txt`.
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
- Ollama installed locally if you want transcript auto-formatting

Install the Python dependency:

```bash
pip install faster-whisper
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
pip install faster-whisper
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
  demo.txt
```

If `out/meeting.txt` already exists, `meeting.mp3` will be skipped on the next run.

## Output behavior

- The script never overwrites an existing `out/<stem>.txt`.
- Each new file produces one output file.
- If Ollama formatting succeeds, the saved text is the cleaned transcript.
- If Ollama is unavailable, times out, or the model is missing, the raw transcript is saved instead.

This means transcription still works even if the local formatting step fails.

## Console output

The script prints concise progress information, including:

- number of inputs found
- skipped files
- files being transcribed
- formatting status
- output path

## Typical workflow

1. Drop new recordings into `in/`.
2. Run `python transcribe_new.py`.
3. Collect finished `.txt` files from `out/`.
4. Repeat later with more files; previously transcribed items are skipped automatically.

## Troubleshooting

### `Failed to load faster-whisper model`

Install the dependency:

```bash
pip install faster-whisper
```

### `ollama not found`

Install Ollama locally, or disable formatting in `.env`:

```env
ENABLE_LLM_FORMATTING=false
```

### `ollama model '...' unavailable`

Pull the configured model:

```bash
ollama pull qwen3.5:9b
```

Or change `OLLAMA_MODEL` in `.env` to a model you already have installed.

## Notes

- This project is designed for local use.
- It does not depend on paid LLM APIs.
- The formatting step is intentionally conservative: it is meant to improve readability, not rewrite the transcript into notes or summaries.
