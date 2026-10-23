#!/usr/bin/env python3
"""Install or update the KytyPS5 emulator from its official GitHub releases (chenxiao07/KytyPS5).

  ./des-update.py              check, show what changed, ask, then install or update
  ./des-update.py --check      only check (exit code 10 when an update is there)
  ./des-update.py --yes        install or update without asking (install.sh, the launcher's button)
  ./des-update.py --rollback   put the previous version back (from _Old/)

What it replaces: the release package's files (the emulator, the precompile tool and script, its hints, README,
licenses). run_ds.sh is upstream's with one line changed (patch_run_ds) so that the launcher can set the window size
and the console language. Never touched: saves, the launcher and its settings, the shader cache. The replaced files go
to _Old/<version>/ first; a failed step puts them back. In a git repository the update is committed too.
"""
import re
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = "chenxiao07/KytyPS5"
OLD = HERE / "_Old"
EXECUTABLE = {"kyty_emulator", "kyty_shader_precompile"}
KEEP_BACKUPS = 2


def say(text=""):
    print(text, flush=True)


def fail(text):
    say(f"error: {text}")
    sys.exit(1)


def api(path):
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/{path}",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "kyty-updater"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def installed_version():
    """The emulator's own version line: 'Release, ..., git = v20261020b, date = ...'."""
    try:
        out = subprocess.run([str(HERE / "kyty_emulator"), "--help"], capture_output=True, text=True,
                             timeout=30).stdout
    except OSError:
        return None
    for part in out.splitlines()[0].split(",") if out else []:
        if part.strip().startswith("git ="):
            return part.split("=", 1)[1].strip()
    return None


def linux_releases():
    """Published releases with a Linux package, newest first: (tag, asset, release)."""
    found = []
    for rel in api("releases?per_page=30"):
        if rel.get("draft") or rel.get("prerelease"):
            continue
        for asset in rel.get("assets", []):
            if asset["name"].startswith("KytyPS5-linux-") and asset["name"].endswith(".zip"):
                found.append((rel["tag_name"], asset, rel))
                break
    found.sort(key=lambda f: f[2]["published_at"], reverse=True)
    return found


def busy():
    """Why updating now would break something running, or None."""
    for pattern, what in (("-x kyty_emulator", "the game is running"),
                          ("-f precompile-as-emulator/kyty_emulator", "a shader precompile is running"),
                          ("-f precompile-linux.sh", "a shader precompile is running")):
        if subprocess.run(["pgrep"] + pattern.split(), capture_output=True).returncode == 0:
            return what
    return None


def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True, check=check)


# run_ds.sh gives the emulator a fixed 1920x1080 window and English; the launcher sets them (KYTY_WIDTH, KYTY_HEIGHT,
# KYTY_LANGUAGE), the same defaults when unset.
FIXED_LINE = re.compile(r"--screen-width 1920 --screen-height 1080 --console-language 1\b")
PATCHED_LINE = '--screen-width "${KYTY_WIDTH:-1920}" --screen-height "${KYTY_HEIGHT:-1080}" ' \
               '--console-language "${KYTY_LANGUAGE:-1}"'


def patch_run_ds(text):
    patched, count = FIXED_LINE.subn(PATCHED_LINE, text)
    if count != 1 and "KYTY_WIDTH" not in text:
        say("run_ds.sh: its window size line changed upstream; the launcher's window size and language settings are "
            "not applied (the game still runs, at 1920x1080 in English)")
        return text
    return patched


def download(asset, folder):
    path = folder / asset["name"]
    say(f"downloading {asset['name']} ({asset['size'] / 2**20:.0f} MB)…")
    sha = hashlib.sha256()
    with urllib.request.urlopen(asset["browser_download_url"], timeout=60) as r, open(path, "wb") as out:
        while chunk := r.read(1 << 20):
            sha.update(chunk)
            out.write(chunk)
    digest = asset.get("digest") or ""
    if digest.startswith("sha256:"):
        if sha.hexdigest() != digest[7:]:
            fail("the download does not match GitHub's checksum (broken or tampered): nothing changed")
        say("checksum: matches GitHub's sha256")
    else:
        say("checksum: GitHub lists none for this file (not verified)")
    return path


def extract(zip_path, folder):
    """The package's files (inside its one top folder), refusing paths that leave the folder."""
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            target = (folder / info.filename).resolve()
            if not str(target).startswith(str(folder.resolve()) + os.sep):
                fail(f"unsafe path in the package: {info.filename}")
        z.extractall(folder)
    tops = [p for p in folder.iterdir() if p.is_dir()]
    root = tops[0] if len(tops) == 1 else folder
    for name in EXECUTABLE:
        if not (root / name).is_file():
            fail(f"the package has no {name}: nothing changed")
    return root


def package_files(root):
    return sorted(p.relative_to(root) for p in root.rglob("*") if p.is_file())


def prune_backups():
    backups = sorted((p for p in OLD.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime) if OLD.exists() else []
    for old in backups[:-KEEP_BACKUPS]:
        shutil.rmtree(old, ignore_errors=True)


def update(tag, asset, current):
    work = Path(tempfile.mkdtemp(prefix="kyty-update-"))
    backup = OLD / (current or "unknown")
    moved = []  # (installed path, backup path or None for a file that was new)
    try:
        root = extract(download(asset, work), work / "package")
        for name in EXECUTABLE | {p.name for p in root.glob("*.sh")}:
            if (root / name).exists():
                (root / name).chmod(0o755)
        version_line = subprocess.run([str(root / "kyty_emulator"), "--help"], capture_output=True, text=True,
                                      timeout=30).stdout.splitlines()[:1]
        if not version_line:
            fail("the new emulator does not start (--help printed nothing): nothing changed")
        say(f"new emulator: {version_line[0]}")

        files = package_files(root)
        if (root / "run_ds.sh").exists():
            run_ds = root / "run_ds.sh"
            run_ds.write_text(patch_run_ds(run_ds.read_text()))
        if current:
            backup.mkdir(parents=True, exist_ok=True)
        for rel in files:
            dest = HERE / rel
            if dest.exists() and current:
                keep = backup / rel
                keep.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(dest, keep)
                moved.append((dest, keep))
            else:
                moved.append((dest, None))
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / rel, dest)
        if current:
            (backup / "VERSION").write_text(f"{current}\n")
            say(f"installed {tag}: {len(files)} files; the old ones are in {backup.relative_to(HERE)}/")
        else:
            say(f"installed {tag}: {len(files)} files")
    except BaseException:
        for dest, keep in reversed(moved):
            dest.unlink(missing_ok=True)
            if keep:
                shutil.move(keep, dest)
        if moved:
            say("restored the previous version")
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
    prune_backups()
    commit(f"Update KytyPS5 to {tag}", tag)


def commit(message, tag):
    """In a git repository (a setup kept in git), the update as a commit, pushed when there is a remote."""
    if not (HERE / ".git").exists():
        return
    git("add", "-A")
    if git("diff", "--cached", "--quiet", check=False).returncode == 0:
        return
    done = git("commit", "-q", "-m", message, check=False)
    if done.returncode != 0:
        say(f"git: not committed:\n{done.stdout}{done.stderr}")
        return
    say(f"git: committed \"{message}\"")
    if git("remote", check=False).stdout.strip():
        pushed = git("push", "-q", check=False)
        say("git: pushed to GitHub" if pushed.returncode == 0 else f"git: push failed: {pushed.stderr.strip()}")


def precompile_status():
    """What the shader cache holds against the installed emulator (kyty_shader_precompile --status)."""
    try:
        settings = json.loads((HERE / "des-launcher.json").read_text())
    except (OSError, ValueError):
        settings = {}
    game = settings.get("game", "")
    seeds = sorted(HERE.glob("seeds-*.seeds"), key=lambda p: p.stat().st_mtime)
    if not game or not seeds:
        say("\n→ run the shader precompile once (the launcher's ⚙ Precompile shaders button): fewer stutters")
        return
    env = dict(os.environ)
    if settings.get("gpu", "auto") != "auto":
        env["KYTY_GPU"] = settings["gpu"]
    say("\nchecking the shader cache against the installed emulator…")
    out = subprocess.run([str(HERE / "kyty_shader_precompile"), "--game", game, "--seeds", str(seeds[-1]), "--status"],
                         cwd=HERE, env=env, capture_output=True, text=True).stdout
    lines = [l for l in out.splitlines() if l.startswith(("inputs", "static cache"))]
    for line in lines:
        say(f"  {line}")
    if any("stale" in l or "outdated" in l for l in lines):
        say("→ run the shader precompile again (the launcher's ⚙ Precompile shaders button)")


def rollback():
    backups = sorted((p for p in OLD.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime) if OLD.exists() else []
    if not backups:
        fail("no earlier version in _Old/")
    backup = backups[-1]
    version = (backup / "VERSION").read_text().strip() if (backup / "VERSION").exists() else backup.name
    current = installed_version()
    files = [p.relative_to(backup) for p in backup.rglob("*") if p.is_file() and p.name != "VERSION"]
    for rel in files:
        shutil.copy2(backup / rel, HERE / rel)
        if rel.name in EXECUTABLE or rel.suffix == ".sh":
            (HERE / rel).chmod(0o755)
    shutil.rmtree(backup)
    say(f"rolled back from {current} to {version} ({len(files)} files)")
    commit(f"Roll KytyPS5 back to {version}", version)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--yes", action="store_true")
    mode.add_argument("--rollback", action="store_true")
    opt = ap.parse_args()

    if not opt.check:
        why = busy()
        if why:
            fail(f"{why}: close it first")
    if opt.rollback:
        rollback()
        precompile_status()
        return

    current = installed_version()
    say(f"installed: {current or 'none (a new install)'}")
    try:
        releases = linux_releases()
    except OSError as e:
        fail(f"cannot reach GitHub: {e}")
    if not releases:
        fail("no Linux release found")
    tag, asset, _ = releases[0]
    say(f"latest:    {tag}")
    if current == tag:
        say("up to date")
        return
    newer = []
    for rel_tag, _, rel in releases:
        if rel_tag == current:
            break
        newer.append((rel_tag, rel))
    if not current:
        newer = newer[:1]  # (a new install: what the latest release brings)
    say(f"\n{len(newer)} newer release(s):")
    for rel_tag, rel in newer:
        notes = (rel.get("body") or "").strip().splitlines()
        say(f"\n=== {rel_tag} ({rel['published_at'][:10]})")
        for line in notes[:25]:
            say(f"  {line}")
        if len(notes) > 25:
            say(f"  … ({len(notes) - 25} more lines: https://github.com/{REPO}/releases/tag/{rel_tag})")
    if opt.check:
        sys.exit(10)
    if not opt.yes:
        question = f"Update {current} → {tag}?" if current else f"Install KytyPS5 {tag} into {HERE}?"
        if input(f"\n{question} [y/N] ").strip().lower() not in ("y", "yes"):
            say("nothing changed")
            return
    update(tag, asset, current)
    precompile_status()


if __name__ == "__main__":
    main()
