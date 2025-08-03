"""Test configuration to ensure modules see predictable paths."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

os.environ.setdefault("APP_DIR", str(ROOT))
os.environ.setdefault("DATA_DIR", str(ROOT / "test_data"))
os.makedirs(os.environ["DATA_DIR"], exist_ok=True)
os.environ.setdefault("STATIC_DIR", str(ROOT / "static"))
os.environ.setdefault("PROMPTS_FILE", str(ROOT / "prompts.yaml"))
os.environ.setdefault("TEMPLATES_DIR", str(ROOT / "templates"))
