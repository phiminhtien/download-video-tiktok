import sys
import os
import re
import subprocess
import json
import uuid

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")


def extract_post_id(url: str) -> str | None:
    for p in [r"(?:tiktok\.com/@[\w.-]+/(?:video|photo)/(\d+))", r"vm\.tiktok\.com/(\w+)", r"tiktok\.com/t/(\w+)"]:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def fetch_images_from_page(url: str) -> list[str] | None:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.tiktok.com/",
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
        print(f"  Error: {e}")
    return None


def download_images(images: list[str], post_id: str) -> list[str]:
    files = []
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.tiktok.com/"}
    for i, img_url in enumerate(images):
        try:
            resp = requests.get(img_url, headers=headers, stream=True, timeout=30)
            resp.raise_for_status()
            ext = resp.headers.get("Content-Type", "image/webp").split("/")[-1].split(";")[0] or "webp"
            fp = os.path.join(DOWNLOAD_DIR, f"{post_id}_{i+1:05d}.{ext}")
            with open(fp, "wb") as f:
                for chunk in resp.iter_content(8192):
                    if chunk:
                        f.write(chunk)
            files.append(fp)
        except Exception as e:
            print(f"  Image download error ({i}): {e}")
    return files


def download_ytdlp(url: str) -> list[str] | None:
    output_template = os.path.join(DOWNLOAD_DIR, "%(id)s_%(autonumber)s.%(ext)s")
    cmd = [sys.executable, "-m", "yt_dlp", url, "-o", output_template, "--no-playlist", "--no-warnings", "--print", "after_move:filepath"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            files = [f.strip() for f in result.stdout.strip().splitlines() if f.strip()]
            return [f for f in files if os.path.exists(f)] or None
        print(f"  yt-dlp error: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        print("  Download timed out.")
    except Exception as e:
        print(f"  Error: {e}")
    return None


def main():
    print("=" * 55)
    print("  TikTok Downloader — No Watermark")
    print("=" * 55)

    if len(sys.argv) > 1:
        tiktok_url = sys.argv[1]
    else:
        tiktok_url = input("\nEnter TikTok URL: ").strip()

    if not tiktok_url or "tiktok" not in tiktok_url:
        print("Invalid TikTok URL.")
        sys.exit(1)

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    print(f"\n  URL: {tiktok_url}")

    if "/photo/" in tiktok_url:
        print("\n  Fetching images...")
        post_id = extract_post_id(tiktok_url) or uuid.uuid4().hex[:8]
        images = fetch_images_from_page(tiktok_url)
        if images:
            files = download_images(images, post_id)
            if files:
                total = sum(os.path.getsize(f) for f in files)
                print(f"\n  Done! ({len(files)} images, {total/1024/1024:.2f} MB)")
                for f in files:
                    print(f"    - {f}")
                return
        print("\n  Failed to extract images.")
        sys.exit(1)

    print("\n  Downloading...")
    files = download_ytdlp(tiktok_url)
    if files:
        total = sum(os.path.getsize(f) for f in files)
        print(f"\n  Done! ({len(files)} file(s), {total/1024/1024:.2f} MB)")
        for f in files:
            print(f"    - {f}")
    else:
        print("\n  Download failed. Try updating yt-dlp:")
        print(f"    {sys.executable} -m pip install -U yt-dlp")
        sys.exit(1)


if __name__ == "__main__":
    main()
