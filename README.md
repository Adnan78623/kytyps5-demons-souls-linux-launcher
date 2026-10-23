# Demon's Souls launcher for KytyPS5 on Linux (unofficial)

A settings window for playing **Demon's Souls (PS5)** on Linux with
[KytyPS5 by chenxiao07](https://github.com/chenxiao07/KytyPS5), an experimental PS5 emulator made for this game.

The emulator itself is **chenxiao07's work**. This project only adds a launcher around their official Linux release:
the installer and the updater download it from their GitHub releases, so you always run their latest build. Bugs in
the emulator belong in [their issues](https://github.com/chenxiao07/KytyPS5/issues); bugs in the launcher, here.

This project is not affiliated with Sony, Bluepoint Games, FromSoftware or the KytyPS5 developers. It contains no
game files: you need your own copy of Demon's Souls (PPSA01340/01341/01342), version 01.007.000 or 01.005.000.

## What it does

- **One-step install** of the latest KytyPS5 Linux release, checked against GitHub's checksum, plus a menu entry.
- **Game check:** tells you whether the folder you chose is Demon's Souls, and a version KytyPS5 runs.
- **Display:** window size, render resolution (the 3D world, 720p to 2160p, in performance mode), frame rate
  (30/60/120 Hz), present mode, fullscreen, HDR.
- **AMD FSR 3**, built into KytyPS5 and working on any GPU: upscaling on the game's PS5 Pro path, frame generation
  (2x), low latency.
- **Shader precompile** in one click (upstream's `precompile-linux.sh`), so new areas do not stutter on their first
  shaders. Progress shows in the launcher.
- **Updates** in one click: shows what changed, keeps the previous version for `./des-update.py --rollback`.
- GPU choice (for PCs with an integrated GPU too), console language, MangoHud, gamescope window scaling, and an
  experimental *Skip intro logos*.

## Requirements

- Linux x86-64 with a CPU that has AVX2, a Vulkan 1.3 GPU with current drivers (Mesa for AMD/Intel), glibc 2.35+
- Python 3 and PyQt6: `sudo pacman -S python-pyqt6` (Arch), `sudo apt install python3-pyqt6` (Debian/Ubuntu),
  `sudo dnf install python3-pyqt6` (Fedora)
- Optional: `vulkan-tools` (GPU list), `mangohud`, `gamescope`

## Install

```
git clone https://github.com/<you>/des-linux-launcher
cd des-linux-launcher
./install.sh
```

This puts KytyPS5 and the launcher in `~/Games/KytyPS5-DeS` (or `./install.sh <folder>`; an existing KytyPS5 Linux
folder gets the launcher added). Then open **Demon's Souls (KytyPS5)** from the application menu, choose the game
folder, and press **Precompile shaders** once (minutes to an hour; it can be stopped and resumes). Run it again
after a GPU driver update.

## Tips

- **Performance mode, not Cinematic**, in the game's settings: the render resolution and FSR 3 apply to the
  performance mode only, and Cinematic renders native 4K at 30 fps.
- **Faster:** lower *Render resolution* and turn on *FSR 3 upscaling* (1080p or higher, or 720p). Keep the window at
  your monitor's size; gamescope scaling is not needed then.
- **Smoother:** *FSR 3 frame generation* with *Frame rate 60 Hz* shows 120 fps on a 120 Hz monitor (a little more input
  lag; *Low latency* helps).
- The log under the buttons shows what the emulator does; `logs/last-run.log` keeps it.

## Files

| File | What it is |
|---|---|
| `des-launcher.py` | the launcher (PyQt6) |
| `des-update.py` | installs and updates KytyPS5 from chenxiao07's releases; `--rollback` goes back one version |
| `install.sh` | installs both and adds the menu entry |

The launcher sets the emulator's own switches (`KYTY_RENDER_HEIGHT`, `KYTY_UPSCALER`, `KYTY_FRAMEGEN`, …) and starts
upstream's `run_ds.sh`, with one line of it changed so that the window size and language can be set.

## License

GPL-2.0, as KytyPS5. See `LICENSE`.
