"""Core application paths and configuration constants."""

from pathlib import Path
import os

# Allow overriding important paths via environment variables for easier testing
# and deployment in restricted environments.
APP_DIR = Path(os.getenv("APP_DIR", "/app"))
DATA_DIR = Path(os.getenv("DATA_DIR", "/journals"))
PROMPTS_FILE = Path(os.getenv("PROMPTS_FILE", str(APP_DIR / "prompts.json")))
STATIC_DIR = Path(os.getenv("STATIC_DIR", str(APP_DIR / "static")))
ENCODING = "utf-8"
WORDNIK_API_KEY = os.getenv("WORDNIK_API_KEY")
