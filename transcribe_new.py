from pathlib import Path
import subprocess
import sys

IN_DIR = Path("in")
OUT_DIR = Path("out")

AUDIO_EXTENSIONS = {
    ".mp3",
    ".mp4",
    ".m4a",
    ".wav",
    ".ogg",
    ".opus",
    ".flac",
    ".aac",
    ".wma",
    ".webm",
}

WHISPER_LANGUAGE = "en"
WHISPER_MODEL = "base"  # change to "small" or "medium" if you want better quality


def main() -> None:
    IN_DIR.mkdir(exist_ok=True)
    OUT_DIR.mkdir(exist_ok=True)

    audio_files = [
        file
        for file in IN_DIR.iterdir()
        if file.is_file() and file.suffix.lower() in AUDIO_EXTENSIONS
    ]

    if not audio_files:
        print(f"No audio files found in .\\{IN_DIR}")
        return

    files_to_process = []

    for audio_file in audio_files:
        expected_txt = OUT_DIR / f"{audio_file.stem}.txt"

        if expected_txt.exists():
            print(f"Skipping already transcribed: {audio_file.name}")
        else:
            files_to_process.append(audio_file)

    if not files_to_process:
        print("All files are already transcribed.")
        return

    print(f"Found {len(files_to_process)} file(s) to transcribe.")

    for audio_file in files_to_process:
        print(f"\nTranscribing: {audio_file.name}")

        command = [
            "whisper",
            str(audio_file),
            "--language",
            WHISPER_LANGUAGE,
            "--task",
            "transcribe",
            "--model",
            WHISPER_MODEL,
            "--output_format",
            "txt",
            "--output_dir",
            str(OUT_DIR),
        ]

        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as exc:
            print(f"Failed to transcribe {audio_file.name}")
            print(f"Exit code: {exc.returncode}")
            continue
        except FileNotFoundError:
            print("Whisper command not found.")
            print("Install it with:")
            print("pip install -U openai-whisper")
            sys.exit(1)

    print("\nDone.")


if __name__ == "__main__":
    main()
