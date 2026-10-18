"""Alphabet lesson data (data/alphabet.json)."""
import json
import logging

import config

log = logging.getLogger("site.alphabet")


def load_letters():
    """The 31 letters in standard order, as a list of dicts."""
    letters = json.loads(config.ALPHABET_FILE.read_text(encoding="utf-8"))
    log.debug("loaded %d letters", len(letters))
    return letters
