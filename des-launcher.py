#!/usr/bin/env python3
"""Demon's Souls launcher for KytyPS5 on Linux (unofficial): a settings window in front of run_ds.sh.

KytyPS5 (chenxiao07's official Linux release) lives in its own folder, KYTY_DIR: the launcher's folder when the
release is there (install.sh), else $DES_HOME, else ~/Games/KytyPS5-DeS (the AppImage, which is read-only). The
launcher downloads it there when it is missing (des-update.py) and keeps it up to date. Settings, logs, saves and the
shader cache are in that folder too (des-launcher.json, logs/, _SaveData/, _PipelineCache/).
"""
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from PyQt6.QtCore import QProcess, QProcessEnvironment
    from PyQt6.QtGui import QFont, QTextCursor
    from PyQt6.QtWidgets import (
        QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
        QDoubleSpinBox, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget,
    )
except ImportError:
    message = ("The launcher needs PyQt6. Arch: sudo pacman -S python-pyqt6; Debian/Ubuntu: sudo apt install "
               "python3-pyqt6; Fedora: sudo dnf install python3-pyqt6")
    print(message, file=sys.stderr)
    if shutil.which("kdialog"):
        subprocess.run(["kdialog", "--error", message])
    sys.exit(1)

HERE = Path(__file__).resolve().parent  # the launcher's own files (des-update.py, the icon)


def kyty_dir():
    if os.environ.get("DES_HOME"):
        return Path(os.environ["DES_HOME"]).expanduser().resolve()
    if (HERE / "run_ds.sh").exists() or (HERE / "kyty_emulator").exists():
        return HERE
    return Path.home() / "Games" / "KytyPS5-DeS"


KYTY_DIR = kyty_dir()
SETTINGS_FILE = KYTY_DIR / "des-launcher.json"
LOG_FILE = KYTY_DIR / "logs" / "last-run.log"
PRECOMPILE_LOG = KYTY_DIR / "logs" / "last-precompile.log"
UPDATE_LOG = KYTY_DIR / "logs" / "last-update.log"
APP_NAME = "Demon's Souls (KytyPS5)"


def python_exe():
    """The Python that runs des-update.py. In the AppImage, sys.executable is the AppImage itself (its Python's wrapper
    reports the command it was started as), which would start a second launcher: its Python is run by path instead."""
    appdir = os.environ.get("APPDIR")
    if appdir and (Path(appdir) / "usr" / "bin" / "python3").exists():
        return str(Path(appdir) / "usr" / "bin" / "python3")
    return sys.executable

RESOLUTIONS = ["1280x720", "1600x900", "1920x1080", "2560x1440", "3840x2160"]
# KYTY_RENDER_HEIGHT (src/loader/demonsSoulsRenderSize.h): the height Demon's Souls renders its 3D at, 16:9; the
# game's output and HUD stay 4K. Unset = the game's own 2560x1440.
RENDER_HEIGHTS = [("720p (1280x720) - fastest", 720), ("900p (1600x900)", 900), ("1080p (1920x1080)", 1080),
                  ("1260p (2240x1260)", 1260), ("1440p (2560x1440) - game default", 1440),
                  ("1800p (3200x1800)", 1800), ("2160p (3840x2160) - sharpest", 2160)]
LANGUAGES = [
    "Japanese", "English (US)", "French", "Spanish", "German", "Italian", "Dutch",
    "Portuguese (PT)", "Russian", "Korean", "Chinese (Traditional)", "Chinese (Simplified)",
    "Finnish", "Swedish", "Danish", "Norwegian", "Polish", "Portuguese (BR)", "English (UK)",
    "Turkish", "Spanish (LatAm)", "Arabic", "French (CA)", "Czech", "Hungarian", "Greek",
    "Romanian", "Thai", "Vietnamese", "Indonesian",
]
UPSCALERS = {"Off": None, "AMD FSR 1 (gamescope)": "fsr", "NVIDIA NIS (gamescope)": "nis",
             "Integer scaling (gamescope)": "integer"}

DEFAULTS = {
    "game": "", "resolution": "", "render_height": 1440, "fullscreen": False, "hdr": False,
    "present_mode": "Mailbox", "fps": 60, "gpu": "auto", "language": 1, "mangohud": True,
    "upscaler": "Off", "output_resolution": "2560x1440", "sharpness": 2,
    "fsr_upscaler": False, "fsr_sharpness": 0.6, "frame_gen": False, "low_latency": False,
    "convars": "doIndexBufferCulling=false", "extra_args": "", "skip_intro": False, "menu_asked": False,
}


# The game this launcher is for: Demon's Souls (PS5), its regions and the versions KytyPS5 runs.
TITLES = {"PPSA01340", "PPSA01341", "PPSA01342"}
VERSIONS = {"01.007.000", "01.005.000"}


def game_info(path):
    """(title, version) from a game folder's sce_sys/param.json, or None (a .zar or no param.json)."""
    try:
        param = json.loads((Path(path) / "sce_sys" / "param.json").read_text(encoding="utf-8"))
        return param.get("titleId", ""), param.get("contentVersion", "")
    except (OSError, ValueError):
        return None


def list_gpus():
    """Vulkan devices in enumeration order, as KYTY_GPU numbers them (the log's "Vulkan GPU <n>:")."""
    try:
        out = subprocess.run(["vulkaninfo", "--summary"], capture_output=True, text=True,
                             timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [line.split("=", 1)[1].strip() for line in out.splitlines()
            if line.strip().startswith("deviceName")]


class Launcher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Demon's Souls — KytyPS5 Launcher (unofficial)")
        self.resize(760, 720)
        self.proc = None
        self.log_handle = None
        self.settings = dict(DEFAULTS)
        try:
            self.settings.update(json.loads(SETTINGS_FILE.read_text()))
        except (OSError, ValueError):
            pass

        if not self.settings["resolution"]:
            # (First start: the window as large as the screen. A window at most 1080 lines high makes the emulator use
            # the game's own 1080p output, softer on a larger screen.)
            screen = QApplication.primaryScreen().size()
            self.settings["resolution"] = f"{screen.width()}x{screen.height()}"

        root = QVBoxLayout(self)

        # Game
        game_box = QGroupBox("Game")
        gv = QVBoxLayout(game_box)
        g = QHBoxLayout()
        gv.addLayout(g)
        self.game = QLineEdit(self.settings["game"])
        self.game.textChanged.connect(self.check_game)
        self.game.setPlaceholderText("Folder with eboot.bin, or a .zar archive")
        pick_dir = QPushButton("Folder…")
        pick_dir.clicked.connect(self.pick_folder)
        pick_zar = QPushButton(".zar…")
        pick_zar.clicked.connect(self.pick_zar)
        g.addWidget(self.game)
        g.addWidget(pick_dir)
        g.addWidget(pick_zar)
        self.game_status = QLabel()
        gv.addWidget(self.game_status)
        self.kyty_status = QLabel()
        self.kyty_status.setWordWrap(True)
        gv.addWidget(self.kyty_status)
        root.addWidget(game_box)

        # Display
        disp_box = QGroupBox("Display")
        d = QFormLayout(disp_box)
        self.resolution = self.combo(RESOLUTIONS, self.settings["resolution"], editable=True)
        self.resolution.setToolTip("The emulator's window. The game's picture is scaled to it; this does not change "
                                   "how much work the GPU does (Render resolution does).")
        d.addRow("Window resolution", self.resolution)
        self.render_height = QComboBox()
        for label, value in RENDER_HEIGHTS:
            self.render_height.addItem(label, value)
        self.render_height.setCurrentIndex(max(0, self.render_height.findData(self.settings["render_height"])))
        self.render_height.setToolTip("The resolution Demon's Souls draws its 3D world at (the HUD stays sharp). "
                                      "Lower = faster if the GPU is the limit, softer picture.")
        d.addRow("Render resolution", self.render_height)
        self.fps = QComboBox()
        for v in (30, 60, 120):
            self.fps.addItem(f"{v} Hz", v)
        self.fps.setCurrentIndex(max(0, self.fps.findData(self.settings["fps"])))
        self.fps.setToolTip("Virtual vblank. Above 60, run_ds.sh adds gameMinDeltaTime so the "
                            "game does not run faster than real time.")
        d.addRow("Frame rate", self.fps)
        self.present = self.combo(["Mailbox", "Fifo", "Immediate"], self.settings["present_mode"])
        self.present.setToolTip("Mailbox: smooth, no tearing. Fifo: strict vsync. "
                                "Immediate: lowest latency, tears.")
        d.addRow("Present mode", self.present)
        self.fullscreen = QCheckBox("Borderless fullscreen")
        self.fullscreen.setChecked(self.settings["fullscreen"])
        self.hdr = QCheckBox("HDR10 output (when supported)")
        self.hdr.setChecked(self.settings["hdr"])
        d.addRow(self.fullscreen)
        d.addRow(self.hdr)
        root.addWidget(disp_box)

        # AMD FSR 3, built into the emulator (KYTY_UPSCALER=fsr, KYTY_FRAMEGEN_BACKEND=fsr): from the game's own
        # depth and motion, so much better than a scaler working on the finished picture.
        fsr_box = QGroupBox("AMD FSR 3 (built into the emulator)")
        f = QFormLayout(fsr_box)
        self.fsr_upscaler = QCheckBox("FSR 3 upscaling (the game's PS5 Pro path)")
        self.fsr_upscaler.setChecked(self.settings["fsr_upscaler"])
        self.fsr_upscaler.setToolTip("FSR 3 makes the game's 4K picture from the Render resolution, in place of Sony's "
                                     "PS5 Pro upscaler. Use Render resolution 1080p or higher (or 720p).")
        self.fsr_upscaler.toggled.connect(self.update_enabled)
        f.addRow(self.fsr_upscaler)
        self.fsr_sharpness = QDoubleSpinBox()
        self.fsr_sharpness.setRange(0.0, 1.0)
        self.fsr_sharpness.setSingleStep(0.1)
        self.fsr_sharpness.setValue(self.settings["fsr_sharpness"])
        self.fsr_sharpness.setToolTip("FSR 3's sharpening: 0.0 = none, 1.0 = most (default 0.6)")
        f.addRow("FSR 3 sharpness", self.fsr_sharpness)
        self.frame_gen = QCheckBox("FSR 3 frame generation (2x: a generated frame between each two)")
        self.frame_gen.setChecked(self.settings["frame_gen"])
        self.frame_gen.setToolTip("Smoother motion (60 fps shown as 120), a little more input lag. Keep Frame rate at "
                                  "60 Hz for 120 on a 120 Hz monitor. Not together with gamescope scaling.")
        self.frame_gen.toggled.connect(self.update_enabled)
        f.addRow(self.frame_gen)
        self.low_latency = QCheckBox("Low latency (one frame queued instead of about two)")
        self.low_latency.setChecked(self.settings["low_latency"])
        self.low_latency.setToolTip("What you press shows sooner (at 60 Hz about 15-23 ms instead of ~30); the frame "
                                    "pacing is a little less even. Helps offset frame generation's lag.")
        f.addRow(self.low_latency)
        root.addWidget(fsr_box)

        # Upscaling of the window by gamescope (FSR 1 / NIS on the finished picture)
        up_box = QGroupBox("Window scaling (gamescope)")
        u = QFormLayout(up_box)
        self.upscaler = self.combo(list(UPSCALERS), self.settings["upscaler"])
        self.upscaler.currentTextChanged.connect(self.update_enabled)
        u.addRow("Scaler", self.upscaler)
        self.output_res = self.combo(RESOLUTIONS, self.settings["output_resolution"], editable=True)
        u.addRow("Output resolution", self.output_res)
        self.sharpness = QSpinBox()
        self.sharpness.setRange(0, 20)
        self.sharpness.setValue(self.settings["sharpness"])
        self.sharpness.setToolTip("0 = sharpest, 20 = softest")
        u.addRow("Sharpness (0 = max)", self.sharpness)
        note = QLabel("Scales the finished window to the output resolution. Usually not needed: lower Render "
                      "resolution (with FSR 3 upscaling above) and keep the window at your monitor's size.")
        note.setWordWrap(True)
        note.setStyleSheet("color: gray;")
        u.addRow(note)
        if not shutil.which("gamescope"):
            self.upscaler.setEnabled(False)
            self.upscaler.setToolTip("Install gamescope to enable upscaling")
        root.addWidget(up_box)

        # System
        sys_box = QGroupBox("System")
        s = QFormLayout(sys_box)
        self.gpu = QComboBox()
        self.gpu.addItem("Auto", "auto")
        for i, name in enumerate(list_gpus()):
            self.gpu.addItem(f"{i}: {name}", str(i))
        self.gpu.setCurrentIndex(max(0, self.gpu.findData(self.settings["gpu"])))
        s.addRow("GPU", self.gpu)
        self.language = QComboBox()
        self.language.addItems(LANGUAGES)
        self.language.setCurrentIndex(self.settings["language"])
        s.addRow("Console language", self.language)
        self.mangohud = QCheckBox("MangoHud overlay (FPS, frame time, temps)")
        self.mangohud.setChecked(self.settings["mangohud"])
        if not shutil.which("mangohud"):
            self.mangohud.setEnabled(False)
        s.addRow(self.mangohud)
        self.skip_intro = QCheckBox("Skip intro logos (experimental: the game's cp11_debug_skipSplashScreens)")
        self.skip_intro.setToolTip("A developer setting left in the game. If the game stops at a black screen at "
                                   "start-up, turn it off.")
        self.skip_intro.setChecked(self.settings["skip_intro"])
        s.addRow(self.skip_intro)
        self.convars = QLineEdit(self.settings["convars"])
        self.convars.setToolTip("KYTY_GAME_CONVARS: game engine settings, separated by ';'")
        s.addRow("Game convars", self.convars)
        self.extra = QLineEdit(self.settings["extra_args"])
        self.extra.setPlaceholderText("Extra emulator arguments, e.g. --keymap Cross=Space")
        s.addRow("Extra arguments", self.extra)
        root.addWidget(sys_box)

        # Buttons
        b = QHBoxLayout()
        self.launch_btn = QPushButton("▶  Launch")
        self.launch_btn.setDefault(True)
        self.launch_btn.setMinimumHeight(36)
        self.launch_btn.clicked.connect(self.launch)
        self.stop_btn = QPushButton("■  Stop")
        self.stop_btn.setMinimumHeight(36)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop)
        self.precompile_btn = QPushButton("⚙  Precompile shaders")
        self.precompile_btn.setMinimumHeight(36)
        self.precompile_btn.setToolTip("Compile every shader of the game ahead of time (about an hour; "
                                       "stop any time, it resumes). Run again after a Mesa update.")
        self.precompile_btn.clicked.connect(self.precompile)
        b.addWidget(self.launch_btn, 2)
        self.update_btn = QPushButton("⟳  Check for updates")
        self.update_btn.setMinimumHeight(36)
        self.update_btn.setToolTip("Look for a newer KytyPS5 on GitHub, show what changed, and update if you want "
                                   "(the old version is kept in _Old/ for a rollback)")
        self.update_btn.clicked.connect(self.check_updates)
        b.addWidget(self.precompile_btn, 1)
        b.addWidget(self.update_btn, 1)
        b.addWidget(self.stop_btn, 1)
        root.addLayout(b)

        self.status = QLabel("Ready")
        root.addWidget(self.status)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        self.log.setFont(QFont("monospace", 8))
        root.addWidget(self.log, 1)

        self.update_enabled()
        self.check_game()
        self.refresh_install()

    def installed_version(self):
        """KytyPS5's version in KYTY_DIR ('v20261023'), '' when it is not installed."""
        exe = KYTY_DIR / "kyty_emulator"
        if not exe.is_file():
            return ""
        try:
            first = subprocess.run([str(exe), "--help"], capture_output=True, text=True, timeout=30).stdout
        except (OSError, subprocess.SubprocessError):
            return "?"
        parts = [p.split("=", 1)[1].strip() for p in first.splitlines()[0].split(",") if "git =" in p] if first else []
        return parts[0] if parts else "?"

    def refresh_install(self):
        """Launch and precompile need KytyPS5; without it the update button installs it."""
        version = self.installed_version()
        busy = self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning
        self.launch_btn.setEnabled(bool(version) and not busy)
        self.precompile_btn.setEnabled(bool(version) and not busy)
        self.update_btn.setEnabled(not busy)
        if version:
            self.kyty_status.setText(f"KytyPS5 {version} (chenxiao07) in {KYTY_DIR}")
            self.kyty_status.setStyleSheet("color: gray;")
            self.update_btn.setText("⟳  Check for updates")
        else:
            self.kyty_status.setText(f"KytyPS5 is not installed yet: press ⬇ Install KytyPS5 (about 100 MB, from "
                                     f"chenxiao07's GitHub, into {KYTY_DIR}).")
            self.kyty_status.setStyleSheet("color: orange;")
            self.update_btn.setText("⬇  Install KytyPS5")
        return version

    def check_game(self):
        path = self.game.text().strip()
        info = game_info(path) if path else None
        if not path:
            text, color = "Choose the Demon's Souls folder (the one with eboot.bin) or a .zar archive.", "gray"
        elif not Path(path).exists():
            text, color = "This path does not exist.", "red"
        elif info is None:
            text, color = ("A .zar archive (its version is checked by the emulator)." if path.endswith(".zar")
                           else "No sce_sys/param.json here: is this the game's folder?"), "gray"
        elif info[0] not in TITLES:
            text, color = f"{info[0]} is not Demon's Souls (PPSA01340-PPSA01342): this launcher is for it only.", "red"
        elif info[1] not in VERSIONS:
            text, color = f"Demon's Souls {info[1]}: KytyPS5 runs 01.007.000 and 01.005.000 only.", "orange"
        else:
            text, color = f"Demon's Souls {info[0]}, version {info[1]}.", "green"
        self.game_status.setText(text)
        self.game_status.setStyleSheet(f"color: {color};")

    @staticmethod
    def combo(items, current, editable=False):
        c = QComboBox()
        c.addItems(items)
        c.setEditable(editable)
        if current not in items:
            c.addItem(current)
        c.setCurrentText(current)
        return c

    def pick_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Game folder", self.game.text() or str(Path.home()))
        if path:
            self.game.setText(path)

    def pick_zar(self):
        path, _ = QFileDialog.getOpenFileName(self, "Game archive", self.game.text() or str(Path.home()),
                                              "ZArchive (*.zar)")
        if path:
            self.game.setText(path)

    def update_enabled(self):
        self.fsr_sharpness.setEnabled(self.fsr_upscaler.isChecked())
        # FSR 3 frame generation owns the swapchain: not under gamescope. FSR 3 upscaling already makes the game's 4K
        # picture, which is shrunk to the window: gamescope scaling it up again would only soften it.
        fsr3 = self.frame_gen.isChecked() or self.fsr_upscaler.isChecked()
        if fsr3:
            self.upscaler.setCurrentText("Off")
        self.upscaler.setEnabled(not fsr3 and bool(shutil.which("gamescope")))
        self.upscaler.setToolTip("Off while FSR 3 is on: FSR 3 already upscales (and frame generation cannot run "
                                 "under gamescope)" if fsr3 else "")
        on = UPSCALERS.get(self.upscaler.currentText()) is not None
        self.output_res.setEnabled(on)
        self.sharpness.setEnabled(on and UPSCALERS[self.upscaler.currentText()] in ("fsr", "nis"))

    def collect(self):
        return {
            "game": self.game.text().strip(), "resolution": self.resolution.currentText().strip(),
            "render_height": self.render_height.currentData(),
            "fullscreen": self.fullscreen.isChecked(), "hdr": self.hdr.isChecked(),
            "present_mode": self.present.currentText(), "fps": self.fps.currentData(),
            "gpu": self.gpu.currentData(), "language": self.language.currentIndex(),
            "mangohud": self.mangohud.isChecked(), "upscaler": self.upscaler.currentText(),
            "output_resolution": self.output_res.currentText().strip(),
            "sharpness": self.sharpness.value(),
            "fsr_upscaler": self.fsr_upscaler.isChecked(), "fsr_sharpness": round(self.fsr_sharpness.value(), 2),
            "frame_gen": self.frame_gen.isChecked(), "low_latency": self.low_latency.isChecked(), "convars": self.convars.text().strip(), "skip_intro": self.skip_intro.isChecked(),
            "extra_args": self.extra.text().strip(),
        }

    def save_settings(self, cfg=None):
        KYTY_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps({**(cfg or self.collect()),
                                             "menu_asked": self.settings.get("menu_asked", False)}, indent=2))

    @staticmethod
    def parse_res(text):
        w, h = text.lower().replace(" ", "").split("x")
        return int(w), int(h)

    def launch(self):
        cfg = self.collect()
        if not cfg["game"] or not Path(cfg["game"]).exists():
            QMessageBox.warning(self, "Demon's Souls launcher", "Choose the game folder or .zar archive first.")
            return
        try:
            w, h = self.parse_res(cfg["resolution"])
            ow, oh = self.parse_res(cfg["output_resolution"])
        except ValueError:
            QMessageBox.warning(self, "Demon's Souls launcher", "Resolutions must look like 1920x1080.")
            return
        try:
            extra = shlex.split(cfg["extra_args"])
        except ValueError as e:
            QMessageBox.warning(self, "Demon's Souls launcher", f"Extra arguments: {e}")
            return
        self.save_settings(cfg)

        env = QProcessEnvironment.systemEnvironment()
        env.insert("KYTY_GAME", cfg["game"])
        env.insert("KYTY_WIDTH", str(w))
        # (With FSR 3 upscaling a height is always given: unset, its path renders the PS5 Pro's 2688x1512.)
        if cfg["render_height"] != 1440 or cfg["fsr_upscaler"]:
            env.insert("KYTY_RENDER_HEIGHT", str(cfg["render_height"]))
        if cfg["fsr_upscaler"]:
            env.insert("KYTY_UPSCALER", "fsr")
            env.insert("KYTY_FSR_SHARPNESS", f"{cfg['fsr_sharpness']:.2f}")
        if cfg["frame_gen"]:
            env.insert("KYTY_FRAMEGEN", "1")
            env.insert("KYTY_FRAMEGEN_BACKEND", "fsr")
        if cfg["low_latency"]:
            env.insert("KYTY_LOW_LATENCY", "1")
        env.insert("KYTY_HEIGHT", str(h))
        env.insert("KYTY_LANGUAGE", str(cfg["language"]))
        env.insert("KYTY_VBLANK", str(cfg["fps"]))
        env.insert("PRESENT_MODE", cfg["present_mode"])
        # (Unset, the emulator gives the game its own defaults; set, these replace them, so the field keeps them.)
        convars = [c for c in cfg["convars"].split(";") if c.strip()]
        if cfg["skip_intro"] and not any(c.startswith("cp11_debug_skipSplashScreens") for c in convars):
            convars.append("cp11_debug_skipSplashScreens=true")
        if convars:
            env.insert("KYTY_GAME_CONVARS", ";".join(convars))
        if cfg["gpu"] != "auto":
            env.insert("KYTY_GPU", cfg["gpu"])

        emu_args = list(extra)
        if cfg["hdr"]:
            emu_args.append("--hdr")

        filt = UPSCALERS.get(cfg["upscaler"])
        script = str(KYTY_DIR / "run_ds.sh")
        if filt:
            # gamescope owns the output (fullscreen, HDR, overlay); the emulator draws a plain window.
            env.insert("MANGO", "0")
            program = "gamescope"
            args = ["-w", str(w), "-h", str(h), "-W", str(ow), "-H", str(oh),
                    "-r", str(max(cfg["fps"], 60))]
            args += ["-S", "integer"] if filt == "integer" else ["-F", filt, "--sharpness", str(cfg["sharpness"])]
            if cfg["fullscreen"]:
                args.append("-f")
            if cfg["hdr"]:
                args.append("--hdr-enabled")
            if cfg["mangohud"]:
                args.append("--mangoapp")
            args += ["--", script] + emu_args
        else:
            env.insert("MANGO", "1" if cfg["mangohud"] else "0")
            program = script
            args = emu_args + (["--fullscreen"] if cfg["fullscreen"] else [])

        self.run_process(program, args, env, LOG_FILE)

    def precompile(self):
        game = self.game.text().strip()
        if not game or not Path(game).exists():
            QMessageBox.warning(self, "Demon's Souls launcher", "Choose the game folder or .zar archive first.")
            return
        self.save_settings()
        env = QProcessEnvironment.systemEnvironment()
        gpu = self.gpu.currentData()
        if gpu != "auto":
            # (The pipelines are compiled for one graphics card: the one the game runs on.)
            env.insert("KYTY_GPU", gpu)
        self.run_process(str(KYTY_DIR / "precompile-linux.sh"), ["--game", game], env, PRECOMPILE_LOG)

    def updater(self, mode):
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        return env, [str(HERE / "des-update.py"), mode, "--dir", str(KYTY_DIR)]

    def check_updates(self):
        if not self.installed_version():
            if QMessageBox.question(self, APP_NAME, f"Download KytyPS5, the emulator (about 100 MB), from chenxiao07's "
                                    f"GitHub releases into\n{KYTY_DIR}?\n\nIt is checked against GitHub's checksum "
                                    f"before it is installed.") == QMessageBox.StandardButton.Yes:
                env, args = self.updater("--yes")
                self.run_process(python_exe(), args, env, UPDATE_LOG, on_finished=self.installed)
            return
        env, args = self.updater("--check")
        self.run_process(python_exe(), args, env, UPDATE_LOG, on_finished=self.update_checked)

    def installed(self, code):
        if code == 0 and self.installed_version():
            self.status.setText("KytyPS5 is installed. Choose the game, then press ⚙ Precompile shaders once.")
            return True
        return False

    def update_checked(self, code):
        if code == 10:
            self.status.setText("An update is available (what changed is in the log below)")
            if QMessageBox.question(self, "KytyPS5", "A newer KytyPS5 is available (what changed is in the log). "
                                    "Update now?\n\nThe current version is kept for a rollback "
                                    "(des-update.py --rollback).") == QMessageBox.StandardButton.Yes:
                env, args = self.updater("--yes")
                self.run_process(python_exe(), args, env, UPDATE_LOG)
            return True
        return False

    def run_process(self, program, args, env, log_file, on_finished=None):
        self.on_finished = on_finished
        log_file.parent.mkdir(parents=True, exist_ok=True)
        self.log_handle = open(log_file, "w", encoding="utf-8", errors="replace")
        cmdline = " ".join(shlex.quote(a) for a in [program] + args)
        self.log.clear()
        self.append(f"$ {cmdline}\n")

        self.proc = QProcess(self)
        self.proc.setProcessEnvironment(env)
        self.proc.setWorkingDirectory(str(KYTY_DIR))
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self.read_output)
        self.proc.finished.connect(self.finished)
        self.proc.errorOccurred.connect(self.failed)
        self.proc.start(program, args)
        self.launch_btn.setEnabled(False)
        self.precompile_btn.setEnabled(False)
        self.update_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status.setText(f"Running… (log: {log_file})")

    def append(self, text):
        if self.log_handle:
            self.log_handle.write(text)
            self.log_handle.flush()
        self.log.moveCursor(QTextCursor.MoveOperation.End)
        self.log.insertPlainText(text)
        self.log.moveCursor(QTextCursor.MoveOperation.End)

    def read_output(self):
        self.append(bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace"))

    def stop(self):
        if self.proc and self.proc.state() != QProcess.ProcessState.NotRunning:
            self.proc.terminate()
            if not self.proc.waitForFinished(15000):
                self.proc.kill()

    def failed(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.append(f"\nFailed to start: {self.proc.errorString()}\n")
            self.finished(-1, None)

    def finished(self, code, _status):
        if self.log_handle:
            self.log_handle.close()
            self.log_handle = None
        self.stop_btn.setEnabled(False)
        self.refresh_install()
        callback, self.on_finished = getattr(self, "on_finished", None), None
        if callback and callback(code):
            self.refresh_install()
            return
        self.status.setText(f"Exited with code {code}" + ("" if code == 0 else " — see the log below"))

    def offer_menu_entry(self):
        """Run from an AppImage: once, the offer of an application menu entry pointing at it."""
        appimage = os.environ.get("APPIMAGE")
        apps = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "applications"
        entry = apps / "des-launcher.desktop"
        if not appimage or self.settings.get("menu_asked") or entry.exists():
            return
        self.settings["menu_asked"] = True
        self.save_settings()
        if QMessageBox.question(self, APP_NAME, f"Add {APP_NAME} to your application menu?\n\n(It starts this "
                                f"AppImage: {appimage})") != QMessageBox.StandardButton.Yes:
            return
        icon = KYTY_DIR / "des-launcher.png"
        if (HERE / "des-launcher.png").exists():
            shutil.copy2(HERE / "des-launcher.png", icon)
        apps.mkdir(parents=True, exist_ok=True)
        entry.write_text(f"[Desktop Entry]\nType=Application\nName={APP_NAME}\n"
                         f"Comment=Unofficial Linux launcher for the KytyPS5 emulator\nExec=\"{appimage}\"\n"
                         f"Icon={icon if icon.exists() else 'applications-games'}\nTerminal=false\n"
                         f"Categories=Game;Emulator;\n")
        self.status.setText(f"Added {APP_NAME} to the application menu.")

    def closeEvent(self, event):
        self.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setDesktopFileName("des-launcher")
    w = Launcher()
    w.show()
    w.offer_menu_entry()
    sys.exit(app.exec())
