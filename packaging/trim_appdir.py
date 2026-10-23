#!/usr/bin/env python3
"""Trims an AppDir made by python-appimage to what the launcher uses: Qt's Core, Gui, Widgets and DBus with the
platform plugins for X11 and Wayland (the libraries they link to, as ldd resolves them, stay), and Python without
its test suite, Tk and pip. About 300 MB -> 120 MB unpacked.

  trim_appdir.py <AppDir>
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

appdir = Path(sys.argv[1]).resolve()
site = next(appdir.glob("opt/python3*/lib/python3*/site-packages"))
pyqt = site / "PyQt6"
qt = pyqt / "Qt6"
qtlib = qt / "lib"

# PyQt6's modules: the ones the launcher imports (and sip, which they need).
KEEP_MODULES = {"QtCore", "QtGui", "QtWidgets", "QtDBus"}
for module in pyqt.glob("Qt*.abi3.so"):
    if module.name.split(".")[0] not in KEEP_MODULES:
        module.unlink()
for stub in pyqt.glob("Qt*.pyi"):
    if stub.stem not in KEEP_MODULES:
        stub.unlink()
for folder in ("uic", "lupdate"):
    shutil.rmtree(pyqt / folder, ignore_errors=True)

# Qt's plugins: displays (X11, Wayland), image formats, icon engines, input methods, desktop themes.
KEEP_PLUGINS = {"platforms", "xcbglintegrations", "wayland-decoration-client", "wayland-graphics-integration-client",
                "wayland-shell-integration", "imageformats", "iconengines", "platforminputcontexts", "platformthemes",
                "generic"}
for folder in (qt / "plugins").iterdir():
    if folder.name not in KEEP_PLUGINS:
        shutil.rmtree(folder)
for plugin in (qt / "plugins" / "platforms").iterdir():
    if not re.match(r"libq(xcb|wayland|offscreen|minimal)", plugin.name):
        plugin.unlink()
for folder in ("qml", "qsci", "translations"):
    shutil.rmtree(qt / folder, ignore_errors=True)

# Qt's libraries: those the kept modules and plugins link to, transitively.
env = dict(os.environ, LD_LIBRARY_PATH=str(qtlib))
needed, queue = set(), [m for m in pyqt.glob("*.so")] + list((qt / "plugins").rglob("*.so"))
while queue:
    out = subprocess.run(["ldd", str(queue.pop())], capture_output=True, text=True, env=env).stdout
    for line in out.splitlines():
        match = re.search(r"=> (\S+)", line)
        if match and Path(match.group(1)).parent == qtlib and match.group(1) not in needed:
            needed.add(match.group(1))
            queue.append(Path(match.group(1)))
removed = 0
for lib in qtlib.iterdir():
    if lib.is_file() and str(lib) not in needed:
        removed += lib.stat().st_size
        lib.unlink()
print(f"Qt: kept {len(needed)} libraries, removed {removed / 2**20:.0f} MiB")

# Python: no test suite, Tk, IDLE or pip at run time.
stdlib = site.parent
for folder in ("test", "idlelib", "tkinter", "turtledemo", "ensurepip", "lib2to3", "pydoc_data"):
    shutil.rmtree(stdlib / folder, ignore_errors=True)
for folder in site.iterdir():
    if folder.name.startswith(("pip", "setuptools", "wheel")):
        shutil.rmtree(folder, ignore_errors=True) if folder.is_dir() else folder.unlink()
for cache in list(appdir.rglob("__pycache__")):
    shutil.rmtree(cache, ignore_errors=True)
