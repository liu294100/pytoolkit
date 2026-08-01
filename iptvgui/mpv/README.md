# MPV Player Library

English | [中文](README_ZH.md)

This directory contains the MPV player library required for video playback.

## Quick Download

### Automatic Download

Run one of the following scripts:

```bash
# Windows
download_mpv.bat

# Python (cross-platform)
python download_mpv.py

# Linux/macOS
./download_mpv.sh
```

### Manual Download (Windows)

1. **Go to releases page:**
   
   https://github.com/shinchiro/mpv-winbuild-cmake/releases/

2. **Download `mpv-dev-x86_64-v3-xxxxxxxx-git-xxxxxxx.7z`:**
   
   Look for the file that starts with `mpv-dev-x86_64` and ends with `.7z`
   
   Example: `mpv-dev-x86_64-v3-20260610-git-304426c.7z`
   
   Direct download link:
   https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20260610/mpv-dev-x86_64-v3-20260610-git-304426c.7z
   
   > ⚠️ Download `mpv-dev-x86_64-*.7z`, NOT `mpv-x86_64-*.7z`
   > 
   > The `mpv-dev` version contains `libmpv-2.dll` which is required.

3. **Extract `libmpv-2.dll`:**
   
   Use 7-Zip or other tools to extract the `.7z` file.
   
   Find `libmpv-2.dll` inside the archive.

4. **Copy to this directory:**
   
   ```
   iptvgui/
   └── mpv/
       └── libmpv-2.dll   <-- Put the file here
   ```

### Manual Download (Linux)

Install via package manager:

```bash
# Ubuntu/Debian
sudo apt install libmpv-dev libmpv1

# Fedora
sudo dnf install mpv-libs-devel

# Arch Linux
sudo pacman -S mpv
```

### Manual Download (macOS)

```bash
brew install mpv
```

## Directory Structure

After setup, this directory should look like:

```
iptvgui/mpv/
├── libmpv-2.dll      # ← Required for Windows (~112 MB)
├── README.md         # English (this file)
├── README_ZH.md      # 中文说明
├── download_mpv.bat  # Windows download script
├── download_mpv.py   # Python download script
└── download_mpv.sh   # Linux/macOS download script
```

## Verification

To verify the file is correctly placed:

```bash
# Windows
dir mpv\libmpv-2.dll

# Should show something like:
# 2026/06/10  12:00    117,532,160 libmpv-2.dll
```

The file size should be approximately **112-120 MB**.

## Troubleshooting

### "MPV not found" error

- Make sure `libmpv-2.dll` is in the `iptvgui/mpv/` directory
- Check file size is ~112 MB (not 0 bytes or very small)
- Try re-downloading

### Download link not working

The releases page occasionally updates. Go to:
https://github.com/shinchiro/mpv-winbuild-cmake/releases/

And download the latest `mpv-dev-x86_64-*.7z` file.

### Extraction failed

- Install [7-Zip](https://www.7-zip.org/) to extract `.7z` files
- Or use Python: `pip install py7zr`

### Hardware decoding not working

1. Update GPU drivers
2. The player will automatically use the best available decoder

## Version Info

- Recommended: Latest release from [shinchiro/mpv-winbuild-cmake](https://github.com/shinchiro/mpv-winbuild-cmake)
- Features: GPU acceleration, H.264/H.265/HEVC hardware decoding
