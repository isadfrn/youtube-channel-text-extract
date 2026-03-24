#!/usr/bin/env python3
"""Core download logic for ytextract."""

import re
import sys
from pathlib import Path

import yt_dlp

YOUTUBE_URL_RE = re.compile(
    r"^https?://(?:www\.)?(?:youtube\.com/(?:(?:@|c/|channel/|user/)[\w-]+|playlist\?list=[\w-]+|watch\?v=[\w-]+)|youtu\.be/[\w-]+)",
    re.IGNORECASE,
)

# Characters not allowed in directory names on Windows (and generally safe to strip elsewhere)
_INVALID_DIRNAME_RE = re.compile(r'[\\/:*?"<>|]')


def get_desktop_path() -> Path:
    """Return the path to the user's Desktop directory (Windows, Linux, Mac)."""
    return Path.home() / "Desktop"


def sanitize_dirname(name: str) -> str:
    """Remove characters that are invalid in directory names across platforms."""
    name = _INVALID_DIRNAME_RE.sub("_", name)
    return name.strip(". ") or "channel"


def is_youtube_url(url: str) -> bool:
    """Return True if url looks like a valid YouTube URL."""
    return bool(url and YOUTUBE_URL_RE.match(url.strip()))


def get_channel_name(channel_url: str) -> str | None:
    """Fetch the channel/uploader name from YouTube without downloading any media."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "playlist_items": "1",
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(channel_url.strip(), download=False)
            return (
                info.get("uploader")
                or info.get("channel")
                or info.get("title")
            )
    except Exception:
        return None


def download_channel(
    channel_url: str,
    audio_dir: Path,
    audio_format: str = "mp3",
    use_archive: bool = True,
    quiet: bool = False,
) -> int:
    """Download audio from a YouTube channel into audio_dir. Returns 0 on success."""
    url = channel_url.strip()
    if not is_youtube_url(url):
        print("Error: URL does not look like a valid YouTube URL.", file=sys.stderr)
        print(
            "Examples: https://www.youtube.com/@ChannelName, https://www.youtube.com/watch?v=VIDEO_ID",
            file=sys.stderr,
        )
        return 1

    audio_dir = Path(audio_dir).resolve()
    audio_dir.mkdir(parents=True, exist_ok=True)

    # Archive lives in the channel dir (parent of audio/) so it persists across runs
    archive_file = None if not use_archive else (audio_dir.parent / "downloaded.txt")
    outtmpl = str(audio_dir / "%(title)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": "0",
            }
        ],
        "quiet": quiet,
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
