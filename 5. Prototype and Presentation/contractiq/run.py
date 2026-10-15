"""Start AtliQ ContractIQ on http://127.0.0.1:8000 (localhost only).

AI is optional: set GROQ_API_KEY or ANTHROPIC_API_KEY in the environment before starting.
Without a key the app runs in an explicitly labelled demo mode.
"""
import os
import sys
from pathlib import Path

import uvicorn

HERE = Path(__file__).resolve().parent
os.chdir(HERE)
sys.path.insert(0, str(HERE))

if __name__ == "__main__":
    uvicorn.run("backend.app:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8000")),
                reload=bool(os.environ.get("CONTRACTIQ_RELOAD")))
