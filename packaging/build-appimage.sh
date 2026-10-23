#!/bin/bash
# Builds DemonsSouls-KytyPS5-Launcher-x86_64.AppImage: the launcher with its own Python 3.12 and PyQt6, trimmed to
# what it uses. Used by the release workflow (.github/workflows/appimage.yml) and locally:
#   packaging/build-appimage.sh [output folder]      (default: dist/)
set -e
repo="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.."
repo="$(realpath "$repo")"
out="$(realpath -m "${1:-$repo/dist}")"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

python3 -m venv "$work/venv"
"$work/venv/bin/pip" install -q python-appimage
cd "$work"
# (--no-packaging: python-appimage names the AppDir after the menu entry, "Demon's Souls (KytyPS5)", and runs
# appimagetool through an unquoted shell command, which the apostrophe breaks.)
"$work/venv/bin/python-appimage" build app --no-packaging -p 3.12 -n DemonsSouls-KytyPS5-Launcher \
  -x "$repo/des-launcher.py" "$repo/des-update.py" "$repo/packaging/appimage/des-launcher.png" \
  -- "$repo/packaging/appimage"
mv ./*-x86_64 AppDir
python3 "$repo/packaging/trim_appdir.py" AppDir
appimagetool="$("$work/venv/bin/python-appimage" which appimagetool)"
mkdir -p "$out"
ARCH=x86_64 "$appimagetool" --no-appstream AppDir "$out/DemonsSouls-KytyPS5-Launcher-x86_64.AppImage"
ls -l "$out/DemonsSouls-KytyPS5-Launcher-x86_64.AppImage"
