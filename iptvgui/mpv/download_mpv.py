#!/usr/bin/env python3
"""
MPV Library Downloader

Downloads libmpv-2.dll from GitHub releases.
Supports Windows/Linux/macOS.

Download URL:
https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20260610/mpv-dev-x86_64-v3-20260610-git-304426c.7z
"""

import os
import sys
import shutil
import tempfile
from pathlib import Path

# Target directory
SCRIPT_DIR = Path(__file__).parent
TARGET_FILE = SCRIPT_DIR / "libmpv-2.dll"

# Download URLs
MPV_RELEASE_API = "https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/latest"
MPV_FALLBACK_URL = "https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20260610/mpv-dev-x86_64-v3-20260610-git-304426c.7z"


def download_file(url: str, dest: Path, desc: str = "Downloading") -> bool:
    """Download a file with progress."""
    try:
        import requests
    except ImportError:
        print("[INFO] Installing requests...")
        os.system(f"{sys.executable} -m pip install requests -q")
        import requests
    
    print(f"[INFO] {desc}...")
    print(f"       URL: {url[:80]}...")
    
    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        
        total = int(resp.headers.get('content-length', 0))
        downloaded = 0
        
        with open(dest, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"\r       Progress: {pct}% ({downloaded // 1024 // 1024}MB)", end="", flush=True)
        
        print()
        return True
    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}")
        return False


def get_latest_release_url() -> str | None:
    """Get the latest mpv-dev download URL from GitHub API."""
    try:
        import requests
    except ImportError:
        return None
    
    print("[INFO] Fetching latest release info...")
    
    try:
        resp = requests.get(MPV_RELEASE_API, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            if "mpv-dev-x86_64" in name and name.endswith(".7z"):
                return asset.get("browser_download_url")
    except Exception as e:
        print(f"[WARN] Failed to get latest release: {e}")
    
    return None


def extract_7z(archive: Path, target_file: str, dest_dir: Path) -> bool:
    """Extract a specific file from 7z archive."""
    
    # Try py7zr
    try:
        import py7zr
        print("[INFO] Extracting with py7zr...")
        
        with py7zr.SevenZipFile(archive, 'r') as z:
            # Find the file in archive
            names = z.getnames()
            target = None
            for name in names:
                if name.endswith(target_file):
                    target = name
                    break
            
            if target:
                z.extract(path=dest_dir, targets=[target])
                # Move to correct location if nested
                extracted = dest_dir / target
                if extracted.exists() and extracted != dest_dir / target_file:
                    shutil.move(str(extracted), str(dest_dir / target_file))
                    # Clean up nested dirs
                    for item in dest_dir.iterdir():
                        if item.is_dir():
                            shutil.rmtree(item)
                return True
    except ImportError:
        print("[INFO] Installing py7zr...")
        os.system(f"{sys.executable} -m pip install py7zr -q")
        try:
            import py7zr
            return extract_7z(archive, target_file, dest_dir)
        except Exception:
            pass
    except Exception as e:
        print(f"[WARN] py7zr extraction failed: {e}")
    
    # Try system 7z
    seven_zip_paths = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
        "7z",
        "7za",
    ]
    
    for sz in seven_zip_paths:
        try:
            import subprocess
            result = subprocess.run(
                [sz, "e", str(archive), target_file, f"-o{dest_dir}", "-y"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and (dest_dir / target_file).exists():
                print(f"[INFO] Extracted with {sz}")
                return True
        except Exception:
            continue
    
    return False


def main():
    print("=" * 50)
    print("  MPV Library Downloader")
    print("=" * 50)
    print()
    
    # Check if already exists
    if TARGET_FILE.exists():
        size_mb = TARGET_FILE.stat().st_size / 1024 / 1024
        print(f"[INFO] libmpv-2.dll already exists ({size_mb:.1f} MB)")
        
        response = input("Download again? [y/N]: ").strip().lower()
        if response != 'y':
            print("Skipped.")
            return
    
    # Get download URL
    url = get_latest_release_url() or MPV_FALLBACK_URL
    
    # Download to temp
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        archive = tmpdir / "mpv-dev.7z"
        
        if not download_file(url, archive, "Downloading mpv-dev"):
            print("[ERROR] Download failed!")
            print(f"Please download manually from:")
            print(f"  https://github.com/shinchiro/mpv-winbuild-cmake/releases")
            return 1
        
        print(f"[INFO] Downloaded: {archive.stat().st_size / 1024 / 1024:.1f} MB")
        
        # Extract
        if not extract_7z(archive, "libmpv-2.dll", SCRIPT_DIR):
            print("[ERROR] Extraction failed!")
            print("Please extract manually:")
            print(f"  1. Download mpv-dev-x86_64-*.7z from GitHub")
            print(f"  2. Extract libmpv-2.dll to {SCRIPT_DIR}")
            return 1
    
    # Verify
    if TARGET_FILE.exists():
        size_mb = TARGET_FILE.stat().st_size / 1024 / 1024
        print()
        print("=" * 50)
        print(f"  Download completed!")
        print(f"  File: {TARGET_FILE}")
        print(f"  Size: {size_mb:.1f} MB")
        print("=" * 50)
        return 0
    else:
        print("[ERROR] libmpv-2.dll not found after extraction!")
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
