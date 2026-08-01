#!/bin/bash
#
# MPV Library Downloader for Linux/macOS
#
# Download URL:
# https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20260610/mpv-dev-x86_64-v3-20260610-git-304426c.7z
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  MPV Library Downloader"
echo "========================================"
echo

# Detect OS
OS="$(uname -s)"
case "$OS" in
    Linux*)     PLATFORM="linux";;
    Darwin*)    PLATFORM="macos";;
    MINGW*|MSYS*|CYGWIN*)  PLATFORM="windows";;
    *)          PLATFORM="unknown";;
esac

echo "[INFO] Platform: $PLATFORM"

# For Windows (Git Bash/MSYS), download DLL
if [ "$PLATFORM" = "windows" ]; then
    if [ -f "libmpv-2.dll" ]; then
        echo "[INFO] libmpv-2.dll already exists."
        read -p "Download again? [y/N]: " CONFIRM
        if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
            echo "Skipped."
            exit 0
        fi
    fi
    
    # Try Python script
    if command -v python &> /dev/null; then
        echo "[INFO] Running Python downloader..."
        python download_mpv.py
        exit $?
    fi
    
    # Fallback to curl
    echo "[INFO] Downloading with curl..."
    MPV_URL="https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20260610/mpv-dev-x86_64-v3-20260610-git-304426c.7z"
    
    curl -L -o mpv-dev.7z "$MPV_URL"
    
    if command -v 7z &> /dev/null; then
        7z e mpv-dev.7z libmpv-2.dll -y
    else
        echo "[ERROR] 7z not found. Please install p7zip or extract manually."
        exit 1
    fi
    
    rm -f mpv-dev.7z
    
    if [ -f "libmpv-2.dll" ]; then
        echo
        echo "========================================"
        echo "  Download completed!"
        echo "  File: libmpv-2.dll"
        echo "========================================"
    fi
    exit 0
fi

# For Linux/macOS, install system package
echo
echo "[INFO] On $PLATFORM, mpv is typically installed via package manager."
echo

if [ "$PLATFORM" = "linux" ]; then
    echo "Install commands:"
    echo
    echo "  Ubuntu/Debian:"
    echo "    sudo apt install libmpv-dev libmpv1"
    echo
    echo "  Fedora:"
    echo "    sudo dnf install mpv-libs-devel"
    echo
    echo "  Arch Linux:"
    echo "    sudo pacman -S mpv"
    echo
    echo "  openSUSE:"
    echo "    sudo zypper install libmpv-devel"
    echo
    
    # Try to detect distro and offer auto-install
    if command -v apt &> /dev/null; then
        read -p "Install with apt? [Y/n]: " CONFIRM
        if [ "$CONFIRM" != "n" ] && [ "$CONFIRM" != "N" ]; then
            sudo apt update
            sudo apt install -y libmpv-dev libmpv1
        fi
    elif command -v dnf &> /dev/null; then
        read -p "Install with dnf? [Y/n]: " CONFIRM
        if [ "$CONFIRM" != "n" ] && [ "$CONFIRM" != "N" ]; then
            sudo dnf install -y mpv-libs-devel
        fi
    elif command -v pacman &> /dev/null; then
        read -p "Install with pacman? [Y/n]: " CONFIRM
        if [ "$CONFIRM" != "n" ] && [ "$CONFIRM" != "N" ]; then
            sudo pacman -S --noconfirm mpv
        fi
    fi
    
elif [ "$PLATFORM" = "macos" ]; then
    echo "Install with Homebrew:"
    echo "    brew install mpv"
    echo
    
    if command -v brew &> /dev/null; then
        read -p "Install with brew? [Y/n]: " CONFIRM
        if [ "$CONFIRM" != "n" ] && [ "$CONFIRM" != "N" ]; then
            brew install mpv
        fi
    else
        echo "[WARN] Homebrew not found. Please install from https://brew.sh"
    fi
fi

# Verify installation
echo
echo "[INFO] Checking mpv installation..."

if [ "$PLATFORM" = "linux" ]; then
    if ldconfig -p 2>/dev/null | grep -q libmpv; then
        echo "[OK] libmpv found in system libraries"
        ldconfig -p | grep libmpv
    else
        echo "[WARN] libmpv not found. Please install mpv packages."
    fi
elif [ "$PLATFORM" = "macos" ]; then
    if [ -f "/opt/homebrew/lib/libmpv.dylib" ] || [ -f "/usr/local/lib/libmpv.dylib" ]; then
        echo "[OK] libmpv found"
        ls -la /opt/homebrew/lib/libmpv* /usr/local/lib/libmpv* 2>/dev/null || true
    else
        echo "[WARN] libmpv not found. Please install mpv."
    fi
fi

echo
echo "Done."
