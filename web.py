import os
import re
import subprocess
import sys

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


def extract_video_id(url: str) -> str | None:
    patterns = [
        r"(?:tiktok\.com/@[\w.-]+/video/(\d+))",
        r"(?:vm\.tiktok\.com/(\w+))",
        r"(?:tiktok\.com/t/(\w+))",
        r"(?:tiktok\.com/embed/v2/(\d+))",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def download_ytdlp(url: str) -> dict:
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
                is_video = any(f.lower().endswith(('.mp4', '.webm', '.mkv', '.mov')) for f in files)
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
    url = url.strip().replace("/photo/", "/video/")
    if not url or "tiktok" not in url:
        return JSONResponse({"success": False, "error": "Invalid TikTok URL"})

    result = download_ytdlp(url)
    if result["success"]:
        return JSONResponse(result)
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
