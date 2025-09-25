#!/usr/bin/env python3
"""Deploy-friendly main.py

How it finds ZIP URLs (in order):
  1. Environment variable ZIP_URLS (comma-separated)
  2. Environment variable ZIP_URLS_FILE (path to a file with one URL per line)
  3. Local file ./urls.txt (one URL per line)
  4. Command-line positional arguments (any arg starting with http:// or https:// or file://)

If no URLs are found, the script exits *gracefully* with code 0 (so deployments won't fail).
MODE can be set via env var MODE or via command-line --mode / -m. Valid modes: download, play, both.
"""

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
    # Support local files (file:// or direct local path) and remote URLs
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

    # 3. Find video files
    video_files = []
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if file.lower().endswith((".mp4", ".mkv", ".webm", ".mov", ".avi")):
                full_path = os.path.join(root, file)
                video_files.append(full_path)

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

def _urls_from_env():
    env = os.getenv("ZIP_URLS", "").strip()
    if not env:
        return []
    return [u.strip() for u in env.split(",") if u.strip()]

def _urls_from_file_path(path):
    try:
        with open(path, "r") as f:
            lines = [line.strip() for line in f.readlines()]
        return [l for l in lines if l and not l.startswith("#")]
    except Exception:
        return []

def _urls_from_argv():
    # Very permissive: treat any arg that looks like a URL as a URL
    candidates = []
    for a in sys.argv[1:]:
        la = a.lower()
        if la.startswith(("http://", "https://", "file://")):
            candidates.append(a)
    return candidates

def get_urls():
    # 1. ZIP_URLS env var
    urls = _urls_from_env()
    if urls:
        print(f"[+] Found {len(urls)} URL(s) in ZIP_URLS environment variable.")
        return urls

    # 2. ZIP_URLS_FILE env var (path to file)
    path = os.getenv("ZIP_URLS_FILE", "").strip()
    if path:
        expanded = os.path.expanduser(path)
        if os.path.exists(expanded):
            urls = _urls_from_file_path(expanded)
            if urls:
                print(f"[+] Found {len(urls)} URL(s) in ZIP_URLS_FILE: {expanded}")
                return urls
            else:
                print(f"[!] ZIP_URLS_FILE provided but no URLs found in: {expanded}")

    # 3. local urls.txt
    local = os.path.join(os.getcwd(), "urls.txt")
    if os.path.exists(local):
        urls = _urls_from_file_path(local)
        if urls:
            print(f"[+] Found {len(urls)} URL(s) in {local}")
            return urls
        else:
            print(f"[!] Found {local} but it contained no URLs.")

    # 4. command-line args
    urls = _urls_from_argv()
    if urls:
        print(f"[+] Found {len(urls)} URL(s) in command-line arguments.")
        return urls

    return []

def get_mode():
    # precedence: argv --mode / -m, then env MODE, default 'both'
    mode = os.getenv("MODE", "both").lower()
    for i, a in enumerate(sys.argv):
        if a in ("--mode", "-m") and i + 1 < len(sys.argv):
            mode = sys.argv[i + 1].lower()
            break
    if mode not in ("download", "play", "both"):
        print(f"[!] Invalid MODE '{mode}', falling back to 'both'.")
        mode = "both"
    return mode

if __name__ == "__main__":

    urls = get_urls()

    if not urls:
        print("[!] No URLs provided. To supply URLs you can:")
        print("    - set ZIP_URLS environment variable (comma-separated),")
        print("    - set ZIP_URLS_FILE to a path to a file with one URL per line,")
        print("    - create a local 'urls.txt' file with one URL per line,")
        print("    - or pass URLs as command-line args (e.g. python main.py https://...)")
        print("") 
        print("[i] Exiting gracefully (exit code 0) so deployment won't fail.")
        sys.exit(0)

    mode = get_mode()
    print(f"[+] Using mode: {mode}")
    for url in urls:
        print(f"-> Processing: {url}")
        try:
            process_zip_video(url, mode)
        except Exception as e:
            print(f"[!] Error while processing {url}: {e}")
