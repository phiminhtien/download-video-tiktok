import os
import re
import sys
import subprocess
import shutil
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("tiktok")
import threading
import time

import requests
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="TikTok Downloader")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(APP_DIR)
DOWNLOAD_DIR = os.path.join(PROJECT_DIR, "downloads")
DOWNLOAD_TTL = int(os.getenv("DOWNLOAD_TTL", "0"))  # hours, 0 = never clean
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

templates_dir = os.path.join(APP_DIR, "templates")
static_dir = os.path.join(APP_DIR, "static")
os.makedirs(static_dir, exist_ok=True)

templates = Jinja2Templates(directory=templates_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/downloads", StaticFiles(directory=DOWNLOAD_DIR), name="downloads")


def cleanup_old():
    if DOWNLOAD_TTL <= 0:
        return
    now = time.time()
    cutoff = now - DOWNLOAD_TTL * 3600
    for name in os.listdir(DOWNLOAD_DIR):
        path = os.path.join(DOWNLOAD_DIR, name)
        if os.path.isdir(path) and os.path.getmtime(path) < cutoff:
            shutil.rmtree(path, ignore_errors=True)


def start_cleanup():
    cleanup_old()
    if DOWNLOAD_TTL > 0:
        def loop():
            while True:
                time.sleep(3600)
                cleanup_old()
        threading.Thread(target=loop, daemon=True).start()


start_cleanup()


def is_photo_url(url: str) -> bool:
    return "/photo/" in url


def extract_post_id(url: str) -> str | None:
    for p in [r"(?:tiktok\.com/@[\w.-]+/(?:video|photo)/(\d+))", r"vm\.tiktok\.com/(\w+)", r"tiktok\.com/t/(\w+)"]:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def ensure_dir(subdir: str) -> str:
    path = os.path.join(DOWNLOAD_DIR, subdir)
    os.makedirs(path, exist_ok=True)
    return path

def download_photo_via_tikwm(url: str) -> dict:
    """Download all images + audio from TikTok photo slideshow via tikwm.com API."""
    post_id = extract_post_id(url) or "unknown"
    folder = post_id
    out_dir = ensure_dir(folder)
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
            filename = f"{i:03d}.{ext}"
            filepath = os.path.join(out_dir, filename)
            with open(filepath, "wb") as f:
                for chunk in img_resp.iter_content(8192):
                    f.write(chunk)
            size = os.path.getsize(filepath)
            total_size += size
            files.append(f"{folder}/{filename}")

        # Also download audio (music)
        music_url = data.get("data", {}).get("music", "") or data.get("data", {}).get("music_info", {}).get("play", "")
        if music_url:
            try:
                audio_resp = requests.get(music_url, timeout=30, stream=True)
                audio_resp.raise_for_status()
                audio_name = "audio.mp3"
                audio_path = os.path.join(out_dir, audio_name)
                with open(audio_path, "wb") as f:
                    for chunk in audio_resp.iter_content(8192):
                        f.write(chunk)
                audio_size = os.path.getsize(audio_path)
                total_size += audio_size
                files.append(f"{folder}/{audio_name}")
            except Exception as e:
                print(f"  Audio download failed: {e}")

        return {
            "success": True,
            "type": "images",
            "files": files,
            "size_mb": round(total_size / 1024 / 1024, 2),
            "folder": folder,
        }
    except requests.RequestException as e:
        logger.error(f"Photo API error: {e}")
        return {"success": False, "error": "Tải thất bại"}
    except Exception as e:
        logger.error(f"Photo download error: {e}", exc_info=True)
        return {"success": False, "error": "Lỗi máy chủ"}


def download_ytdlp(url: str) -> dict:
    """Download video via yt-dlp."""
    post_id = extract_post_id(url) or "video"
    out_dir = ensure_dir(post_id)
    output_video = os.path.join(out_dir, "%(id)s.%(ext)s")

    cmd = [
        sys.executable, "-m", "yt_dlp",
        url,
        "-o", output_video,
        "-S", "vcodec:h264",
        "--no-playlist",
        "--no-warnings",
        "--print", "after_move:filepath",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        files = []
        total_size = 0

        if result.returncode == 0:
            for f in result.stdout.strip().splitlines():
                f = f.strip()
                if f and os.path.exists(f):
                    files.append(f"{post_id}/{os.path.basename(f)}")
                    total_size += os.path.getsize(f)

        # Also download audio from tikwm API
        try:
            api_resp = requests.post(
                "https://www.tikwm.com/api/",
                data={"url": url, "count": 1, "hd": 1},
                timeout=30,
            )
            api_data = api_resp.json()
            if api_data.get("code") == 0:
                music_url = api_data.get("data", {}).get("music", "") or api_data.get("data", {}).get("music_info", {}).get("play", "")
                if music_url:
                    audio_resp = requests.get(music_url, timeout=30, stream=True)
                    audio_resp.raise_for_status()
                    audio_name = "audio.mp3"
                    audio_path = os.path.join(out_dir, audio_name)
                    with open(audio_path, "wb") as af:
                        for chunk in audio_resp.iter_content(8192):
                            af.write(chunk)
                    audio_size = os.path.getsize(audio_path)
                    total_size += audio_size
                    files.append(f"{post_id}/{audio_name}")
        except Exception as e:
            print(f"  Audio download failed: {e}")

        if files:
            return {
                "success": True,
                "type": "video",
                "files": files,
                "size_mb": round(total_size / 1024 / 1024, 2),
                "folder": post_id,
            }
        logger.warning(f"Video download failed: {result.stderr.strip()}")
        return {"success": False, "error": "Tải thất bại"}
    except subprocess.TimeoutExpired:
        logger.error(f"Download timed out: {url}")
        return {"success": False, "error": "Quá thời gian chờ"}
    except Exception as e:
        logger.error(f"Download error: {e}", exc_info=True)
        return {"success": False, "error": "Lỗi máy chủ"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/api/download")
async def api_download(url: str = Form(...)):
    url = url.strip()
    if not url or "tiktok" not in url:
        return JSONResponse({"success": False, "error": "Link không hợp lệ"})

    logger.info(f"Download request: {url}")

    if is_photo_url(url):
        result = download_photo_via_tikwm(url)
        return JSONResponse(result)

    result = download_ytdlp(url)
    return JSONResponse(result)


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
