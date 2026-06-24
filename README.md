# TikTok Video Downloader — No Watermark

Download TikTok videos without watermark — CLI and Web UI.

## Features

- Downloads TikTok videos without watermark
- Supports short URLs (`vm.tiktok.com`)
- **CLI mode** — simple command line
- **Web UI** — beautiful browser interface

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### CLI

```bash
python main.py <tiktok-url>
python main.py  # then paste URL when prompted
```

### Web UI

```bash
python web.py
# Open http://127.0.0.1:8000
```

## Troubleshooting

```bash
pip install -U yt-dlp
```

Install [ffmpeg](https://ffmpeg.org/download.html) for best quality.
