from pathlib import Path
from typing import Any
import os
import re
import sys

IN_DIR = Path("in")
OUT_DIR = Path("out")
ENV_FILE = Path(".env")
RAW_TRANSCRIPT_SUFFIX = ".txt"
FORMATTED_TRANSCRIPT_SUFFIX = ".md"
CHUNKS_DIR = OUT_DIR / "chunks"

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
DEFAULT_OLLAMA_THINK: bool | str = False
DEFAULT_FORMAT_CHUNK_MAX_CHARS = 3000
DEFAULT_FORMAT_SAVE_CHUNKS = True

OLLAMA_TEMPERATURE = 0.1
OLLAMA_TOP_P = 0.9
OLLAMA_REPEAT_PENALTY = 1.1
OLLAMA_NUM_PREDICT = 1200

FORMAT_PROMPT = """You are formatting a raw speech-to-text transcript.

Clean the transcript into readable Markdown using only these allowed changes:
- fix punctuation
- fix spacing
- split into readable paragraphs
- remove obvious false starts or repeated filler when the correction is unambiguous
- add a conservative Markdown heading only when the transcript clearly introduces a section or topic
- preserve speaker turns in Markdown when the dialogue structure is obvious

Rules:
- do not summarize
- do not add facts
- do not remove meaningful content
- do not rewrite for style
- do not convert it into notes
- keep the same language as the input
- preserve names, numbers, and wording as closely as possible
- do not invent section titles that are not supported by the transcript
- do not perform broad editing beyond punctuation, spacing, paragraphing, and clearly safe transcript cleanup
- do not use code fences
- return valid plain Markdown only

Return only the cleaned Markdown transcript text.
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


def get_env_ollama_think(name: str, default: bool | str) -> bool | str:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    if normalized in {"low", "medium", "high"}:
        return normalized

    print(
        f"Invalid Ollama thinking setting for {name}: {value!r}. "
        f"Using default {default!r}."
    )
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
OLLAMA_THINK = get_env_ollama_think(
    "OLLAMA_THINK",
    DEFAULT_OLLAMA_THINK,
)
FORMAT_CHUNK_MAX_CHARS = get_env_int(
    "FORMAT_CHUNK_MAX_CHARS",
    DEFAULT_FORMAT_CHUNK_MAX_CHARS,
)
FORMAT_SAVE_CHUNKS = get_env_bool(
    "FORMAT_SAVE_CHUNKS",
    DEFAULT_FORMAT_SAVE_CHUNKS,
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


def get_raw_output_path(input_file: Path) -> Path:
    return OUT_DIR / f"{input_file.stem}{RAW_TRANSCRIPT_SUFFIX}"


def get_formatted_output_path(input_file: Path) -> Path:
    return OUT_DIR / f"{input_file.stem}{FORMATTED_TRANSCRIPT_SUFFIX}"


def get_chunk_output_dir() -> Path:
    return CHUNKS_DIR


def get_chunk_output_path(stem: str, index: int) -> Path:
    return get_chunk_output_dir() / f"{stem}_{index:03d}{FORMATTED_TRANSCRIPT_SUFFIX}"


def check_formatting_backend() -> tuple[bool, str]:
    if not ENABLE_LLM_FORMATTING:
        return False, "Formatting disabled."

    try:
        import ollama
    except ImportError:
        return (
            False,
            "Formatting skipped: Python package 'ollama' is not installed. "
            "Install it with: pip install ollama",
        )

    try:
        client = ollama.Client(timeout=30)
        client.show(OLLAMA_MODEL)
    except ollama.ResponseError:
        return (
            False,
            f"Formatting skipped: Ollama model '{OLLAMA_MODEL}' is not installed. "
            f"Run: ollama pull {OLLAMA_MODEL}",
        )
    except Exception as exc:
        return False, f"Formatting skipped: could not reach Ollama: {exc}"

    think_mode = OLLAMA_THINK if isinstance(OLLAMA_THINK, str) else str(OLLAMA_THINK).lower()
    return True, (
        f"Formatting enabled with Ollama model '{OLLAMA_MODEL}' "
        f"(think={think_mode})."
    )


def format_prompt_messages(raw_text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": FORMAT_PROMPT},
        {"role": "user", "content": raw_text},
    ]


def extract_formatted_markdown(response: Any) -> str:
    message = getattr(response, "message", None)
    if message is None:
        return ""

    content = getattr(message, "content", "")
    return content.strip() if content else ""


def request_markdown_from_ollama(
    client: Any,
    raw_text: str,
    think_mode: bool | str,
) -> Any:
    return client.chat(
        model=OLLAMA_MODEL,
        messages=format_prompt_messages(raw_text),
        stream=False,
        think=think_mode,
        options={
            "temperature": OLLAMA_TEMPERATURE,
            "top_p": OLLAMA_TOP_P,
            "repeat_penalty": OLLAMA_REPEAT_PENALTY,
            "num_predict": OLLAMA_NUM_PREDICT,
        },
    )


def normalize_transcript_text(raw_text: str) -> str:
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = re.sub(r"[^\S\n]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_long_segment(segment: str, max_chars: int) -> list[str]:
    if len(segment) <= max_chars:
        return [segment]

    sentence_parts = re.split(r"(?<=[.!?])\s+", segment)
    if len(sentence_parts) > 1:
        return pack_segments(sentence_parts, max_chars, separator=" ")

    pieces: list[str] = []
    remaining = segment.strip()
    while remaining:
        if len(remaining) <= max_chars:
            pieces.append(remaining)
            break

        split_at = remaining.rfind(" ", 0, max_chars + 1)
        if split_at <= 0:
            split_at = max_chars

        pieces.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()

    return [piece for piece in pieces if piece]


def pack_segments(
    segments: list[str],
    max_chars: int,
    separator: str = "\n\n",
) -> list[str]:
    chunks: list[str] = []
    current_parts: list[str] = []
    current_length = 0

    for segment in segments:
        cleaned = segment.strip()
        if not cleaned:
            continue

        if len(cleaned) > max_chars:
            if current_parts:
                chunks.append(separator.join(current_parts))
                current_parts = []
                current_length = 0
            chunks.extend(split_long_segment(cleaned, max_chars))
            continue

        separator_length = len(separator) if current_parts else 0
        projected_length = current_length + separator_length + len(cleaned)
        if current_parts and projected_length > max_chars:
            chunks.append(separator.join(current_parts))
            current_parts = [cleaned]
            current_length = len(cleaned)
            continue

        current_parts.append(cleaned)
        current_length = projected_length

    if current_parts:
        chunks.append(separator.join(current_parts))

    return chunks


def split_transcript_chunks(normalized_text: str, max_chars: int) -> list[str]:
    if not normalized_text:
        return [""]

    safe_max_chars = max(200, max_chars)
    paragraphs = normalized_text.split("\n\n")
    return pack_segments(paragraphs, safe_max_chars)


def format_single_chunk(
    client: Any,
    chunk_text: str,
    think_mode: bool | str,
) -> tuple[str | None, bool]:
    response = request_markdown_from_ollama(client, chunk_text, think_mode)
    formatted_text = extract_formatted_markdown(response)
    used_fallback = False

    if not formatted_text and think_mode is not False:
        response = request_markdown_from_ollama(client, chunk_text, False)
        formatted_text = extract_formatted_markdown(response)
        used_fallback = bool(formatted_text)

    if not formatted_text:
        return None, used_fallback

    return formatted_text, used_fallback


def assemble_formatted_markdown(formatted_chunks: list[str]) -> str:
    cleaned_chunks = [chunk.strip() for chunk in formatted_chunks if chunk.strip()]
    if not cleaned_chunks:
        return ""

    merged = "\n\n".join(cleaned_chunks)
    merged = re.sub(r"\n{3,}", "\n\n", merged)
    return merged.strip()


def write_chunk_artifacts(stem: str, formatted_chunks: list[str]) -> list[Path]:
    chunk_dir = get_chunk_output_dir()
    chunk_dir.mkdir(exist_ok=True)

    for existing_path in chunk_dir.glob(f"{stem}_*{FORMATTED_TRANSCRIPT_SUFFIX}"):
        existing_path.unlink()

    written_paths: list[Path] = []
    for index, chunk_text in enumerate(formatted_chunks, start=1):
        chunk_path = get_chunk_output_path(stem, index)
        chunk_path.write_text(chunk_text.rstrip() + "\n", encoding="utf-8")
        written_paths.append(chunk_path)

    return written_paths


def format_transcript_markdown(raw_text: str) -> tuple[str | None, str, list[str], bool]:
    normalized_text = normalize_transcript_text(raw_text)
    if not normalized_text:
        return "", "empty transcript", [""], False

    try:
        import ollama
    except ImportError:
        return None, "python package 'ollama' not found; markdown formatting skipped", [], False

    try:
        client = ollama.Client(timeout=OLLAMA_TIMEOUT_SECONDS)
        chunks = split_transcript_chunks(normalized_text, FORMAT_CHUNK_MAX_CHARS)
    except ollama.ResponseError as exc:
        if "pull" in str(exc).lower() or "not found" in str(exc).lower():
            message = (
                f"ollama model '{OLLAMA_MODEL}' unavailable; run: ollama pull "
                f"{OLLAMA_MODEL}"
            )
        else:
            message = f"ollama formatting failed: {exc}"
        return None, message, [], False
    except Exception as exc:
        return None, f"ollama formatting failed: {exc}", [], False

    formatted_chunks: list[str] = []
    used_fallback = False

    try:
        for chunk_text in chunks:
            if not chunk_text:
                formatted_chunks.append("")
                continue

            formatted_chunk, chunk_used_fallback = format_single_chunk(
                client,
                chunk_text,
                OLLAMA_THINK,
            )
            if formatted_chunk is None:
                return None, "ollama returned empty output; markdown formatting skipped", [], False

            formatted_chunks.append(formatted_chunk)
            used_fallback = used_fallback or chunk_used_fallback
    except ollama.ResponseError as exc:
        if "pull" in str(exc).lower() or "not found" in str(exc).lower():
            return (
                None,
                f"ollama model '{OLLAMA_MODEL}' unavailable; run: ollama pull {OLLAMA_MODEL}",
                [],
                False,
            )
        return None, f"ollama formatting failed: {exc}", [], False
    except Exception as exc:
        return None, f"ollama formatting failed: {exc}", [], False

    formatted_text = assemble_formatted_markdown(formatted_chunks)
    status = f"formatted markdown with ollama ({OLLAMA_MODEL}); chunks={len(chunks)}"
    if FORMAT_SAVE_CHUNKS:
        status += "; chunk artifacts written"
    else:
        status += "; chunk artifacts disabled"
    if used_fallback:
        status += "; retried with think=false after empty chunk response"
    return formatted_text, status, formatted_chunks, True


def prompt_yes_no(message: str) -> bool:
    while True:
        answer = input(f"{message} [y/N]: ").strip().lower()
        if not answer:
            return False
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer y or n.")


def prompt_markdown_regeneration(markdown_files: list[Path]) -> set[Path]:
    if not markdown_files:
        return set()

    if not sys.stdin.isatty():
        print("Markdown already exists; non-interactive mode detected, skipping regeneration.")
        return set()

    if len(markdown_files) == 1:
        markdown_file = markdown_files[0]
        should_regenerate = prompt_yes_no(
            f"Formatted Markdown already exists for {markdown_file.name}. Regenerate it?"
        )
        return {markdown_file} if should_regenerate else set()

    print("Formatted Markdown already exists for these files:")
    for index, markdown_file in enumerate(markdown_files, start=1):
        print(f"[ ] {index}. {markdown_file.name}")

    print("Enter numbers separated by commas to regenerate, 'all' for every file, or press Enter to skip.")

    while True:
        answer = input("Selection: ").strip().lower()
        if not answer:
            return set()
        if answer == "all":
            return set(markdown_files)

        selections: set[Path] = set()
        valid = True

        for part in answer.split(","):
            item = part.strip()
            if not item.isdigit():
                valid = False
                break

            index = int(item)
            if index < 1 or index > len(markdown_files):
                valid = False
                break

            selections.add(markdown_files[index - 1])

        if valid:
            return selections

        print("Please enter comma-separated numbers, 'all', or press Enter to skip.")


def write_markdown_output(raw_output_file: Path, markdown_output_file: Path) -> str:
    raw_transcript = raw_output_file.read_text(encoding="utf-8")
    formatted_markdown, format_status, formatted_chunks, formatting_succeeded = format_transcript_markdown(raw_transcript)
    if formatted_markdown is None:
        raise RuntimeError(format_status)

    if formatting_succeeded and FORMAT_SAVE_CHUNKS:
        write_chunk_artifacts(markdown_output_file.stem, formatted_chunks)

    markdown_output_file.write_text(formatted_markdown.rstrip() + "\n", encoding="utf-8")
    return format_status


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
        output_file = get_raw_output_path(input_file)
        if output_file.exists():
            print(f"Skipped: {input_file.name} -> {output_file}")
            continue
        files_to_process.append(input_file)

    if not files_to_process:
        print("All matching transcripts already exist.")

    formatting_ready, formatting_message = check_formatting_backend()
    if ENABLE_LLM_FORMATTING:
        print(formatting_message)

    model = load_whisper_model() if files_to_process else None

    for input_file in files_to_process:
        output_file = get_raw_output_path(input_file)
        print(f"Transcribing: {input_file.name}")

        try:
            raw_transcript = transcribe_file(model, input_file)
            output_file.write_text(raw_transcript.rstrip() + "\n", encoding="utf-8")
        except Exception as exc:
            print(f"Failed: {input_file.name}")
            print(f"Error: {exc}")
            continue

        print(f"Transcribed: {input_file.name}")
        print(f"Output: {output_file}")

    if formatting_ready:
        markdown_files_to_regenerate = [
            get_formatted_output_path(input_file)
            for input_file in input_files
            if get_raw_output_path(input_file).exists()
            and get_formatted_output_path(input_file).exists()
        ]
        markdown_files_to_generate = [
            get_formatted_output_path(input_file)
            for input_file in input_files
            if get_raw_output_path(input_file).exists()
            and not get_formatted_output_path(input_file).exists()
        ]

        selected_regenerations = prompt_markdown_regeneration(markdown_files_to_regenerate)
        markdown_jobs = sorted(markdown_files_to_generate + list(selected_regenerations))

        for markdown_output_file in markdown_jobs:
            raw_output_file = OUT_DIR / f"{markdown_output_file.stem}{RAW_TRANSCRIPT_SUFFIX}"
            print(f"Formatting: {raw_output_file.name} -> {markdown_output_file.name}")

            try:
                format_status = write_markdown_output(raw_output_file, markdown_output_file)
            except Exception as exc:
                print(f"Failed formatting: {raw_output_file.name}")
                print(f"Error: {exc}")
                continue

            print(f"Formatted: {markdown_output_file}")
            print(f"Formatting status: {format_status}")
    elif ENABLE_LLM_FORMATTING and input_files:
        existing_raw_outputs = [
            get_raw_output_path(input_file)
            for input_file in input_files
            if get_raw_output_path(input_file).exists()
        ]
        if existing_raw_outputs:
            print("Raw transcripts were saved or already available; Markdown formatting was skipped.")

    print("Done.")


if __name__ == "__main__":
    main()
