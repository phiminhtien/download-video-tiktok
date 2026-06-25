import os
import re
import sys
import subprocess
import json

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


def download_photo_via_tikwm(url: str) -> dict:
    """Download all images + audio from TikTok photo slideshow via tikwm.com API."""
    post_id = extract_post_id(url) or "unknown"
    try:
        resp = requests.post(
            "https://www.tikwm.com/api/",
            data={"url": url, "count": 20, "hd": 1},
            timeout=30,
        )
        data = resp.json()
        if data.get("code") != 0:
            return {"success": False, "error": data.get("msg", "API error")}

        images = data.get("data", {}).get("images", [])
        if not images:
            return {"success": False, "error": "No images found in this post"}

        files = []
        total_size = 0
        for i, img_url in enumerate(images, 1):
            img_resp = requests.get(img_url, timeout=30, stream=True)
            img_resp.raise_for_status()
            ext = img_resp.headers.get("Content-Type", "image/jpeg").split("/")[-1].split(";")[0]
            if ext not in ("jpeg", "jpg", "png", "webp"):
                ext = "jpg"
            filename = f"{post_id}_{i:03d}.{ext}"
            filepath = os.path.join(DOWNLOAD_DIR, filename)
            with open(filepath, "wb") as f:
                for chunk in img_resp.iter_content(8192):
                    f.write(chunk)
            size = os.path.getsize(filepath)
            total_size += size
            files.append(filename)

        # Also download audio (music)
        music_url = data.get("data", {}).get("music", "") or data.get("data", {}).get("music_info", {}).get("play", "")
        if music_url:
            try:
                audio_resp = requests.get(music_url, timeout=30, stream=True)
                audio_resp.raise_for_status()
                audio_ext = audio_resp.headers.get("Content-Type", "audio/mpeg").split("/")[-1].split(";")[0]
                if audio_ext not in ("mp3", "m4a", "aac", "wav"):
                    audio_ext = "mp3"
                audio_name = f"{post_id}_audio.{audio_ext}"
                audio_path = os.path.join(DOWNLOAD_DIR, audio_name)
                with open(audio_path, "wb") as f:
                    for chunk in audio_resp.iter_content(8192):
                        f.write(chunk)
                audio_size = os.path.getsize(audio_path)
                total_size += audio_size
                files.append(audio_name)
            except Exception as e:
                print(f"  Audio download failed: {e}")

        return {
            "success": True,
            "type": "images",
            "files": files,
            "size_mb": round(total_size / 1024 / 1024, 2),
        }
    except requests.RequestException as e:
        return {"success": False, "error": f"API request failed: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
        result = download_photo_via_tikwm(url)
        return JSONResponse(result)

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
