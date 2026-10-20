"""Walk through the videos held for review, a few at a time.

Usage:
  python tools\\site\\review_queue.py next [--n 8]       show the next batch (most-viewed first)
  python tools\\site\\review_queue.py accept 12 15 ...    add these songs' videos to the site
  python tools\\site\\review_queue.py reject 20 21 ...    never show these again
  python tools\\site\\review_queue.py status              how many are left
Decisions are kept in data/review_decisions.json. Debug log: data/review_queue.log
"""
import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bulk_videos as b1  # noqa: E402
import bulk_videos2 as b2  # noqa: E402
import config  # noqa: E402
import songs as songs_data  # noqa: E402
import videos_tool  # noqa: E402

log = logging.getLogger("site.review_queue")
DECISIONS_FILE = config.DATA_DIR / "review_decisions.json"


def load_decisions(path=DECISIONS_FILE):
    if Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return {"accepted": [], "rejected": []}


def save_decisions(decisions, path=DECISIONS_FILE):
    Path(path).write_text(json.dumps(decisions, indent=1) + "\n", encoding="utf-8")


def build_queue(pass1, pass2, songs_by_id, existing_videos, decisions):
    """Rows still to look at, most-viewed first. A song in both passes uses its pass-2 video."""
    chosen = {}
    for progress in (pass1, pass2):
        for key, video in progress["review"].items():
            chosen[int(key)] = video
    skip = set(decisions["accepted"]) | set(decisions["rejected"]) | set(existing_videos)
    rows = [
        {"song_id": sid, "song": songs_by_id[sid], "video": video}
        for sid, video in chosen.items()
        if sid not in skip and sid in songs_by_id
    ]
    rows.sort(key=lambda r: (-r["video"]["views"], r["song_id"]))
    return rows


def next_batch(queue, n):
    return queue[:n]


def format_row(row):
    s, v = row["song"], row["video"]
    note = f"\n      note:    {v['note']}" if v.get("note") else ""
    return (
        f"#{row['song_id']}  {s['title_cyr']}  |  {s['title_latin']}  |  {s['title_en']}\n"
        f"      video:   {v['title']}\n"
        f"      channel: {v['channel']}   views: {v['views']:,}{note}\n"
        f"      link:    https://www.youtube.com/watch?v={v['id']}"
    )


def apply_decisions(queue, accept_ids, reject_ids, decisions, existing_videos, add_fn):
    """Apply accept/reject choices. Returns {'added': [...], 'rejected': [...], 'skipped': [(id, why)], 'unknown': [...]}."""
    both = set(accept_ids) & set(reject_ids)
    if both:
        raise ValueError(f"These are in both lists: {sorted(both)}")
    by_id = {r["song_id"]: r for r in queue}
    used = {v["id"] for v in existing_videos.values()}
    result = {"added": [], "rejected": [], "skipped": [], "unknown": []}
    for sid in accept_ids:
        row = by_id.get(sid)
        if row is None:
            result["unknown"].append(sid)
        elif sid in existing_videos:
            result["skipped"].append((sid, "already has a video"))
        elif row["video"]["id"] in used:
            result["skipped"].append((sid, "that video is already used by another song"))
        else:
            add_fn(sid, f"https://www.youtube.com/watch?v={row['video']['id']}")
            used.add(row["video"]["id"])
            decisions["accepted"].append(sid)
            result["added"].append(sid)
    for sid in reject_ids:
        if sid not in by_id:
            result["unknown"].append(sid)
        else:
            decisions["rejected"].append(sid)
            result["rejected"].append(sid)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    nxt = sub.add_parser("next")
    nxt.add_argument("--n", type=int, default=8)
    acc = sub.add_parser("accept")
    acc.add_argument("ids", type=int, nargs="+")
    rej = sub.add_parser("reject")
    rej.add_argument("ids", type=int, nargs="+")
    sub.add_parser("status")
    args = ap.parse_args(argv)

    handlers = [logging.FileHandler(config.DATA_DIR / "review_queue.log", mode="a", encoding="utf-8")]
    if args.debug:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.DEBUG, handlers=handlers, format="%(asctime)s %(levelname)s %(name)s %(message)s", force=True
    )
    sys.stdout.reconfigure(encoding="utf-8")

    songs_by_id = {s["id"]: s for s in songs_data.load_songs()}
    pass1, pass2 = b1.load_progress(b1.PROGRESS_FILE), b1.load_progress(b2.PROGRESS2_FILE)
    decisions = load_decisions()
    existing = songs_data.load_videos()
    queue = build_queue(pass1, pass2, songs_by_id, existing, decisions)

    if args.cmd == "status":
        print(f"left to review: {len(queue)}  accepted so far: {len(decisions['accepted'])}  "
              f"rejected so far: {len(decisions['rejected'])}")
        return 0
    if args.cmd == "next":
        for row in next_batch(queue, args.n):
            print(format_row(row))
            print()
        print(f"({len(queue)} left in total)")
        return 0
    accept = args.ids if args.cmd == "accept" else []
    reject = args.ids if args.cmd == "reject" else []
    result = apply_decisions(queue, accept, reject, decisions, existing, videos_tool.add_video)
    save_decisions(decisions)
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
