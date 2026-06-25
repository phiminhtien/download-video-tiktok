import sys
import os
import re
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")


def extract_post_id(url: str) -> str | None:
    for p in [r"(?:tiktok\.com/@[\w.-]+/(?:video|photo)/(\d+))", r"vm\.tiktok\.com/(\w+)", r"tiktok\.com/t/(\w+)"]:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


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


def download_photo_ytdlp(url: str) -> list[str] | None:
    output_template = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")
    cmd = [
        sys.executable, "-m", "yt_dlp", url, "-o", output_template,
        "--write-thumbnail", "-f", "audio", "--no-playlist", "--no-warnings",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            post_id = extract_post_id(url)
            if post_id:
                pattern = re.compile(re.escape(post_id) + r"\.[a-zA-Z0-9]+")
                files = sorted([f for f in os.listdir(DOWNLOAD_DIR) if pattern.match(f)])
                return [os.path.join(DOWNLOAD_DIR, f) for f in files] or None
            return None
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

    print("\n  Downloading...")
    tiktok_url = tiktok_url.replace("/photo/", "/video/")
    files = download_photo_ytdlp(tiktok_url) if "/photo/" in tiktok_url else download_ytdlp(tiktok_url)

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
