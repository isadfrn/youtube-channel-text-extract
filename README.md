# YouTube Channel Text Extract

Download all videos from a YouTube channel as **audio only** (no video), then transcribe them to text locally with **OpenAI Whisper**. The text is ready for Claude, NotebookLM, or any text-based tool.

## Two-step workflow

1. **Download** channel audio: `download_channel_audio.py <channel_url>`
2. **Transcribe** to text: `transcribe_audio.py` (reads from `downloads/` by default)

## Requirements

- **Python 3.8+**
- **FFmpeg** — required for both download (audio conversion) and transcription (Whisper). Install and ensure it is on your PATH.
  - [FFmpeg download](https://ffmpeg.org/download.html)

## Setup

```bash
pip install -r requirements.txt
```

The first time you run transcription, Whisper will download the chosen model (e.g. `base`); this is one-time and runs locally (no API key).

---

## Step 1: Download channel audio

```bash
python download_channel_audio.py "https://www.youtube.com/@ChannelName"
```

Audio files are saved under `downloads/<ChannelName>/` by default.

### Download options

| Option               | Description                                                          |
| -------------------- | -------------------------------------------------------------------- |
| `-o`, `--output-dir` | Output directory (default: `downloads`)                              |
| `-f`, `--format`     | Audio format: `mp3`, `m4a`, `opus`, `vorbis`, `wav` (default: `mp3`) |
| `--no-archive`       | Do not use download archive; re-download all videos                  |
| `-q`, `--quiet`      | Less verbose output                                                  |

### Download examples

```bash
# Download as MP3 to default folder
python download_channel_audio.py "https://www.youtube.com/@SomeChannel"

# Save to a custom folder as M4A
python download_channel_audio.py "https://www.youtube.com/c/ChannelName" -o ./my_audio -f m4a

# Re-run skips already downloaded videos (uses downloaded.txt in output dir)
python download_channel_audio.py "https://www.youtube.com/@ChannelName"
```

---

## Step 2: Transcribe audio to text

```bash
python transcribe_audio.py
```

This scans the default `downloads/` directory (or use `-i` to point elsewhere), finds all audio files, and writes a `.txt` file next to each one (e.g. `Video Title.mp3` → `Video Title.txt`). Already-transcribed files are skipped unless you pass `--force`.

### Transcribe options

| Option              | Description                                                                 |
| ------------------- | --------------------------------------------------------------------------- |
| `-i`, `--input-dir` | Directory containing audio files (default: `downloads`)                     |
| `-m`, `--model`     | Whisper model: `tiny`, `base`, `small`, `medium`, `large` (default: `base`) |
| `--force`           | Re-transcribe even if `.txt` already exists                                 |
| `--with-timestamps` | Also write `.srt` and `.segments.json` next to each transcript              |
| `-q`, `--quiet`     | Less verbose output                                                         |

### Transcribe examples

```bash
# Transcribe everything in downloads/
python transcribe_audio.py

# Use a different folder (e.g. same as custom download output)
python transcribe_audio.py -i ./my_audio

# Use a larger model for better accuracy (slower)
python transcribe_audio.py -m small

# Get SRT and segment JSON alongside each .txt
python transcribe_audio.py --with-timestamps
```

Whisper runs locally (CPU or GPU if available); no API key is required. FFmpeg must be on your PATH.

---

## Step 3 (optional): Organize into audio and text folders

To separate audio and transcripts into dedicated folders (e.g. for backup or upload to other tools):

```bash
python organize_downloads.py
```

This moves files from `downloads/<Channel>/` into:

- **audio/** — all `.mp3`, `.m4a`, etc., under `audio/<Channel>/`
- **texto/** — all `.txt`, `.srt`, `.segments.json`, under `texto/<Channel>/`

The file `downloads/downloaded.txt` (yt-dlp archive) is left in place. Use `--dry-run` to preview moves.

---

## How it works

- **Download:** [yt-dlp](https://github.com/yt-dlp/yt-dlp) with the `bestaudio` format so only the audio stream is downloaded—no video data. FFmpeg converts to your chosen format (e.g. MP3).
- **Transcription:** [OpenAI Whisper](https://github.com/openai/whisper) runs on your machine and writes plain-text transcripts next to each audio file, suitable for uploading to Claude, NotebookLM, or similar tools.
