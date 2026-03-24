#!/usr/bin/env python3
"""ytextract — download and transcribe YouTube channel audio in one command."""

import argparse
import sys
from pathlib import Path

from .downloader import download_channel, get_channel_name, get_desktop_path, sanitize_dirname
from .transcriber import transcribe_directory


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="ytextract",
        description=(
            "Download a YouTube channel as audio and transcribe it locally with Whisper. "
            "Output is saved to Desktop/<ChannelName>/audio/ and Desktop/<ChannelName>/transcriptions/."
        ),
    )
    parser.add_argument(
        "channel_url",
        help="YouTube channel URL (e.g. https://www.youtube.com/@ChannelName)",
    )

    # Output location
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=None,
        help=(
            "Base directory where the channel folder will be created "
            "(default: Desktop)"
        ),
    )

    # Download options
    dl = parser.add_argument_group("download")
    dl.add_argument(
        "-f", "--format",
        choices=["mp3", "m4a", "opus", "vorbis", "wav"],
        default="mp3",
        help="Audio format (default: mp3). FFmpeg required for mp3/wav.",
    )
    dl.add_argument(
        "--no-archive",
        action="store_true",
        help="Do not use download archive; re-download all videos.",
    )

    # Transcribe options
    tr = parser.add_argument_group("transcribe")
    tr.add_argument(
        "-m", "--model",
        choices=["tiny", "base", "small", "medium", "large"],
        default="base",
        help="Whisper model size (default: base)",
    )
    tr.add_argument(
        "--force",
        action="store_true",
        help="Re-transcribe even if .txt already exists.",
    )
    tr.add_argument(
        "--with-timestamps",
        action="store_true",
        help="Also write .srt and .segments.json timestamp files.",
    )

    # Common
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Less verbose output.",
    )

    args = parser.parse_args()

    # Resolve base directory (Desktop by default)
    base_dir = args.output_dir.resolve() if args.output_dir else get_desktop_path()

    # Fetch channel name to name the output folder
    if not args.quiet:
        print("Fetching channel info...")
    raw_name = get_channel_name(args.channel_url)
    if not raw_name:
        print(
            "Warning: could not fetch channel name; using 'channel' as folder name.",
            file=sys.stderr,
        )
        raw_name = "channel"
    channel_name = sanitize_dirname(raw_name)

    channel_dir = base_dir / channel_name
    audio_dir = channel_dir / "audio"
    transcriptions_dir = channel_dir / "transcriptions"

    if not args.quiet:
        print(f"Output folder: {channel_dir}")

    print("\n=== Step 1/2: Download ===")
    rc = download_channel(
        channel_url=args.channel_url,
        audio_dir=audio_dir,
        audio_format=args.format,
        use_archive=not args.no_archive,
        quiet=args.quiet,
    )
    if rc != 0:
        return rc

    print("\n=== Step 2/2: Transcribe ===")
    rc = transcribe_directory(
        input_dir=audio_dir,
        output_dir=transcriptions_dir,
        model_name=args.model,
        force=args.force,
        with_timestamps=args.with_timestamps,
        quiet=args.quiet,
    )
    if rc != 0:
        return rc

    return 0


if __name__ == "__main__":
    sys.exit(main())
