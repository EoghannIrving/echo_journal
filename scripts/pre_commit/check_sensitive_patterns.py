#!/usr/bin/env python3
"""Guard against committing sensitive keywords or credentials."""

import re
import subprocess
import sys
from pathlib import Path

EXCLUDED_PREFIXES = ("docs/", "config/", "scripts/pre_commit/")
EXCLUDED_FILES = {
    ".gitignore",
    ".pre-commit-config.yaml",
    "SETUP.md",
    "docker-compose.sample.yml",
    "config/config.sample.json",
    ".secrets.baseline",
}

PATTERN_CONFIG = [
    (
        re.compile(r"(?i)\b(api|secret|token|password|passwd|key|credential)s?\b"),
        "credential keyword",
    ),
    (
        re.compile(r"(?i)\b(private_KEY|BEGIN (RSA|DSA|EC) PRIVATE KEY)\b"),
        "private key header",
    ),
    (re.compile(r"(?i)\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (
        re.compile(r"(?i)(?:\b|\W)(?:\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4})(?:\b|\W)"),
        "long numeric token",
    ),
]


def staged_files() -> list[Path]:
    """Return the list of staged files to inspect."""

    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        check=True,
    )
    files = []
    for line in result.stdout.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        path = Path(candidate)
        if path.name in EXCLUDED_FILES:
            continue
        if any(str(path).startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            continue
        files.append(path)
    return files


def inspect_file(path: Path) -> list[tuple[int, str, str]]:
    """Check a single file for suspicious patterns."""

    findings: list[tuple[int, str, str]] = []
    if not path.exists() or path.is_dir():
        return findings
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return findings
    for line_no, line in enumerate(text.splitlines(), 1):
        for pattern, reason in PATTERN_CONFIG:
            if pattern.search(line):
                findings.append((line_no, reason, line.strip()))
    return findings


def main() -> int:
    files = staged_files()
    if not files:
        return 0

    violations: dict[Path, list[tuple[int, str, str]]] = {}
    for file_path in files:
        hits = inspect_file(file_path)
        if hits:
            violations[file_path] = hits

    if violations:
        print("Potentially sensitive content detected in staged files:")
        for path, hits in violations.items():
            for line_no, reason, snippet in hits:
                print(f"{path}:{line_no} — {reason}: {snippet}")
        print("Please remove or redact the sensitive content before committing.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
