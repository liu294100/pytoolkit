#!/usr/bin/env python3
"""
MPV Library Downloader

Downloads libmpv-2.dll for IPTV Player.
Run this script before first use.

Download URL:
https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20260610/mpv-dev-x86_64-v3-20260610-git-304426c.7z
"""

import subprocess
import sys
from pathlib import Path

# Run the actual download script in mpv directory
script_dir = Path(__file__).parent
mpv_script = script_dir / "mpv" / "download_mpv.py"

if mpv_script.exists():
    sys.exit(subprocess.call([sys.executable, str(mpv_script)]))
else:
    print(f"[ERROR] Script not found: {mpv_script}")
    print()
    print("Please download manually from:")
    print("https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20260610/mpv-dev-x86_64-v3-20260610-git-304426c.7z")
    print()
    print("Extract libmpv-2.dll to mpv/ directory")
    sys.exit(1)
