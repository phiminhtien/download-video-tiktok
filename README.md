# TikTok Downloader — No Watermark

Download TikTok videos and image slideshows without watermark.

## Features

- Download TikTok videos without watermark
- Download image slideshows with all photos + audio
- **CLI mode** — command line
- **Web UI** — browser interface
- **Docker support** — one command to run

## Project Structure

```
├── app/                  # Web application
│   ├── web.py
│   ├── templates/
│   └── static/
├── downloads/            # Downloaded files (auto-created)
├── main.py               # CLI entry point
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### CLI

```bash
python main.py "https://www.tiktok.com/@user/video/123456789"
```

### Web UI (local)

```bash
python app/web.py
# Open http://127.0.0.1:8000
```

### Docker

```bash
docker compose up -d
# Open http://localhost:8000
```

## Troubleshooting

```bash
pip install -U yt-dlp
```

Install [ffmpeg](https://ffmpeg.org/download.html) for best quality.
