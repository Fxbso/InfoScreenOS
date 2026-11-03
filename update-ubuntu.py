#!/usr/bin/env python3
"""Unattended KUFGEM InfoScreen application updater (no GitHub Actions)."""
import argparse
import datetime as dt
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path("/opt/kufgem-infoscreen")
BACKUP = Path("/opt/kufgem-infoscreen.previous")
STATE = Path("/var/lib/kufgem-infoscreen")
REVISION = STATE / "installed-commit"
STATUS = STATE / "update-status.json"
API = "https://api.github.com/repos/Fxbso/InfoScreenOS/commits/main"
ARCHIVE = "https://api.github.com/repos/Fxbso/InfoScreenOS/tarball/"
FILES = (
    "backend/app.py", "backend/set_password.py", "display/renderer.py",
    "dashboard/index.html", "dashboard/app.js",
)
MAX_ARCHIVE = 16 * 1024 * 1024
MAX_ITEM = 8 * 1024 * 1024
MAX_TOTAL = 36 * 1024 * 1024


def log(message):
    print(message, flush=True)


def run(*argv, **kwargs):
    return subprocess.run(argv, check=True, **kwargs)


def get(url, max_size=MAX_ARCHIVE):
    req = urllib.request.Request(
        url, headers={"User-Agent": "KUFGEM-InfoScreen-Updater/1", "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read(max_size + 1)
        if len(data) > max_size:
            raise ValueError("Download exceeds size limit")
        return data


def remote_revision():
    item = json.loads(get(API, 1024 * 1024))
    sha = item["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Invalid GitHub commit SHA")
    return sha


def write_status(result, **values):
    STATE.mkdir(mode=0o755, parents=True, exist_ok=True)
    data = {"result": result, "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(), **values}
    fd, name = tempfile.mkstemp(prefix=".update-status-", dir=STATE)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(data, out)
        os.chmod(name, 0o644)
        os.replace(name, STATUS)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def unpack_selected(blob, stage):
    """Copy only declared regular source files; reject links and traversal."""
    wanted = set(FILES)
    seen = set()
    total = 0
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
        for member in archive:
            parts = Path(member.name).parts
            if len(parts) < 2:
                continue
            rel = "/".join(parts[1:])
            if rel not in wanted:
                continue
            if rel in seen or not member.isfile() or member.size > MAX_ITEM:
                raise ValueError("Unsafe archive member: " + rel)
            total += member.size
            if total > MAX_TOTAL:
                raise ValueError("Unpacked archive too large")
            seen.add(rel)
            destination = stage / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise ValueError("Cannot read archive member")
            with destination.open("wb") as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)
    if seen != wanted:
        raise ValueError("Missing app files: " + ", ".join(sorted(wanted - seen)))


def preflight(stage):
    # No network or elevated privileges required during preflight.
    run("/usr/bin/python3", "-m", "compileall", "-q", str(stage / "backend"), str(stage / "display"))
    # Validate JavaScript syntax if node is installed; otherwise skip.
    node = shutil.which("node")
    if node:
        run(node, "--check", str(stage / "dashboard" / "app.js"))
    for relative in FILES:
        if (stage / relative).stat().st_size < 20:
            raise ValueError("Invalid empty source: " + relative)


def healthy():
    try:
        result = get("http://127.0.0.1:8080/api/health", 1024)
        return json.loads(result).get("ok") is True
    except (OSError, ValueError, urllib.error.URLError):
        return False


def restart_and_check():
    run("systemctl", "restart", "kufgem-infoscreen-api.service")
    for _ in range(12):
        if healthy():
            return
        time.sleep(1)
    raise RuntimeError("Local API did not become healthy")


def update(force=False, check_only=False):
    sha = remote_revision()
    installed = REVISION.read_text().strip() if REVISION.is_file() else ""
    if installed == sha and not force:
        write_status("current", installed=installed, available=sha)
        log("Already current: " + sha[:12])
        return
    if check_only:
        write_status("available", installed=installed, available=sha)
        log("Available: " + sha)
        return
    log("Updating from " + (installed[:12] or "unknown") + " to " + sha[:12])
    archive = get(ARCHIVE + sha)
    with tempfile.TemporaryDirectory(prefix=".infoscreen-update-", dir="/opt") as folder:
        stage = Path(folder) / "app"
        stage.mkdir()
        unpack_selected(archive, stage)
        preflight(stage)
        # Preserve no runtime data in /opt; layout, background and password
        # are stored independently in /var/lib and /etc.
        if not ROOT.is_dir():
            raise RuntimeError("InfoScreen app directory not found")
        # Never destroy a previous rollback copy until a new staged build
        # is confirmed valid and ready.
        if BACKUP.exists():
            shutil.rmtree(BACKUP)
        ROOT.rename(BACKUP)
        try:
            stage.rename(ROOT)
            restart_and_check()
            # Refresh native on-screen renderer only if a graphical session is active.
            if subprocess.run(["systemctl", "is-active", "--quiet", "lightdm.service"]).returncode == 0:
                run("systemctl", "restart", "lightdm.service")
            REVISION.write_text(sha + "\n", encoding="ascii")
            REVISION.chmod(0o644)
            write_status("updated", installed=sha, previous=installed)
            log("Update successful: " + sha[:12])
        except Exception:
            log("Update failed; rolling back")
            if ROOT.exists():
                shutil.rmtree(ROOT)
            BACKUP.rename(ROOT)
            try:
                restart_and_check()
                if subprocess.run(["systemctl", "is-active", "--quiet", "lightdm.service"]).returncode == 0:
                    run("systemctl", "restart", "lightdm.service")
            finally:
                write_status("rolled-back", installed=installed, available=sha)
            raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Only check GitHub")
    parser.add_argument("--force", action="store_true", help="Reinstall even if revision is unchanged")
    args = parser.parse_args()
    if os.geteuid() != 0:
        sys.exit("Run with sudo")
    try:
        update(force=args.force, check_only=args.check)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError, tarfile.TarError, KeyError) as exc:
        log("Updater error: " + str(exc))
        write_status("error", error=str(exc)[:200])
        sys.exit(1)


if __name__ == "__main__":
    main()
