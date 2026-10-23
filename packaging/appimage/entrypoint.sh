#! /bin/bash
# The launcher, run by the bundled Python. Its own files are in the AppImage ($APPDIR, read-only); KytyPS5, the
# settings, saves and shader cache go to ~/Games/KytyPS5-DeS ($DES_HOME to change it).
{{ python-executable }} "${APPDIR}/des-launcher.py" "$@"
