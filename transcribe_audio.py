#!/usr/bin/env python3
"""
Transcribe downloaded audio files to plain text using OpenAI Whisper (local).
Reads audio from the directory produced by download_channel_audio.py and writes
one .txt per file, suitable for Claude, NotebookLM, etc.
"""

import argparse
import json
import sys
from pathlib import Path

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".opus", ".webm", ".wav"}

def find_audio_files(root: Path) -> list[Path]:
    """Return all audio files under root, recursively."""
    root = root.resolve()
    if not root.is_dir():
        return []
    return sorted(
        p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    )

def write_srt(segments: list[dict], path: Path) -> None:
    """Write segments to an SRT file."""
    def srt_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    for i, seg in enumerate(segments, 1):
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        text = seg.get("text", "").strip()
        lines.append(f"{i}\n{srt_time(start)} --> {srt_time(end)}\n{text}\n")
    path.write_text("\n".join(lines), encoding="utf-8")

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transcribe audio files to text using OpenAI Whisper (local)."
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        type=Path,
        default=Path("downloads"),
        help="Directory containing audio files (default: downloads)",
    )
    parser.add_argument(
        "-m",
        "--model",
        choices=["tiny", "base", "small", "medium", "large"],
        default="base",
        help="Whisper model size (default: base)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-transcribe even if .txt already exists",
    )
    parser.add_argument(
        "--with-timestamps",
        action="store_true",
        help="Also write timestamped segments (SRT + .segments.json) next to each .txt",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Less verbose output",
    )
    args = parser.parse_args()

    input_dir = args.input_dir.resolve()
    if not input_dir.is_dir():
        print(f"Error: Input directory does not exist: {input_dir}", file=sys.stderr)
        return 1

    audio_files = find_audio_files(input_dir)
    if not audio_files:
        print(f"No audio files found under {input_dir}", file=sys.stderr)
        print(
            f"Supported extensions: {', '.join(sorted(AUDIO_EXTENSIONS))}",
            file=sys.stderr,
        )
        return 1

    try:
        import whisper
    except ImportError:
        print(
            "Error: openai-whisper is not installed. Run: pip install openai-whisper",
            file=sys.stderr,
        )
        return 1

    if not args.quiet:
        print(f"Loading Whisper model '{args.model}'...")
    try:
        model = whisper.load_model(args.model)
    except Exception as e:
        print(f"Error loading Whisper model: {e}", file=sys.stderr)
        print("Ensure FFmpeg is on your PATH (required by Whisper).", file=sys.stderr)
        return 1

    skipped = 0
    failed = 0
    for i, audio_path in enumerate(audio_files, 1):
        txt_path = audio_path.with_suffix(".txt")
        if txt_path.exists() and not args.force:
            if not args.quiet:
                print(f"[{i}/{len(audio_files)}] Skip (exists): {audio_path.name}")
            skipped += 1
            continue

        if not args.quiet:
            print(f"[{i}/{len(audio_files)}] Transcribing: {audio_path.name}")

        try:
            result = model.transcribe(
                str(audio_path),
                verbose=not args.quiet,
                fp16=False,
            )
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)
            failed += 1
            continue

        text = (result.get("text") or "").strip()
        txt_path.write_text(text, encoding="utf-8")

        if args.with_timestamps:
            segments = result.get("segments") or []
            if segments:
                srt_path = audio_path.with_suffix(".srt")
                write_srt(segments, srt_path)
                seg_path = audio_path.with_suffix(".segments.json")
                seg_path.write_text(
                    json.dumps(segments, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

    if not args.quiet:
        done = len(audio_files) - skipped - failed
        print(f"Done: {done} transcribed, {skipped} skipped, {failed} failed.")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
