import sys
import os
import re
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")


def extract_video_id(url: str) -> str | None:
    patterns = [
        r"(?:tiktok\.com/@[\w.-]+/video/(\d+))",
        r"(?:vm\.tiktok\.com/(\w+))",
        r"(?:tiktok\.com/t/(\w+))",
        r"(?:tiktok\.com/embed/v2/(\d+))",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def download_ytdlp(url: str) -> list[str] | None:
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
                return files
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

    tiktok_url = tiktok_url.replace("/photo/", "/video/")
    if not tiktok_url or "tiktok." not in tiktok_url:
        print("Invalid TikTok URL.")
        sys.exit(1)

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    print(f"\n  URL: {tiktok_url}")
    print(f"  Output: {DOWNLOAD_DIR}\\")

    print("\n  Downloading...")
    files = download_ytdlp(tiktok_url)

    if files:
        total = sum(os.path.getsize(f) for f in files)
        print(f"\n  Tải thành công! ({len(files)} file, {total/1024/1024:.2f} MB)")
        for f in files:
            print(f"    - {f}")
        print()
    else:
        print("\n  Download failed. Try updating yt-dlp:")
        print(f"    {sys.executable} -m pip install -U yt-dlp")
        sys.exit(1)


if __name__ == "__main__":
    main()
