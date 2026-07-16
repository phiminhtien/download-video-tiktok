import sys
import os
import re
import subprocess
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")


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


def download_ytdlp(url: str) -> list[str] | None:
    post_id = extract_post_id(url) or "video"
    out_dir = ensure_dir(post_id)
    output_video = os.path.join(out_dir, "%(id)s.%(ext)s")
    output_audio = os.path.join(out_dir, "%(id)s_audio.%(ext)s")

    cmd_video = [sys.executable, "-m", "yt_dlp", url, "-o", output_video, "--no-playlist", "--no-warnings", "--print", "after_move:filepath"]
    try:
        result = subprocess.run(cmd_video, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"  yt-dlp error: {result.stderr.strip()}")
            return None
    except subprocess.TimeoutExpired:
        print("  Download timed out.")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None

    files = []
    for f in result.stdout.strip().splitlines():
        f = f.strip()
        if f and os.path.exists(f):
            files.append(f)

    # Download audio
    cmd_audio = [sys.executable, "-m", "yt_dlp", url, "-o", output_audio, "-f", "bestaudio[ext=m4a]/bestaudio", "--no-playlist", "--no-warnings", "--print", "after_move:filepath"]
    try:
        audio_result = subprocess.run(cmd_audio, capture_output=True, text=True, timeout=120)
        if audio_result.returncode == 0:
            for f in audio_result.stdout.strip().splitlines():
                f = f.strip()
                if f and os.path.exists(f):
                    name, ext = os.path.splitext(os.path.basename(f))
                    new_name = f"{post_id}_audio{ext}"
                    new_path = os.path.join(out_dir, new_name)
                    try:
                        os.rename(f, new_path)
                        files.append(new_path)
                    except OSError:
                        files.append(f)
    except Exception as e:
        print(f"  Audio download failed: {e}")

    return files or None


def download_photo_tikwm(url: str) -> list[str] | None:
    post_id = extract_post_id(url) or "unknown"
    out_dir = ensure_dir(post_id)
    try:
        resp = requests.post("https://www.tikwm.com/api/", data={"url": url, "count": 20, "hd": 1}, timeout=30)
        data = resp.json()
        if data.get("code") != 0:
            print(f"  API error: {data.get('msg')}")
            return None
        images = data.get("data", {}).get("images", [])
        if not images:
            print("  No images found.")
            return None
        files = []
        for i, img_url in enumerate(images, 1):
            r = requests.get(img_url, timeout=30, stream=True)
            r.raise_for_status()
            ext = r.headers.get("Content-Type", "image/jpeg").split("/")[-1].split(";")[0]
            if ext not in ("jpeg", "jpg", "png", "webp"):
                ext = "jpg"
            fp = os.path.join(out_dir, f"{i:03d}.{ext}")
            with open(fp, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            files.append(fp)

        music_url = data.get("data", {}).get("music", "") or data.get("data", {}).get("music_info", {}).get("play", "")
        if music_url:
            try:
                r = requests.get(music_url, timeout=30, stream=True)
                r.raise_for_status()
                audio_ext = r.headers.get("Content-Type", "audio/mpeg").split("/")[-1].split(";")[0]
                if audio_ext not in ("mp3", "m4a", "aac", "wav"):
                    audio_ext = "mp3"
                fp = os.path.join(out_dir, f"audio.{audio_ext}")
                with open(fp, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                files.append(fp)
            except Exception as e:
                print(f"  Audio download failed: {e}")

        return files or None
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
    if "/photo/" in tiktok_url:
        files = download_photo_tikwm(tiktok_url)
    else:
        files = download_ytdlp(tiktok_url)

    if files:
        total = sum(os.path.getsize(f) for f in files)
        print(f"\n  Done! ({len(files)} file(s), {total/1024/1024:.2f} MB)")
        print(f"  Folder: {os.path.dirname(files[0])}\\")
        for f in files:
            print(f"    - {os.path.basename(f)}")
    else:
        print("\n  Download failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
