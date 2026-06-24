import os
import re
import subprocess
import sys
import uuid

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


def download_video_ytdlp(url: str) -> tuple[str | None, str | None]:
    output_template = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")
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
            filepath = result.stdout.strip().split("\n")[-1].strip()
            if filepath and os.path.exists(filepath):
                video_id = extract_video_id(url) or uuid.uuid4().hex[:8]
                return filepath, video_id
        return None, result.stderr.strip() if result.stderr else "Unknown error"
    except subprocess.TimeoutExpired:
        return None, "Download timed out"
    except Exception as e:
        return None, str(e)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/api/download")
async def api_download(url: str = Form(...)):
    url = url.strip()
    if not url or "tiktok" not in url:
        return JSONResponse({"success": False, "error": "Invalid TikTok URL"})

    filepath, error = download_video_ytdlp(url)
    if filepath and os.path.exists(filepath):
        filename = os.path.basename(filepath)
        size = os.path.getsize(filepath)
        return JSONResponse({
            "success": True,
            "filename": filename,
            "size_mb": round(size / 1024 / 1024, 2),
            "download_url": f"/downloads/{filename}",
        })

    return JSONResponse({"success": False, "error": error})


@app.get("/download/{filename}")
async def download_file(filename: str):
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, filename=filename)
    return JSONResponse({"error": "File not found"}, status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
