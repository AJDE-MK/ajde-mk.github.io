"""Validate agent output in data/work_out and merge it into data/songs.

Checks per song:
  * stanza and line counts match the Cyrillic exactly, en and mt lists have equal length
  * lines marked mt=false use only words found in Pesna's English (reflow check)
Songs that fail are listed and NOT merged. Run after build_data.py; safe to re-run.
"""
import argparse
import json
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
log = logging.getLogger("songbook.merge")


def _words(text):
    return re.findall(r"[^\W\d_]+", text.lower())


def validate(work, out):
    """Return (problems, foreign_word_ratio) for an agent output against its work item."""
    problems = []
    pesna_words = {w for st in work["pesna_english_stanzas"] for ln in st for w in _words(ln)}
    by_index = {v["index"]: v for v in out.get("versions", [])}
    foreign = total = 0
    for v in work["versions"]:
        ov = by_index.get(v["index"])
        if ov is None:
            problems.append(f"version {v['index']} missing")
            continue
        if len(ov["stanzas"]) != len(v["stanzas"]):
            problems.append(f"v{v['index']} stanza count {len(ov['stanzas'])} != {len(v['stanzas'])}")
            continue
        for si, (st, ost) in enumerate(zip(v["stanzas"], ov["stanzas"])):
            n = len(st["cyr"])
            if len(ost["en"]) != n or len(ost["mt"]) != n:
                problems.append(f"v{v['index']} s{si} lines en={len(ost['en'])} mt={len(ost['mt'])} cyr={n}")
                continue
            for text, mt in zip(ost["en"], ost["mt"]):
                if mt:
                    continue
                for w in _words(text):
                    total += 1
                    if w not in pesna_words:
                        foreign += 1
            if any(("—" in t or "–" in t) for t in ost["en"]):
                problems.append(f"v{v['index']} s{si} contains long dash")
    ratio = (foreign / total) if total else 0.0
    return problems, ratio


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-foreign", type=float, default=0.15, help="max share of non-mt words not in Pesna text")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    handlers = [logging.FileHandler(DATA / "merge.log", mode="w", encoding="utf-8")]
    if args.debug:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(level=logging.DEBUG, handlers=handlers, format="%(levelname)s %(name)s %(message)s")
    sys.stdout.reconfigure(encoding="utf-8")

    done = {"ok": 0, "fixed": 0, "aligned": 0}
    failed = []
    missing = []
    for wp in sorted((DATA / "work").glob("*.json")):
        work = json.loads(wp.read_text(encoding="utf-8"))
        op = DATA / "work_out" / wp.name
        if not op.exists():
            missing.append(work["id"])
            continue
        out = json.loads(op.read_text(encoding="utf-8"))
        status = out.get("status")
        if status == "ok":
            if work["kind"] != "verify":
                failed.append((work["id"], ["status ok on an align item"]))
                continue
            done["ok"] += 1
            continue
        problems, ratio = validate(work, out)
        if ratio > args.max_foreign:
            problems.append(f"{ratio:.0%} of non-mt words are not in Pesna text")
        if problems:
            failed.append((work["id"], problems))
            log.debug("FAIL %s %s", work["id"], problems)
            continue
        sp = DATA / "songs" / wp.name
        song = json.loads(sp.read_text(encoding="utf-8"))
        for v, ov in zip(song["versions"], sorted(out["versions"], key=lambda x: x["index"])):
            any_mt = False
            all_mt = True
            for st, ost in zip(v["stanzas"], ov["stanzas"]):
                for ln, text, mt in zip(st["lines"], ost["en"], ost["mt"]):
                    ln["en"] = text
                    ln["en_mt"] = bool(mt)
                    any_mt = any_mt or mt
                    all_mt = all_mt and mt
            v["en_source"] = "mt" if all_mt else ("mixed" if any_mt else "pesna")
        song["pending_english"] = False
        sp.write_text(json.dumps(song, ensure_ascii=False, indent=1), encoding="utf-8")
        done[status if status in done else "aligned"] += 1
        log.debug("merged %s status=%s", work["id"], status)

    print("ok (no change):", done["ok"], " fixed:", done["fixed"], " aligned:", done["aligned"])
    print("not yet done (no output file):", len(missing))
    print("failed validation:", len(failed))
    for i, p in failed[:40]:
        print(" ", i, p)


if __name__ == "__main__":
    main()
