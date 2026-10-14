import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Integrační testy používají Bearer token v hlavičce (ne HttpOnly cookie).
os.environ.setdefault("AUTH_USE_HTTPONLY_COOKIE", "false")
