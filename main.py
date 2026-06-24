import sys
import os
import re
import subprocess
import json
from pathlib import Path


def check_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def download_with_ytdlp(url: str, output_dir: str) -> str | None:
    """Download TikTok video without watermark using yt-dlp."""
    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")

    cmd = [
        sys.executable, "-m", "yt_dlp",
        url,
        "-o", output_template,
        "--no-playlist",
        "--no-warnings",
        "--print", "after_move:filepath",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            filepath = result.stdout.strip().split("\n")[-1].strip()
            if filepath and os.path.exists(filepath):
                return filepath
        else:
            print(f"  yt-dlp error: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        print("  Download timed out.")
    except Exception as e:
        print(f"  Error: {e}")
    return None


def download_direct(url: str, output_dir: str) -> str | None:
    """Fallback: download using direct requests approach."""
    import requests

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        # Parse video ID from URL
        vid_match = re.search(r"video/(\d+)", url)
        if not vid_match:
            # Try short URL
            r = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
            vid_match = re.search(r"video/(\d+)", r.url)
            if not vid_match:
                return None

        video_id = vid_match.group(1)

        # Get page
        page_url = f"https://www.tiktok.com/@-/video/{video_id}"
        r = requests.get(page_url, headers=headers, timeout=15)
        html = r.text

        # Extract playAddr from HTML
        patterns = [
            r'"playAddr"\s*:\s*"([^"]+)"',
            r'"play_addr"\s*:\s*{[^}]*"url_list"\s*:\s*\["([^"]+)"',
        ]

        play_url = None
        for p in patterns:
            m = re.search(p, html)
            if m:
                play_url = m.group(1).replace("\\u002F", "/").replace("\\/", "/")
                break

        if not play_url:
            return None

        play_url = play_url.replace("playwm", "play")

        # Download
        filename = f"tiktok_{video_id}.mp4"
        output_path = os.path.join(output_dir, filename)

        r = requests.get(play_url, headers=headers, stream=True, timeout=60)
        r.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return output_path if os.path.exists(output_path) else None

    except Exception as e:
        print(f"  Direct download error: {e}")
        return None


def main():
    print("=" * 55)
    print("  TikTok Video Downloader — No Watermark")
    print("=" * 55)

    # Parse URL
    if len(sys.argv) > 1:
        tiktok_url = sys.argv[1]
    else:
        tiktok_url = input("\nEnter TikTok video URL: ").strip()

    if not tiktok_url:
        print("No URL provided.")
        sys.exit(1)

    if "tiktok." not in tiktok_url:
        print("Invalid TikTok URL.")
        sys.exit(1)

    # Output directory
    output_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n  URL: {tiktok_url}")
    print(f"  Output: {output_dir}\\")

    # Check ffmpeg
    if not check_ffmpeg():
        print("  Note: ffmpeg not found. If download fails, install ffmpeg.")
        print("  Download: https://ffmpeg.org/download.html\n")

    # Download with yt-dlp (primary method)
    print("\n  Downloading via yt-dlp...")
    filepath = download_with_ytdlp(tiktok_url, output_dir)

    # Fallback to direct download
    if not filepath:
        print("\n  Trying direct download method...")
        filepath = download_direct(tiktok_url, output_dir)

    if filepath and os.path.exists(filepath):
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        print(f"\n  Saved: {filepath}")
        print(f"  Size:  {size_mb:.2f} MB")
        print("\n  Done!")
    else:
        print("\n  Download failed. Try updating yt-dlp:")
        print(f"    {sys.executable} -m pip install -U yt-dlp")
        sys.exit(1)


if __name__ == "__main__":
    main()
