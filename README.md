# Demon's Souls launcher for KytyPS5 on Linux (unofficial)

> [!NOTE]
> **Vibe-coded with Claude.** 🤖⚔️ This launcher was written by Anthropic's Claude (in Claude Code), with a human
> pointing at things and saying "make it do that". It was played and tested on one Linux PC, which is more testing
> than most Souls bosses get before shipping.
>
> If you die, that's the game. If the launcher dies, that's on us: [open an issue](../../issues).
> *Try praising the AI.*

A settings window for playing **Demon's Souls (PS5)** on Linux with
[KytyPS5 by chenxiao07](https://github.com/chenxiao07/KytyPS5), an experimental PS5 emulator made for this game.

The emulator itself is **chenxiao07's work**. This project only adds a launcher around their official Linux release:
the installer and the updater download it from their GitHub releases, so you always run their latest build. Bugs in
the emulator belong in [their issues](https://github.com/chenxiao07/KytyPS5/issues); bugs in the launcher, here.

This project is not affiliated with Sony, Bluepoint Games, FromSoftware or the KytyPS5 developers. It contains no
game files: you need your own copy of Demon's Souls (PPSA01340/01341/01342), version 01.007.000 or 01.005.000.

## Install

1. Download **`DemonsSouls-KytyPS5-Launcher-x86_64.AppImage`** from the
   [latest release](../../releases/latest).
2. Make it executable: right-click → Properties → *Is executable*, or `chmod +x DemonsSouls-KytyPS5-Launcher-x86_64.AppImage`.
3. Double-click it. On first start it offers to add itself to your application menu, then press **⬇ Install KytyPS5**:
   it downloads the emulator (about 100 MB) from chenxiao07's GitHub into `~/Games/KytyPS5-DeS`.

Then choose your Demon's Souls folder, press **⚙ Precompile shaders** once, and **▶ Launch**.

The AppImage brings its own Python and Qt: nothing else to install. If it does not start, your system may lack FUSE 2
(`sudo apt install libfuse2` on Ubuntu 22.04+; on most other distributions it is already there), or run it with
`--appimage-extract-and-run`.

## What it does

- **One-click install** of the latest KytyPS5 Linux release, checked against GitHub's checksum.
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
- Optional: `vulkan-tools` (GPU list), `mangohud`, `gamescope`

### Without the AppImage

With Python 3 and PyQt6 installed (`sudo pacman -S python-pyqt6`, `sudo apt install python3-pyqt6`,
`sudo dnf install python3-pyqt6`):

```
git clone https://github.com/<you>/des-linux-launcher
cd des-linux-launcher
./install.sh
```

This puts KytyPS5 and the launcher in `~/Games/KytyPS5-DeS` (or `./install.sh <folder>`; an existing KytyPS5 Linux
folder gets the launcher added) and adds **Demon's Souls (KytyPS5)** to the application menu.

The precompile takes minutes to an hour the first time, can be stopped, and resumes. Run it again after a GPU driver
update. Your settings, saves, logs and the shader cache are in `~/Games/KytyPS5-DeS` (`DES_HOME` changes it).

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
| `install.sh` | installs both without the AppImage and adds the menu entry |
| `packaging/` | the AppImage build (`build-appimage.sh`), run by `.github/workflows/appimage.yml` for each `v*` tag |

The launcher sets the emulator's own switches (`KYTY_RENDER_HEIGHT`, `KYTY_UPSCALER`, `KYTY_FRAMEGEN`, …) and starts
upstream's `run_ds.sh`, with one line of it changed so that the window size and language can be set.

## License

GPL-2.0, as KytyPS5. See `LICENSE`.
