# TikTok Video Downloader — No Watermark

A command-line tool to download TikTok videos without the watermark.

## Features

- Downloads TikTok videos without watermark
- Supports short URLs (`vm.tiktok.com`)
- Automatic fallback between yt-dlp and direct scraping
- Simple CLI interface

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/download.html) (optional, for best quality)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py <tiktok-url>
```

Or run without arguments to paste the URL:

```bash
python main.py
```

### Example

```bash
python main.py https://www.tiktok.com/@user/video/123456789
```

Output is saved to the `downloads/` directory.

## Troubleshooting

```bash
pip install -U yt-dlp
```

If ffmpeg is missing, download from [ffmpeg.org](https://ffmpeg.org/download.html). Without it, yt-dlp may fall back to lower quality.
