#!/usr/bin/env python3
"""Core transcription logic for ytextract."""

import json
import sys
from pathlib import Path

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".opus", ".webm", ".wav"}


def find_audio_files(root: Path) -> list:
    """Return all audio files under root, recursively."""
    root = Path(root).resolve()
    if not root.is_dir():
        return []
    return sorted(
        p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    )


def write_srt(segments: list, path: Path) -> None:
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


def transcribe_directory(
    input_dir: Path,
    output_dir: Path = None,
    model_name: str = "base",
    force: bool = False,
    with_timestamps: bool = False,
    quiet: bool = False,
) -> int:
    """Transcribe all audio files in input_dir.

    Transcripts are written to output_dir when provided, otherwise next to
    each audio file. Returns 0 on success, 1 on error.
    """
    input_dir = Path(input_dir).resolve()
    if not input_dir.is_dir():
        print(f"Error: Input directory does not exist: {input_dir}", file=sys.stderr)
        return 1

    if output_dir is not None:
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

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

    if not quiet:
        print(f"Loading Whisper model '{model_name}'...")
    try:
        model = whisper.load_model(model_name)
    except Exception as e:
        print(f"Error loading Whisper model: {e}", file=sys.stderr)
        print("Ensure FFmpeg is on your PATH (required by Whisper).", file=sys.stderr)
        return 1

    skipped = 0
    failed = 0
    for i, audio_path in enumerate(audio_files, 1):
        out_base = (output_dir or audio_path.parent) / audio_path.stem
        txt_path = out_base.with_suffix(".txt")
        if txt_path.exists() and not force:
            if not quiet:
                print(f"[{i}/{len(audio_files)}] Skip (exists): {audio_path.name}")
            skipped += 1
            continue

        if not quiet:
            print(f"[{i}/{len(audio_files)}] Transcribing: {audio_path.name}")

        try:
            result = model.transcribe(
                str(audio_path),
                verbose=not quiet,
                fp16=False,
            )
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)
            failed += 1
            continue

        text = (result.get("text") or "").strip()
        txt_path.write_text(text, encoding="utf-8")

        if with_timestamps:
            segments = result.get("segments") or []
            if segments:
                write_srt(segments, out_base.with_suffix(".srt"))
                out_base.with_suffix(".segments.json").write_text(
                    json.dumps(segments, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

    if not quiet:
        done = len(audio_files) - skipped - failed
        print(f"Done: {done} transcribed, {skipped} skipped, {failed} failed.")
    return 1 if failed else 0
