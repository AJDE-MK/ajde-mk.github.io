"""Test helper: puts tools/site on sys.path so tests can import the site modules."""
import os
import sys
from pathlib import Path

# Tests must not depend on the build environment (CI sets these for the real build).
os.environ["MK_BASE_PATH"] = ""
os.environ["MK_FORM_KEY"] = ""

ROOT = Path(__file__).resolve().parents[1]
SITE_TOOLS = ROOT / "tools" / "site"
if str(SITE_TOOLS) not in sys.path:
    sys.path.insert(0, str(SITE_TOOLS))
