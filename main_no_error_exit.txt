#!/usr/bin/env python3
import os
import sys
import requests
import zipfile
import tempfile
import subprocess

DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")

def ensure_download_dir():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        print(f"[+] Created download folder: {DOWNLOAD_DIR}")

def download_zip(url, save_path, timeout=30):
    print(f"[+] Downloading ZIP from: {url}")
    r = requests.get(url, stream=True, timeout=timeout)
    r.raise_for_status()
    with open(save_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    print(f"[✓] Saved ZIP: {save_path}")

def unzip_file(zip_path, extract_to):
    print(f"[+] Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"[✓] Extracted to: {extract_to}")

def play_video(video_path):
    print(f"[▶] Playing: {video_path}")
    try:
        if os.name == "nt":  # Windows
            os.startfile(video_path)
        elif os.name == "posix":  # Linux/Mac
            subprocess.Popen(["xdg-open", video_path])
        else:
            print("Open manually:", video_path)
    except Exception as e:
        print("Could not play video automatically:", e)

def process_zip_video(url, mode="both"):
    ensure_download_dir()
    temp_dir = tempfile.mkdtemp()
    if url.startswith("file://"):
        zip_path = url[len("file://"):]
        if not os.path.exists(zip_path):
            print(f"[!] Local file not found: {zip_path}")
            return
    elif os.path.exists(url):
        zip_path = url
    else:
        zip_path = os.path.join(temp_dir, "video.zip")
        try:
            download_zip(url, zip_path)
        except Exception as e:
            print(f"[!] Failed to download {url}: {e}")
            return

    try:
        unzip_file(zip_path, temp_dir)
    except zipfile.BadZipFile:
        print(f"[!] The file {zip_path} is not a valid zip archive.")
        return
    except Exception as e:
        print(f"[!] Error extracting {zip_path}: {e}")
        return

    video_files = []
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if file.lower().endswith((".mp4", ".mkv", ".webm", ".mov", ".avi")):
                video_files.append(os.path.join(root, file))

    if not video_files:
        print("[!] No video files found in the ZIP")
        return

    for vid in video_files:
        dest_path = os.path.join(DOWNLOAD_DIR, os.path.basename(vid))
        if mode in ("download", "both"):
            try:
                with open(vid, "rb") as src, open(dest_path, "wb") as dst:
                    dst.write(src.read())
                print(f"[✓] Saved: {dest_path}")
            except Exception as e:
                print(f"[!] Failed to save {vid} -> {dest_path}: {e}")

        if mode in ("play", "both"):
            target = dest_path if os.path.exists(dest_path) else vid
            play_video(target)

def get_urls():
    urls = []
    env_urls = os.getenv("ZIP_URLS", "").strip()
    if env_urls:
        urls = [u.strip() for u in env_urls.split(",") if u.strip()]

    if not urls:
        file_var = os.getenv("ZIP_URLS_FILE", "").strip()
        if file_var and os.path.exists(file_var):
            with open(file_var, "r") as f:
                urls = [line.strip() for line in f if line.strip()]

    if not urls:
        local_file = os.path.join(os.getcwd(), "urls.txt")
        if os.path.exists(local_file):
            with open(local_file, "r") as f:
                urls = [line.strip() for line in f if line.strip()]

    if not urls:
        for a in sys.argv[1:]:
            if a.lower().startswith(("http://", "https://", "file://")):
                urls.append(a.strip())

    return urls

def get_mode():
    mode = os.getenv("MODE", "both").lower()
    for i, a in enumerate(sys.argv):
        if a in ("--mode", "-m") and i + 1 < len(sys.argv):
            mode = sys.argv[i + 1].lower()
            break
    return mode if mode in ("download", "play", "both") else "both"

if __name__ == "__main__":
    urls = get_urls()
    if not urls:
        print("[i] No URLs provided. Nothing to process, exiting gracefully.")
        sys.exit(0)

    mode = get_mode()
    print(f"[+] Using mode: {mode}")
    for url in urls:
        print(f"-> Processing: {url}")
        try:
            process_zip_video(url, mode)
        except Exception as e:
            print(f"[!] Error while processing {url}: {e}")
