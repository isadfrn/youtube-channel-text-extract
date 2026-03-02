#!/usr/bin/env python3
"""
Download all videos from a YouTube channel as audio only (no video).
Uses yt-dlp with best-audio format; only the audio stream is downloaded.
"""

import argparse
import re
import sys
from pathlib import Path

import yt_dlp

YOUTUBE_URL_RE = re.compile(
    r"^https?://(?:www\.)?(?:youtube\.com/(?:@|c/|channel/|user/|playlist\?list=)|youtu\.be/)[\w-]+",
    re.IGNORECASE,
)

def is_youtube_url(url: str) -> bool:
    """Return True if url looks like a valid YouTube URL."""
    return bool(url and YOUTUBE_URL_RE.match(url.strip()))

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download all videos from a YouTube channel as audio only (no video)."
    )
    parser.add_argument(
        "channel_url",
        help="YouTube channel URL (e.g. https://www.youtube.com/@ChannelName)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("downloads"),
        help="Output directory for audio files (default: downloads)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["mp3", "m4a", "opus", "vorbis", "wav"],
        default="mp3",
        help="Audio format (default: mp3). FFmpeg required for mp3/wav.",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Do not use download archive; re-download all videos.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Less verbose yt-dlp output.",
    )
    args = parser.parse_args()

    url = args.channel_url.strip()
    if not is_youtube_url(url):
        print("Error: URL does not look like a valid YouTube URL.", file=sys.stderr)
        print("Examples: https://www.youtube.com/@ChannelName", file=sys.stderr)
        return 1

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    archive_file = None if args.no_archive else (output_dir / "downloaded.txt")

    outtmpl = str(output_dir / "%(uploader)s" / "%(title)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": args.format,
                "preferredquality": "0",
            }
        ],
        "quiet": args.quiet,
    }
    if archive_file is not None:
        ydl_opts["download_archive"] = str(archive_file)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        print(f"Download error: {e}", file=sys.stderr)
        if "ffmpeg" in str(e).lower() or "ffprobe" in str(e).lower():
            print(
                "FFmpeg may be missing. Install it and ensure it is on your PATH.",
                file=sys.stderr,
            )
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
