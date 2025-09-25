import os
import requests
import zipfile
import tempfile
import subprocess

DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")

def ensure_download_dir():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        print(f"[+] Created download folder: {DOWNLOAD_DIR}")

def download_zip(url, save_path):
    print(f"[+] Downloading ZIP from: {url}")
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open(save_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
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
    zip_path = os.path.join(temp_dir, "video.zip")

    # 1. Download ZIP
    download_zip(url, zip_path)

    # 2. Unzip into temp folder
    unzip_file(zip_path, temp_dir)

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
            with open(vid, "rb") as src, open(dest_path, "wb") as dst:
                dst.write(src.read())
            print(f"[✓] Saved: {dest_path}")

        if mode in ("play", "both"):
            target = dest_path if os.path.exists(dest_path) else vid
            play_video(target)

if __name__ == "__main__":
    # Ask user for multiple URLs
    print("Enter ZIP URLs (one per line). Press ENTER twice when done:")
    urls = []
    while True:
        line = input().strip()
        if not line:
            break
        urls.append(line)

    if not urls:
        print("[!] No URLs entered. Exiting.")
        exit()

    print("Select Mode:\n1. Download only\n2. Play only\n3. Both (Download + Play)")
    choice = input("Enter choice (1/2/3): ").strip()

    if choice == "1":
        mode = "download"
    elif choice == "2":
        mode = "play"
    else:
        mode = "both"

    for url in urls:
        process_zip_video(url, mode)
