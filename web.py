import os
import re
import sys
import subprocess
import json
import uuid

import requests
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="TikTok Downloader")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/downloads", StaticFiles(directory=DOWNLOAD_DIR), name="downloads")


def is_photo_url(url: str) -> bool:
    return "/photo/" in url


def extract_post_id(url: str) -> str | None:
    for p in [r"(?:tiktok\.com/@[\w.-]+/(?:video|photo)/(\d+))", r"vm\.tiktok\.com/(\w+)", r"tiktok\.com/t/(\w+)"]:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def fetch_images_from_page(url: str) -> list[str] | None:
    """Scrape image URLs from a TikTok photo slideshow page."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.tiktok.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    })
    try:
        session.get("https://www.tiktok.com/", timeout=10)

        for attempt in range(3):
            resp = session.get(url, timeout=15)
            if len(resp.text) < 50000:
                continue

            m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
            if not m:
                continue

            data = json.loads(m.group(1))
            s = json.dumps(data)

            urls = re.findall(r'"(https?://p\d+\.muscdn\.com/img/[^"]+)"', s)
            seen = set()
            unique = [u for u in urls if not (u in seen or seen.add(u))]
            if unique:
                return unique

        return None

    except Exception as e:
        print(f"  Scrape error: {e}")
    return None


def download_images(images: list[str], post_id: str) -> list[str]:
    files = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.tiktok.com/",
    }
    for i, img_url in enumerate(images):
        try:
            resp = requests.get(img_url, headers=headers, stream=True, timeout=30)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "image/webp")
            ext = content_type.split("/")[-1].split(";")[0] or "webp"
            filename = f"{post_id}_{i+1:05d}.{ext}"
            filepath = os.path.join(DOWNLOAD_DIR, filename)
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(8192):
                    if chunk:
                        f.write(chunk)
            files.append(filepath)
        except Exception as e:
            print(f"  Image download error ({i}): {e}")
    return files


def download_ytdlp(url: str) -> dict:
    """Download via yt-dlp (for videos)."""
    output_template = os.path.join(DOWNLOAD_DIR, "%(id)s_%(autonumber)s.%(ext)s")
    cmd = [
        sys.executable, "-m", "yt_dlp",
        url,
        "-o", output_template,
        "--no-playlist",
        "--no-warnings",
        "--print", "after_move:filepath",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            files = [f.strip() for f in result.stdout.strip().splitlines() if f.strip()]
            files = [f for f in files if os.path.exists(f)]
            if files:
                is_video = any(f.lower().endswith((".mp4", ".webm", ".mkv", ".mov")) for f in files)
                total_size = sum(os.path.getsize(f) for f in files)
                return {
                    "success": True,
                    "type": "video" if is_video else "images",
                    "files": [os.path.basename(f) for f in files],
                    "size_mb": round(total_size / 1024 / 1024, 2),
                }
        return {"success": False, "error": result.stderr.strip() or "Download failed"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Download timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/api/download")
async def api_download(url: str = Form(...)):
    url = url.strip()
    if not url or "tiktok" not in url:
        return JSONResponse({"success": False, "error": "Invalid TikTok URL"})

    if is_photo_url(url):
        post_id = extract_post_id(url) or uuid.uuid4().hex[:8]
        images = fetch_images_from_page(url)
        if images:
            files = download_images(images, post_id)
            if files:
                total_size = sum(os.path.getsize(f) for f in files)
                return JSONResponse({
                    "success": True,
                    "type": "images",
                    "files": [os.path.basename(f) for f in files],
                    "size_mb": round(total_size / 1024 / 1024, 2),
                })
        return JSONResponse({"success": False, "error": "Could not extract images from this post"})

    result = download_ytdlp(url)
    return JSONResponse(result)


@app.get("/download/{filename}")
async def download_file(filename: str):
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, filename=filename)
    return JSONResponse({"error": "File not found"}, status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
