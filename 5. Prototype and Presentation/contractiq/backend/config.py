"""Runtime configuration. Everything is read from environment variables with safe defaults."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = APP_DIR.parent

# The original dataset is only ever READ. Nothing in the app writes into this folder.
DATASET_DIR = Path(os.environ.get("CONTRACTIQ_DATASET_DIR", PROJECT_DIR / "Dataset")).resolve()

DATA_DIR = Path(os.environ.get("CONTRACTIQ_DATA_DIR", APP_DIR / "data")).resolve()
DB_PATH = DATA_DIR / "contractiq.db"
UPLOAD_DIR = DATA_DIR / "uploads"
EXTRACTED_DIR = DATA_DIR / "extracted"

# The dataset README says: treat "today" as 2026-09-28. Override with CONTRACTIQ_AS_OF=YYYY-MM-DD.
AS_OF = date.fromisoformat(os.environ.get("CONTRACTIQ_AS_OF", "2026-09-28"))

# AI is only available when a key is configured. Even then, every external call needs explicit
# per-request consent from the user in the UI (see llm.py).
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
AI_MODEL = os.environ.get("CONTRACTIQ_AI_MODEL", "claude-opus-5-5")
AI_AVAILABLE = bool(ANTHROPIC_API_KEY)

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
EXPIRY_WINDOW_DAYS = int(os.environ.get("CONTRACTIQ_EXPIRY_WINDOW_DAYS", "90"))

CHECKLIST_VERSION = "Karandeep checklist, last edited March 2024 (unapproved personal notes)"

for d in (DATA_DIR, UPLOAD_DIR, EXTRACTED_DIR):
    d.mkdir(parents=True, exist_ok=True)
