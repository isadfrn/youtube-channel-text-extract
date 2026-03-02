#!/usr/bin/env python3
"""
Move files from the downloads folder into separate 'audio' and 'texto' folders,
keeping the per-channel structure (e.g. audio/Fabio Akita/, texto/Fabio Akita/).
Keeps downloaded.txt in downloads/ for yt-dlp archive.
"""

import argparse
import shutil
import sys
from pathlib import Path

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".opus", ".webm", ".wav"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Move download files into audio/ and texto/ folders by type."
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        type=Path,
        default=Path("downloads"),
        help="Downloads root (default: downloads)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be moved, do not move.",
    )
    args = parser.parse_args()

    root = args.input_dir.resolve()
    if not root.is_dir():
        print(f"Error: Directory not found: {root}", file=sys.stderr)
        return 1

    audio_root = root.parent / "audio"
    texto_root = root.parent / "texto"
    archive_name = "downloaded.txt"

    moved_audio = 0
    moved_text = 0

    for channel_dir in sorted(root.iterdir()):
        if not channel_dir.is_dir():
            if channel_dir.name != archive_name:
                # e.g. stray file in downloads root
                print(f"Skipping file in root: {channel_dir.name}")
            continue

        channel_name = channel_dir.name
        audio_dest = audio_root / channel_name
        texto_dest = texto_root / channel_name

        for f in channel_dir.iterdir():
            if not f.is_file():
                continue
            if f.suffix.lower() in AUDIO_EXTENSIONS:
                dest = audio_dest / f.name
                if args.dry_run:
                    print(f"  [dry-run] {f} -> {dest}")
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(f), str(dest))
                moved_audio += 1
            elif f.suffix.lower() == ".txt":
                dest = texto_dest / f.name
                if args.dry_run:
                    print(f"  [dry-run] {f} -> {dest}")
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(f), str(dest))
                moved_text += 1
            # skip .srt, .segments.json etc. or move them to texto as well
            elif f.suffix.lower() in (".srt", ".json") and "segments" in f.stem:
                dest = texto_dest / f.name
                if args.dry_run:
                    print(f"  [dry-run] {f} -> {dest}")
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(f), str(dest))
                moved_text += 1

        if not args.dry_run and channel_dir.exists() and not any(channel_dir.iterdir()):
            channel_dir.rmdir()

    print(f"Moved: {moved_audio} audio, {moved_text} text.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
