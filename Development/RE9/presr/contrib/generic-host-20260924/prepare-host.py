#!/usr/bin/env python3
"""Generic OptiScaler host integration: apply lmxxf HIP backend to any DLSS game.

Usage:
  python3 Development/OptiScaler/prepare-host.py

Clones TheAutomatic/dlss-5-amd-project at the pinned release/1.9.0 commit,
applies the host-side patches in this directory, and copies QueryStateBook.h.
Then build-runtime.sh compiles LmxxfNrRuntime.dll with mingw.
"""
import subprocess, shutil
from pathlib import Path

root = Path(__file__).resolve().parents[3]
here = Path(__file__).resolve().parent

# TheAutomatic upstream pin (same as RE9/presr)
UPSTREAM_REPO = "https://github.com/TheAutomatic/dlss-5-amd-project"
UPSTREAM_BRANCH = "release/1.9.0"
UPSTREAM_COMMIT = "8f71f73bfc836a37936e7cee6701750ad4e8bfec"

# Host checkout location (override with HOST_DIR env)
import os
host = Path(os.environ.get("HOST_DIR", "/tmp/optiscaler-generic-host"))

PREFIX = "OptiScaler-DLSSNR-PreSR-Multipass-main/OptiScaler/"


def run(cmd, cwd=None, check=True):
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)


def ensure_upstream():
    if not host.exists():
        print(f"Cloning {UPSTREAM_REPO} branch {UPSTREAM_BRANCH}...")
        run(["git", "clone", "--branch", UPSTREAM_BRANCH, UPSTREAM_REPO, str(host)])
    head = run(["git", "rev-parse", "HEAD"], cwd=host).stdout.strip()
    if head != UPSTREAM_COMMIT:
        print(f"Checking out {UPSTREAM_COMMIT}...")
        run(["git", "checkout", UPSTREAM_COMMIT], cwd=host)


def apply_patches():
    patches = sorted(here.glob("patch-*.patch"))
    for p in patches:
        print(f"Applying {p.name}...")
        run(["git", "apply", str(p)], cwd=host, check=True)
    # Copy new header
    shutil.copy2(here / "QueryStateBook.h", host / PREFIX / "dlssnr/submission/QueryStateBook.h")
    print("Copied QueryStateBook.h")


if __name__ == "__main__":
    ensure_upstream()
    apply_patches()
    print(f"Generic OptiScaler host prepared at {host}")
