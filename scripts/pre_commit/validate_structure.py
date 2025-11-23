#!/usr/bin/env python3
"""Guarantee the repository keeps the requested production folder layout."""

import sys
from pathlib import Path

REQUIRED_DIRS = [
    ("src", "application source files"),
    ("config", "runtime configuration"),
    ("docs", "project documentation"),
    ("tests", "automated tests"),
    ("docker", "Docker artifacts"),
]
BUILD_DIRS = ["build", "dist"]


def check_layout() -> list[str]:
    missing = []
    for directory, description in REQUIRED_DIRS:
        path = Path(directory)
        if not path.is_dir():
            missing.append(f"{directory} ({description})")
    if not any(Path(candidate).is_dir() for candidate in BUILD_DIRS):
        missing.append("build/ or dist/ (build artifacts)")
    return missing


def main() -> int:
    missing = check_layout()
    if missing:
        print(
            "Repository layout check failed. The following directories are missing or misnamed:"
        )
        for entry in missing:
            print(f"  - {entry}")
        print("Create the folders or adjust the layout before committing.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
