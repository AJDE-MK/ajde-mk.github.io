"""Find a YouTube video for every song that has none. Resumable, polite to YouTube, careful about wrong matches.

For each song: search YouTube twice (Cyrillic title, Latin title), keep only videos whose title carries the same
words as the song title, are a normal length, are not instrumentals, and can be embedded. The one with the most
views wins. Songs with a short title (two words or fewer), and videos with under 300 views, are only HELD for
review: the same short title can belong to many different songs, and a tiny upload is often not the right one.

Usage:
  python tools\\site\\bulk_videos.py [--limit N] [--delay SECONDS] [--debug]   search and record results
  python tools\\site\\bulk_videos.py --apply                                    add the confident results to videos.json
Progress is saved to data/bulk_progress.json after every 20 songs, so a stopped run resumes where it left off.
Review list: docs/video-review.md. Debug log: data/bulk_videos.log
"""
import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import channel_videos as cv  # noqa: E402
import config  # noqa: E402
import songs as songs_data  # noqa: E402
import video_search as vs  # noqa: E402
import videos_tool  # noqa: E402

log = logging.getLogger("site.bulk_videos")

PROGRESS_FILE = config.DATA_DIR / "bulk_progress.json"
REVIEW_FILE = config.ROOT / "docs" / "video-review.md"
SAVE_EVERY = 20
MIN_VIEWS = 300


def is_short_title(song):
    """Two words or fewer: too generic to trust an automatic match."""
    return len(vs._normalize(song["title_latin"])) <= 2 or len(vs._normalize(song["title_cyr"])) <= 2


def process_song(song, search=vs.youtube_search, embeddable=vs.is_embeddable, used_ids=()):
    """Look up one song. Returns {'status': added|review|none|error, 'song_id', 'video', 'error'?}."""
    try:
        pool, seen = [], set()
        for query in (f"{song['title_cyr']} песна", f"{song['title_latin']} makedonska pesna"):
            for r in search(query):
                if r["id"] not in seen:
                    seen.add(r["id"])
                    pool.append(r)
        for r in sorted(pool, key=lambda x: x["views"], reverse=True):
            if r["id"] in used_ids or not cv.is_sung_song(r["title"]) or not cv.title_core_matches(song, r["title"]):
                continue
            if r["seconds"] is None or r["seconds"] > vs.MAX_SECONDS:
                continue
            if not embeddable(r["id"]):
                continue
            unsure = is_short_title(song) or r["views"] < MIN_VIEWS
            return {"status": "review" if unsure else "added", "song_id": song["id"], "video": r}
        return {"status": "none", "song_id": song["id"], "video": None}
    except Exception as err:  # network trouble, a changed page, rate limiting
        return {"status": "error", "song_id": song["id"], "video": None, "error": str(err)}


def load_progress(path=PROGRESS_FILE):
    if Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return {"done": [], "added": {}, "review": {}, "none": [], "error": {}}


def save_progress(path, progress):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(progress, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def record(progress, out):
    sid = out["song_id"]
    key = str(sid)
    if sid not in progress["done"]:
        progress["done"].append(sid)
    progress["error"].pop(key, None)
    status = out["status"]
    if status == "added":
        progress["added"][key] = out["video"]
    elif status == "review":
        progress["review"][key] = out["video"]
    elif status == "none":
        if sid not in progress["none"]:
            progress["none"].append(sid)
    elif status == "error":
        progress["error"][key] = out.get("error", "unknown error")


def songs_to_search(songs, progress, existing_videos):
    """Songs with no video that are not done yet. Songs that failed with an error are tried again."""
    done = set(progress["done"]) - {int(k) for k in progress["error"]}
    return [s for s in songs if s["id"] not in done and s["id"] not in existing_videos]


def review_markdown(progress, songs_by_id):
    lines = [
        "# Videos held for review",
        "",
        "These songs have short titles or the video has few views, so it may be a different song. Open each link, listen, and",
        "add the right ones with `python tools\\site\\videos_tool.py add <song> <link>`.",
        "",
        "| Song | Title | Video | Channel | Views | Link |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for key in sorted(progress["review"], key=int):
        s = songs_by_id.get(int(key))
        v = progress["review"][key]
        title = f"{s['title_cyr']} ({s['title_en']})" if s else key
        lines.append(f"| {key} | {title} | {v['title']} | {v['channel']} | {v['views']:,} | "
                     f"[watch](https://www.youtube.com/watch?v={v['id']}) |")
    return "\n".join(lines) + "\n"


def apply_added(progress, existing_videos):
    """Write the confident results into videos.json. Skips songs that now have a video and repeated video ids."""
    used = {v["id"] for v in existing_videos.values()}
    added = 0
    for key in sorted(progress["added"], key=int):
        sid, v = int(key), progress["added"][key]
        if sid in existing_videos or v["id"] in used:
            continue
        videos_tool.add_video(sid, f"https://www.youtube.com/watch?v={v['id']}")
        used.add(v["id"])
        added += 1
    return added


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="only search this many songs (0 = all)")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between songs")
    ap.add_argument("--apply", action="store_true", help="add confident results to videos.json and stop")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args(argv)

    handlers = [logging.FileHandler(config.DATA_DIR / "bulk_videos.log", mode="a", encoding="utf-8")]
    if args.debug:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.DEBUG, handlers=handlers, format="%(asctime)s %(levelname)s %(name)s %(message)s", force=True
    )
    sys.stdout.reconfigure(encoding="utf-8")

    all_songs = songs_data.load_songs()
    by_id = {s["id"]: s for s in all_songs}
    progress = load_progress()
    existing = songs_data.load_videos()

    if args.apply:
        n = apply_added(progress, existing)
        print(f"added to videos.json: {n}")
        return 0

    todo = songs_to_search(all_songs, progress, existing)
    if args.limit:
        todo = todo[: args.limit]
    print(f"songs to search: {len(todo)}")
    used = {v["id"] for v in existing.values()} | {v["id"] for v in progress["added"].values()} \
        | {v["id"] for v in progress["review"].values()}
    streak = 0
    for i, s in enumerate(todo, 1):
        out = process_song(s, used_ids=used)
        record(progress, out)
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
        if i % SAVE_EVERY == 0:
            save_progress(PROGRESS_FILE, progress)
            print(f"  {i}/{len(todo)}  added {len(progress['added'])}  review {len(progress['review'])}  "
                  f"none {len(progress['none'])}  errors {len(progress['error'])}")
        time.sleep(args.delay)
    save_progress(PROGRESS_FILE, progress)
    REVIEW_FILE.write_text(review_markdown(progress, by_id), encoding="utf-8")
    print(f"done. added {len(progress['added'])}  review {len(progress['review'])}  none {len(progress['none'])}  "
          f"errors {len(progress['error'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
