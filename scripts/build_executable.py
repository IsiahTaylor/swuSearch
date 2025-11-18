"""Build a standalone executable using PyInstaller and drop it in ./builds.

Usage:
    python scripts/build_executable.py 0.2

Requirements:
    - PyInstaller installed in the current Python environment.
    - Run from the repo root (where pyproject.toml lives).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an executable with PyInstaller.")
    parser.add_argument(
        "version",
        help="Two-part version number (e.g., 0.1, 1.4)",
    )
    args = parser.parse_args()

    if not re.fullmatch(r"\d+\.\d+", args.version):
        print("Version must be in two-part format, e.g., 0.1 or 1.4", file=sys.stderr)
        return 1

    repo_root = Path(__file__).resolve().parent.parent
    builds_dir = repo_root / "builds"
    builds_dir.mkdir(exist_ok=True)

    name = f"image-search-app-{args.version}"
    exe_path = builds_dir / name

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        name,
        "--paths",
        str(repo_root / "src"),
        str(repo_root / "src" / "image_search_app" / "main.py"),
    ]

    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=repo_root)
    if result.returncode != 0:
        print("PyInstaller failed. Ensure PyInstaller is installed (pip install pyinstaller).", file=sys.stderr)
        return result.returncode

    # Move the built binary into ./builds
    dist_dir = repo_root / "dist"
    built = dist_dir / name
    if built.exists():
        target = exe_path
    else:
        # On Windows PyInstaller appends .exe
        built = dist_dir / f"{name}.exe"
        target = builds_dir / f"{name}.exe"

    if not built.exists():
        print(f"Expected built binary not found at {built}", file=sys.stderr)
        return 1

    target.write_bytes(built.read_bytes())
    print(f"Executable written to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
