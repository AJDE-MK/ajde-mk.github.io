"""Second pass of the video search, for songs the first pass found nothing for.

The first pass needed the video title to match the song title exactly. This pass accepts videos whose title carries
most of the song's title words, and uses the performer named in the songbook as extra evidence:
  title (75% of words) + performer in the title or channel  ->  added
  title only, or half the title + performer                 ->  held for review
  short titles (two words or fewer) need the performer, or they are ignored.
Each song is searched with its performer's name and with its first lyric line.

Usage:
  python tools\\site\\bulk_videos2.py [--limit N] [--delay SECONDS] [--debug]
  python tools\\site\\bulk_videos2.py --apply
Progress: data/bulk2_progress.json (resumable). Review list: docs/video-review-2.md. Log: data/bulk_videos2.log
"""
import argparse
import logging
import re
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bulk_videos as b1  # noqa: E402
import channel_videos as cv  # noqa: E402
import config  # noqa: E402
import songs as songs_data  # noqa: E402
import video_search as vs  # noqa: E402

log = logging.getLogger("site.bulk_videos2")

PROGRESS2_FILE = config.DATA_DIR / "bulk2_progress.json"
PASS1_FILE = b1.PROGRESS_FILE
REVIEW2_FILE = config.ROOT / "docs" / "video-review-2.md"

_CYR = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ѓ": "gj", "е": "e", "ж": "z", "з": "z", "ѕ": "dz",
    "и": "i", "ј": "j", "к": "k", "л": "l", "љ": "lj", "м": "m", "н": "n", "њ": "nj", "о": "o", "п": "p",
    "р": "r", "с": "s", "т": "t", "ќ": "kj", "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "c", "ш": "s", "џ": "dz",
}
_DIGRAPHS = [("gj", "g"), ("dj", "g"), ("kj", "k"), ("zh", "z"), ("sh", "s"), ("ch", "c"), ("dz", "z"),
             ("lj", "l"), ("nj", "n")]
GENERIC_WORDS = {"ansambl", "grupa", "orkestar", "oktet", "radio", "studio", "skopje", "narodni", "folklorna"}


def translit(text):
    return "".join(_CYR.get(ch, ch) for ch in (text or "").lower())


def fold(text):
    """Lower-case, strip accents, and fold the usual spelling variants (sh/š, zh/ž, ch/č, gj/ǵ, kj/ḱ) together."""
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    for a, b in _DIGRAPHS:
        text = text.replace(a, b)
    return text


def words(text):
    """Words of a text in one comparable form, whichever script it was written in."""
    return set(re.findall(r"[a-z0-9]+", fold(translit(text))))


def performer_evidence(song, result):
    blob = words(f"{result['title']} {result.get('channel', '')}")
    for performer in song.get("performers", []):
        sig = [w for w in words(performer) if len(w) >= 4 and w not in GENERIC_WORDS]
        if sig and all(w in blob for w in sig):
            return True
    return False


def title_recall(song, video_title):
    """Share of the song title's words that appear in the video title (best of the Cyrillic and Latin titles)."""
    video = words(video_title)
    best = 0.0
    for title in (song["title_cyr"], song["title_latin"]):
        wanted = words(title)
        if wanted:
            best = max(best, len(wanted & video) / len(wanted))
    return best


def _first_line(song):
    try:
        return song["versions"][0]["stanzas"][0]["lines"][0]["cyr"]
    except (KeyError, IndexError):
        return ""


def _queries(song):
    perfs = song.get("performers", [])
    queries = [f"{song['title_cyr']} {p}" for p in perfs[:2]]
    if perfs:
        queries.append(f"{song['title_latin']} {translit(perfs[0])}")
    else:
        queries.append(f"{song['title_cyr']} македонска народна песна")
    line = _first_line(song)
    if line:
        queries.append(line)
    return queries


def process_song(song, search=vs.youtube_search, embeddable=vs.is_embeddable, used_ids=()):
    """Returns {'status': added|review|none|error, 'song_id', 'video', 'error'?}."""
    try:
        pool, seen = [], set()
        for q in _queries(song):
            for r in search(q):
                if r["id"] not in seen:
                    seen.add(r["id"])
                    pool.append(r)
        short = b1.is_short_title(song)
        ranked = []
        for r in pool:
            if r["id"] in used_ids or not cv.is_sung_song(r["title"]):
                continue
            if r["seconds"] is None or r["seconds"] > vs.MAX_SECONDS:
                continue
            recall = title_recall(song, r["title"])
            perf = performer_evidence(song, r)
            if short:
                tier = 0 if (perf and recall >= 0.75) else None
            elif recall >= 0.75 and perf:
                tier = 0
            elif recall >= 0.75 or (recall >= 0.5 and perf):
                tier = 1
            else:
                tier = None
            if tier is not None:
                ranked.append((tier, -r["views"], r))
        for tier, _neg, r in sorted(ranked, key=lambda t: (t[0], t[1])):
            if embeddable(r["id"]):
                return {"status": "added" if tier == 0 else "review", "song_id": song["id"], "video": r}
        return {"status": "none", "song_id": song["id"], "video": None}
    except Exception as err:
        return {"status": "error", "song_id": song["id"], "video": None, "error": str(err)}


def songs_to_search(songs, pass1, pass2, existing_videos):
    """Songs the first pass found nothing for, that still have no video and are not done in this pass."""
    candidates = set(pass1["none"])
    done = set(pass2["done"]) - {int(k) for k in pass2["error"]}
    return [s for s in songs if s["id"] in candidates and s["id"] not in done and s["id"] not in existing_videos]


def review_markdown(progress, songs_by_id):
    lines = [
        "# Videos held for review (second pass)",
        "",
        "Found with weaker evidence: the title matches but the performer does not, or the performer matches and",
        "only part of the title does. Open each link and listen. Add the right ones with",
        "`python tools\\site\\videos_tool.py add <song> <link>`.",
        "",
        "| Song | Title | Video | Channel | Views | Link |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for key in sorted(progress["review"], key=int):
        s = songs_by_id.get(int(key))
        v = progress["review"][key]
        title = f"{s['title_cyr']} ({s['title_en']})" if s else key
        note = f" ({v['note']})" if v.get("note") else ""
        lines.append(f"| {key} | {title} | {v['title']}{note} | {v['channel']} | {v['views']:,} | "
                     f"[watch](https://www.youtube.com/watch?v={v['id']}) |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args(argv)

    handlers = [logging.FileHandler(config.DATA_DIR / "bulk_videos2.log", mode="a", encoding="utf-8")]
    if args.debug:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.DEBUG, handlers=handlers, format="%(asctime)s %(levelname)s %(name)s %(message)s", force=True
    )
    sys.stdout.reconfigure(encoding="utf-8")

    all_songs = songs_data.load_songs()
    by_id = {s["id"]: s for s in all_songs}
    pass1 = b1.load_progress(PASS1_FILE)
    pass2 = b1.load_progress(PROGRESS2_FILE)
    existing = songs_data.load_videos()

    if args.apply:
        print(f"added to videos.json: {b1.apply_added(pass2, existing)}")
        return 0

    todo = songs_to_search(all_songs, pass1, pass2, existing)
    if args.limit:
        todo = todo[: args.limit]
    print(f"songs to search: {len(todo)}")
    used = ({v["id"] for v in existing.values()} | {v["id"] for v in pass1["added"].values()}
            | {v["id"] for v in pass1["review"].values()} | {v["id"] for v in pass2["added"].values()}
            | {v["id"] for v in pass2["review"].values()})
    streak = 0
    for i, s in enumerate(todo, 1):
        out = process_song(s, used_ids=used)
        b1.record(pass2, out)
        if out["video"]:
            used.add(out["video"]["id"])
        log.debug("song %s -> %s", s["id"], out["status"])
        streak = streak + 1 if out["status"] == "error" else 0
        if streak >= 5:
            print("five errors in a row, pausing 90 seconds")
            time.sleep(90)
        if streak >= 20:
            print("twenty errors in a row, stopping. Progress is saved; run again later.")
            break
        if i % b1.SAVE_EVERY == 0:
            b1.save_progress(PROGRESS2_FILE, pass2)
            print(f"  {i}/{len(todo)}  added {len(pass2['added'])}  review {len(pass2['review'])}  "
                  f"none {len(pass2['none'])}  errors {len(pass2['error'])}")
        time.sleep(args.delay)
    b1.save_progress(PROGRESS2_FILE, pass2)
    REVIEW2_FILE.write_text(review_markdown(pass2, by_id), encoding="utf-8")
    print(f"done. added {len(pass2['added'])}  review {len(pass2['review'])}  none {len(pass2['none'])}  "
          f"errors {len(pass2['error'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
