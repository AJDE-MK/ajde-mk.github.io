"""Site settings. Change values here, or set the environment variables MK_BASE_PATH and MK_FORM_KEY."""
import os
from pathlib import Path

SITE_TITLE = "Ајде"
SITE_TAGLINE = "Ajde: learn Macedonian through its songs"


def _base_path(raw):
    raw = (raw or "").strip().rstrip("/")
    if raw and not raw.startswith("/"):
        raw = "/" + raw
    return raw


# Path prefix when the site is served from a sub-folder, e.g. "/my-repo". Empty for a root site.
BASE_PATH = _base_path(os.environ.get("MK_BASE_PATH", ""))

# Web3Forms access key. It is a public value by design. Empty means "Feedback form coming soon".
FORM_KEY = os.environ.get("MK_FORM_KEY", "").strip()

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
SONGS_DIR = DATA_DIR / "songs"
VIDEOS_FILE = DATA_DIR / "videos.json"
ALPHABET_FILE = DATA_DIR / "alphabet.json"
STATIC_DIR = Path(__file__).resolve().parent / "static"
SITE_DIR = ROOT / "site"
LOG_FILE = DATA_DIR / "site_build.log"

ATTRIBUTION = "Lyrics: Pesna.org (folk lyrics in the public domain; site content CC BY)."
