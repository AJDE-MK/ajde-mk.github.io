"""Parse one songbook song page (Markdown) into a plain dict.

The songbook pages come in two English shapes:
  * "mt":    3-column lyric tables (Cyrillic | Latin | English), English is a machine translation.
  * "pesna": 2-column lyric tables plus an English section of blockquote stanzas from Pesna.org.
"""
import logging
import re
from pathlib import Path

log = logging.getLogger("songbook.parse")

SEP_CELLS = set("- ")


def _cells(line):
    s = line.strip()
    s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _is_separator(line):
    return set(line.replace("|", "").strip()) <= SEP_CELLS


def _sections(text):
    """Return list of (heading, body) for every '## ' section, in order."""
    parts = re.split(r"^## (.+)$", text, flags=re.M)
    return [(parts[i].strip(), parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


def _parse_lyric_tables(body):
    """Return stanzas as list of lists of cell-lists. Header rows start a new stanza."""
    stanzas, cur, ncols = [], None, 0
    for line in body.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = _cells(s)
        if cells and cells[0] == "Cyrillic":
            cur = []
            stanzas.append(cur)
            ncols = len(cells)
        elif _is_separator(s):
            continue
        else:
            if cur is None:
                raise ValueError("lyric row before header: " + s[:60])
            if len(cells) != ncols:
                raise ValueError("ragged row: " + s[:60])
            cur.append(cells)
    return stanzas, ncols


def _parse_pesna_english(body):
    stanzas, cur = [], []
    for line in body.splitlines():
        if line.startswith(">"):
            t = line[1:].strip()
            if t:
                cur.append(t)
            elif cur:
                stanzas.append(cur)
                cur = []
    if cur:
        stanzas.append(cur)
    return stanzas


def _parse_words_table(body):
    words = []
    for line in body.splitlines():
        s = line.strip()
        if not s.startswith("|") or _is_separator(s):
            continue
        cells = _cells(s)
        if len(cells) == 2 and cells[0] != "Macedonian":
            words.append({"mk": cells[0], "en": cells[1]})
    return words


def parse_song(path):
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    m = re.match(r"(\d+)-(.+)\.md$", path.name)
    song = {"id": int(m.group(1)), "slug": m.group(2), "file": path.name}

    song["title_cyr"] = re.search(r"^# (.+)$", text, re.M).group(1).strip()
    tl = re.search(r"^\*(.+?)\*\s*·\s*\*(.+?)\*\s*$", text, re.M)
    song["title_latin"] = tl.group(1) if tl else ""
    song["title_en"] = tl.group(2) if tl else ""
    pu = re.search(r"^Pesna\.org #(\d+): <(.+?)>", text, re.M)
    song["pesna_url"] = pu.group(2) if pu else ""

    song["background"] = ""
    song["background_source"] = ""
    song["versions"] = []
    song["english_kind"] = None
    song["pesna_english"] = []
    song["en_note"] = ""
    song["translator_notes"] = ""
    song["words_to_learn"] = []
    song["performers"] = []
    song["audio"] = []

    for head, body in _sections(text):
        if head == "Background":
            lines = [l for l in body.strip().splitlines() if l.strip()]
            src = [l for l in lines if l.startswith("*Source of these notes")]
            song["background_source"] = src[0].strip("*") if src else ""
            song["background"] = "\n".join(l for l in lines if l not in src).strip()
        elif head.startswith("Lyrics"):
            stanzas, ncols = _parse_lyric_tables(body)
            vm = re.search(r"version (\d+)", head)
            song["versions"].append(
                {"label": f"Version {vm.group(1)}" if vm else "", "columns": ncols, "table": stanzas}
            )
        elif head == "English":
            if ">" in body and any(l.startswith(">") for l in body.splitlines()):
                song["english_kind"] = "pesna"
                song["pesna_english"] = _parse_pesna_english(body)
                src = re.search(r"^\*From Pesna\.org.*\*\s*$", body, re.M)
                song["en_note"] = src.group(0).strip("*") if src else ""
            else:
                song["english_kind"] = "mt"
                note = re.search(r"^\*(Machine translation.+?)\*\s*$", body, re.M)
                song["en_note"] = note.group(1) if note else ""
                tn = re.search(r"^\*\*Translator's notes\.\*\*\s*(.+)$", body, re.M)
                song["translator_notes"] = tn.group(1).strip() if tn else ""
                song["words_to_learn"] = _parse_words_table(body)
        elif head == "Listen":
            pm = re.search(r"^- Performers: (.+)$", body, re.M)
            song["performers"] = [p.strip() for p in pm.group(1).split(",")] if pm else []
            song["audio"] = [
                {"who": w.strip(), "url": u}
                for w, u in re.findall(r"^- (.+?): <(https://pesna\.org/audio-download/\d+)>", body, re.M)
            ]
    log.debug("parsed %s kind=%s versions=%d", path.name, song["english_kind"], len(song["versions"]))
    return song
