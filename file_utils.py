"""Utility functions for reading and parsing journal entries."""

from pathlib import Path
import re
from typing import List, Tuple, Optional

import aiofiles

from config import DATA_DIR, ENCODING


def safe_entry_path(entry_date: str, data_dir: Path = DATA_DIR) -> Path:
    """Return a normalized path for the given entry date inside ``data_dir``."""
    sanitized = Path(entry_date).name
    sanitized = re.sub(r"[^0-9A-Za-z_-]", "_", sanitized)
    if not sanitized:
        raise ValueError("Invalid entry date")
    path = (data_dir / sanitized).with_suffix(".md")
    # Ensure the path cannot escape ``data_dir``
    try:
        path.resolve().relative_to(data_dir.resolve())
    except ValueError as exc:
        raise ValueError("Invalid entry date") from exc
    return path


def parse_entry(md_content: str) -> Tuple[str, str]:
    """Return (prompt, entry) sections from markdown without raising errors."""
    prompt_lines: List[str] = []
    entry_lines: List[str] = []
    current_section = None
    for line in md_content.splitlines():
        stripped = line.strip()
        if stripped == "# Prompt":
            current_section = "prompt"
            continue
        if stripped == "# Entry":
            current_section = "entry"
            continue
        if current_section == "prompt":
            prompt_lines.append(line.rstrip())
        elif current_section == "entry":
            entry_lines.append(line.rstrip())

    prompt = "\n".join(prompt_lines).strip()
    entry = "\n".join(entry_lines).strip()
    return prompt, entry


def split_frontmatter(text: str) -> Tuple[Optional[str], str]:
    """Return frontmatter and remaining content if present."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1].strip()
            body = parts[2].lstrip("\n")
            return fm, body
    return None, text


async def read_existing_frontmatter(file_path: Path) -> Optional[str]:
    """Return frontmatter from the given file path if present."""
    try:
        async with aiofiles.open(file_path, "r", encoding=ENCODING) as fh:
            existing = await fh.read()
        frontmatter, _ = split_frontmatter(existing)
        return frontmatter
    except OSError:
        return None
