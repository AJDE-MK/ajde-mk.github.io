"""Heuristic alignment check for songs whose English was merged from Pesna.org.

For each merged song, correlate Cyrillic line length with English line length.
If shifting the English by one line (either way) fits clearly better than the aligned
pairing, or the aligned fit is weak, the song is listed for review.
Prints a list. Never changes data.
"""
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SONGS = ROOT / "data" / "songs"


def corr(xs, ys):
    if len(xs) < 4:
        return None
    try:
        return statistics.correlation(xs, ys)
    except statistics.StatisticsError:
        return None


def check(record):
    cyr, en = [], []
    for v in record["versions"][:1]:
        for st in v["stanzas"]:
            for ln in st["lines"]:
                cyr.append(len(ln["cyr"]))
                en.append(len(ln["en"] or ""))
    base = corr(cyr, en)
    up = corr(cyr[1:], en[:-1])
    down = corr(cyr[:-1], en[1:])
    return base, up, down


def main(min_gain=0.15, min_base=0.45):
    sys.stdout.reconfigure(encoding="utf-8")
    flagged = []
    total = 0
    for p in sorted(SONGS.glob("*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        if r["versions"][0]["en_source"] != "pesna":
            continue
        total += 1
        base, up, down = check(r)
        if base is None:
            continue
        best_shift = max([c for c in (up, down) if c is not None], default=-1)
        if best_shift - base > min_gain or base < min_base:
            flagged.append((r["id"], round(base, 2), round(best_shift, 2)))
    print("merged songs checked:", total)
    print("flagged for review:", len(flagged))
    print("(id, aligned_corr, best_shifted_corr)")
    for t in flagged:
        print(" ", t)


if __name__ == "__main__":
    main()
