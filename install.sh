#!/bin/bash
# Installs KytyPS5 (chenxiao07's official Linux release) with the Demon's Souls launcher, and adds the launcher to
# the application menu.
#   ./install.sh                  into ~/Games/KytyPS5-DeS
#   ./install.sh <folder>         into that folder (an existing KytyPS5 Linux folder gets the launcher added)
# Running it again updates the launcher's files; the emulator is updated from the launcher (Check for updates).
set -e
here="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
dest="$(realpath -m "${1:-$HOME/Games/KytyPS5-DeS}")"

command -v python3 >/dev/null || { echo "python3 is needed" >&2; exit 1; }
if ! python3 -c "import PyQt6.QtWidgets" 2>/dev/null; then
  echo "The launcher needs PyQt6:" >&2
  echo "  Arch / CachyOS / Manjaro:  sudo pacman -S python-pyqt6" >&2
  echo "  Debian / Ubuntu / Mint:    sudo apt install python3-pyqt6" >&2
  echo "  Fedora:                    sudo dnf install python3-pyqt6" >&2
  echo "  openSUSE:                  sudo zypper install python3-PyQt6" >&2
  exit 1
fi
command -v vulkaninfo >/dev/null || echo "note: vulkaninfo (vulkan-tools) is not installed: the GPU list stays on Auto"

mkdir -p "$dest"
install -m 755 "$here/des-launcher.py" "$here/des-update.py" "$dest/"
echo "launcher: $dest"

# The emulator: chenxiao07's latest Linux release (checked against GitHub's checksum), unless one is there already.
if [ ! -x "$dest/kyty_emulator" ]; then
  python3 "$dest/des-update.py" --yes
else
  echo "emulator: already installed ($("$dest/kyty_emulator" --help 2>/dev/null | head -1)); update it from the launcher"
fi

apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$apps"
cat > "$apps/des-launcher.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Demon's Souls (KytyPS5)
Comment=Unofficial Linux launcher for the KytyPS5 emulator
Exec=python3 "$dest/des-launcher.py"
Path=$dest
Icon=applications-games
Terminal=false
Categories=Game;Emulator;
EOF
echo "menu entry: Demon's Souls (KytyPS5)"
echo
echo "Done. Open it from the menu (or: python3 \"$dest/des-launcher.py\"), choose your Demon's Souls folder, and"
echo "press Precompile shaders once before playing."
