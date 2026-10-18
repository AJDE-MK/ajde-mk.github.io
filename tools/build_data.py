"""Build normalized song data (3 columns everywhere) from the songbook Markdown.

Writes:
  data/songs/NNNN.json   one record per song; en is null where English still needs aligning
  data/work/NNNN.json    one work item per song whose Pesna English does not line up
  data/build.log         debug log (kept on purpose)
Never touches the songbook files.
"""
import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from songbook_parse import parse_song  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SONGS_DIR = ROOT / "songbook" / "songs"
DATA = ROOT / "data"
log = logging.getLogger("songbook.build")


def _line(cyr, lat, en):
    return {"cyr": cyr, "lat": lat, "en": en}


def _ratio_flags(version):
    """Count lines whose English word count is wildly off from the Cyrillic word count."""
    flags = 0
    for st in version["stanzas"]:
        for ln in st["lines"]:
            if not ln["en"]:
                continue
            a, b = len(ln["cyr"].split()), len(ln["en"].split())
            if a and (b / a > 3.0 or b / a < 0.34):
                flags += 1
    return flags


def build_song(song):
    """Return (record, work_item_or_None, stats)."""
    out_versions, pending = [], False
    for vi, v in enumerate(song["versions"]):
        stanzas = []
        for st in v["table"]:
            if v["columns"] == 3:
                stanzas.append({"lines": [_line(r[0], r[1], r[2]) for r in st]})
            else:
                stanzas.append({"lines": [_line(r[0], r[1], None) for r in st]})
        source = "mt" if v["columns"] == 3 else None
        out_versions.append({"label": v["label"], "en_source": source, "stanzas": stanzas})

    work = None
    if song["english_kind"] == "pesna":
        en = song["pesna_english"]
        v0 = out_versions[0]
        single = len(out_versions) == 1
        exact = (
            single
            and len(en) == len(v0["stanzas"])
            and all(len(a["lines"]) == len(b) for a, b in zip(v0["stanzas"], en))
        )
        proposed = None
        if exact:
            for st, en_st in zip(v0["stanzas"], en):
                for ln, text in zip(st["lines"], en_st):
                    ln["en"] = text
            v0["en_source"] = "pesna"
            proposed = [[ln["en"] for ln in st["lines"]] for st in v0["stanzas"]]
        else:
            pending = True
        work = {
            "id": song["id"],
            "kind": "verify" if exact else "align",
            "title_cyr": song["title_cyr"],
            "title_en": song["title_en"],
            "pesna_english_stanzas": en,
            "proposed_en_version_0": proposed,
            "versions": [
                {
                    "index": i,
                    "label": v["label"],
                    "stanzas": [
                        {"cyr": [l["cyr"] for l in s["lines"]], "lat": [l["lat"] for l in s["lines"]]}
                        for s in v["stanzas"]
                    ],
                }
                for i, v in enumerate(out_versions)
            ],
        }

    record = {
        "id": song["id"],
        "slug": song["slug"],
        "title_cyr": song["title_cyr"],
        "title_latin": song["title_latin"],
        "title_en": song["title_en"],
        "pesna_url": song["pesna_url"],
        "background": song["background"],
        "background_source": song["background_source"],
        "english_kind": song["english_kind"],
        "en_note": song["en_note"],
        "translator_notes": song["translator_notes"],
        "words_to_learn": song["words_to_learn"],
        "performers": song["performers"],
        "audio": song["audio"],
        "versions": out_versions,
        "pending_english": pending,
    }
    return record, work


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true", help="verbose console logging")
    args = ap.parse_args()
    (DATA / "songs").mkdir(parents=True, exist_ok=True)
    (DATA / "work").mkdir(parents=True, exist_ok=True)
    handlers = [logging.FileHandler(DATA / "build.log", mode="w", encoding="utf-8")]
    if args.debug:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(level=logging.DEBUG, handlers=handlers, format="%(levelname)s %(name)s %(message)s")
    sys.stdout.reconfigure(encoding="utf-8")

    counts = {"mt": 0, "pesna_exact": 0, "pesna_pending": 0}
    suspicious = []
    for f in sorted(SONGS_DIR.glob("*.md")):
        song = parse_song(f)
        record, work = build_song(song)
        (DATA / "songs" / f"{song['id']:04d}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        if work:
            (DATA / "work" / f"{song['id']:04d}.json").write_text(
                json.dumps(work, ensure_ascii=False, indent=1), encoding="utf-8"
            )
        if work and work["kind"] == "align":
            counts["pesna_pending"] += 1
        elif song["english_kind"] == "mt":
            counts["mt"] += 1
        else:
            counts["pesna_exact"] += 1
            flags = _ratio_flags(record["versions"][0])
            if flags:
                suspicious.append((song["id"], flags))
        log.debug("wrote %04d pending=%s", song["id"], record["pending_english"])

    print("songs:", sum(counts.values()))
    print("3-col machine translation:", counts["mt"])
    print("Pesna English merged by script:", counts["pesna_exact"])
    print("Pesna English needing alignment (work items):", counts["pesna_pending"])
    suspicious.sort(key=lambda t: -t[1])
    print("merged songs with lines whose word counts look off:", len(suspicious), suspicious[:15])


if __name__ == "__main__":
    main()
