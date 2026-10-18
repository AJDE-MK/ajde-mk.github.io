"""Check a YouTube playlist against the songbook.

For each sung video: is the song in the songbook, does it already have a video, can this video be added,
or is the song missing (with the closest songbook titles as guesses)?

Usage: python tools\\site\\playlist_check.py PLAYLIST_ID [--add] [--debug]
Without --add it only reports. Debug log: data/playlist_check.log
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import channel_videos as cv  # noqa: E402
import config  # noqa: E402
import songs as songs_data  # noqa: E402
import video_search as vs  # noqa: E402
import videos_tool  # noqa: E402

log = logging.getLogger("site.playlist_check")

MAYBE_FLOOR = 0.4
STATUSES = ("can_add", "has_video", "maybe", "not_found")


def classify(videos, songs, existing):
    """One row per sung video. `existing` maps song id to its current video entry ({"id": ...})."""
    rows, proposed = [], {}
    for v in videos:
        if not cv.is_sung_song(v["title"]):
            continue
        scored = sorted(((cv.title_score(s, v["title"]), s) for s in songs), key=lambda t: (-t[0], t[1]["id"]))
        top_score, top_song = scored[0] if scored else (0.0, None)
        if top_song is not None and top_score >= 0.8:
            sid = top_song["id"]
            if sid in existing:
                rows.append({"video": v, "status": "has_video", "song": top_song, "candidates": [],
                             "same_video": existing[sid].get("id") == v["id"]})
            elif sid in proposed:
                rows.append({"video": v, "status": "has_video", "song": top_song, "candidates": [],
                             "same_video": False})
            else:
                proposed[sid] = v["id"]
                rows.append({"video": v, "status": "can_add", "song": top_song, "candidates": [],
                             "same_video": False})
            continue
        candidates = [s for score, s in scored[:3] if score >= MAYBE_FLOOR]
        rows.append({"video": v, "status": "maybe" if candidates else "not_found", "song": None,
                     "candidates": candidates, "same_video": False})
    return rows


def summarize(rows):
    counts = {s: 0 for s in STATUSES}
    for r in rows:
        counts[r["status"]] += 1
    return counts


def _link(v):
    return f"https://www.youtube.com/watch?v={v['id']}"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("playlist_id")
    ap.add_argument("--add", action="store_true", help="add the can_add videos (embeddable only) to data/videos.json")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args(argv)

    handlers = [logging.FileHandler(config.DATA_DIR / "playlist_check.log", mode="w", encoding="utf-8")]
    if args.debug:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.DEBUG, handlers=handlers, format="%(levelname)s %(name)s %(message)s", force=True
    )
    sys.stdout.reconfigure(encoding="utf-8")

    videos = cv.fetch_playlist_videos(args.playlist_id)
    existing = songs_data.load_videos()
    rows = classify(videos, songs_data.load_songs(), existing)
    counts = summarize(rows)
    print(f"playlist videos: {len(videos)}  sung: {len(rows)}")
    print("  " + "  ".join(f"{k}: {counts[k]}" for k in STATUSES))

    print("\nSONG IS IN THE SONGBOOK, VIDEO CAN BE ADDED")
    for r in rows:
        if r["status"] == "can_add":
            print(f"  #{r['song']['id']:<5} {r['song']['title_cyr']}  <-  {r['video']['title']}  {_link(r['video'])}")
    print("\nSONG IS IN THE SONGBOOK AND ALREADY HAS A VIDEO")
    for r in rows:
        if r["status"] == "has_video":
            tag = "same video" if r["same_video"] else "different video"
            print(f"  #{r['song']['id']:<5} {r['song']['title_cyr']}  ({tag})  playlist: {r['video']['title']}")
    print("\nCLOSE BUT NOT CERTAIN (check the spelling of the title)")
    for r in rows:
        if r["status"] == "maybe":
            guesses = "; ".join(f"#{s['id']} {s['title_cyr']}" for s in r["candidates"])
            print(f"  {r['video']['title']}  {_link(r['video'])}\n      closest: {guesses}")
    print("\nNOT FOUND IN THE SONGBOOK")
    for r in rows:
        if r["status"] == "not_found":
            print(f"  {r['video']['title']}  {_link(r['video'])}")

    if args.add:
        added = 0
        for r in rows:
            if r["status"] != "can_add":
                continue
            v = r["video"]
            if not vs.is_embeddable(v["id"]):
                print(f"skipped (cannot be embedded): #{r['song']['id']} {v['title']}")
                continue
            videos_tool.add_video(r["song"]["id"], _link(v))
            added += 1
        print(f"\nadded: {added}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
