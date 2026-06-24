from pathlib import Path
from typing import Any
import os
import subprocess
import sys

IN_DIR = Path("in")
OUT_DIR = Path("out")
ENV_FILE = Path(".env")

SUPPORTED_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".ogg",
    ".flac",
    ".mp4",
    ".mkv",
    ".mov",
}

DEFAULT_MODEL_SIZE = "base"
DEFAULT_WHISPER_LANGUAGE = "en"
DEFAULT_ENABLE_LLM_FORMATTING = True
DEFAULT_OLLAMA_MODEL = "qwen3.5:9b"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 120

FORMAT_PROMPT = """You are formatting a raw speech-to-text transcript.

Rewrite the transcript using only these allowed changes:
- fix capitalization
- fix punctuation
- fix spacing
- split into readable paragraphs

Rules:
- do not summarize
- do not add facts
- do not remove meaningful content
- do not convert it into notes
- keep the same language as the input
- preserve names, numbers, and wording as closely as possible

Return only the cleaned transcript text.
"""


def load_dotenv(env_file: Path) -> None:
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def get_env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        print(f"Invalid integer for {name}: {value!r}. Using default {default}.")
        return default


load_dotenv(ENV_FILE)

MODEL_SIZE = os.getenv("MODEL_SIZE", DEFAULT_MODEL_SIZE)
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", DEFAULT_WHISPER_LANGUAGE)
ENABLE_LLM_FORMATTING = get_env_bool(
    "ENABLE_LLM_FORMATTING",
    DEFAULT_ENABLE_LLM_FORMATTING,
)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
OLLAMA_TIMEOUT_SECONDS = get_env_int(
    "OLLAMA_TIMEOUT_SECONDS",
    DEFAULT_OLLAMA_TIMEOUT_SECONDS,
)


def load_whisper_model() -> Any:
    try:
        from faster_whisper import WhisperModel

        return WhisperModel(MODEL_SIZE)
    except Exception as exc:
        print("Failed to load faster-whisper model.")
        print("Install it with: pip install faster-whisper")
        print(f"Details: {exc}")
        sys.exit(1)


def collect_input_files() -> list[Path]:
    return sorted(
        file
        for file in IN_DIR.iterdir()
        if file.is_file() and file.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def transcribe_file(model: Any, audio_file: Path) -> str:
    segments, _info = model.transcribe(str(audio_file), language=WHISPER_LANGUAGE)
    text = "".join(segment.text for segment in segments).strip()
    return text


def format_transcript(raw_text: str) -> tuple[str, str]:
    if not ENABLE_LLM_FORMATTING:
        return raw_text, "formatting disabled"

    if not raw_text.strip():
        return raw_text, "empty transcript"

    command = ["ollama", "run", OLLAMA_MODEL, FORMAT_PROMPT]

    try:
        completed = subprocess.run(
            command,
            input=raw_text,
            text=True,
            capture_output=True,
            check=True,
            timeout=OLLAMA_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return raw_text, "ollama not found; saved raw transcript"
    except subprocess.TimeoutExpired:
        return raw_text, "ollama timed out; saved raw transcript"
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        if "pull" in stderr.lower() or "not found" in stderr.lower():
            message = (
                f"ollama model '{OLLAMA_MODEL}' unavailable; run: ollama pull "
                f"{OLLAMA_MODEL}"
            )
        elif stderr:
            message = f"ollama formatting failed: {stderr}"
        else:
            message = "ollama formatting failed; saved raw transcript"
        return raw_text, message

    formatted_text = completed.stdout.strip()
    if not formatted_text:
        return raw_text, "ollama returned empty output; saved raw transcript"

    return formatted_text, f"formatted with ollama ({OLLAMA_MODEL})"


def main() -> None:
    IN_DIR.mkdir(exist_ok=True)
    OUT_DIR.mkdir(exist_ok=True)

    input_files = collect_input_files()
    print(f"Inputs found: {len(input_files)}")

    if not input_files:
        print(f"No supported media files found in .\\{IN_DIR}")
        return

    files_to_process: list[Path] = []

    for input_file in input_files:
        output_file = OUT_DIR / f"{input_file.stem}.txt"
        if output_file.exists():
            print(f"Skipped: {input_file.name} -> {output_file}")
            continue
        files_to_process.append(input_file)

    if not files_to_process:
        print("All matching transcripts already exist.")
        return

    model = load_whisper_model()

    for input_file in files_to_process:
        output_file = OUT_DIR / f"{input_file.stem}.txt"
        print(f"Transcribing: {input_file.name}")

        try:
            raw_transcript = transcribe_file(model, input_file)
            final_transcript, format_status = format_transcript(raw_transcript)
            output_file.write_text(final_transcript + "\n", encoding="utf-8")
        except Exception as exc:
            print(f"Failed: {input_file.name}")
            print(f"Error: {exc}")
            continue

        print(f"Transcribed: {input_file.name}")
        print(f"Formatting: {format_status}")
        print(f"Output: {output_file}")

    print("Done.")


if __name__ == "__main__":
    main()
