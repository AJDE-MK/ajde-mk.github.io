"""Safety check for matched videos: does the video's title fit ANOTHER song better than the one it was given to?

The songbook has many near-twin titles (for example "Бог да бие мојта мајка" and "Бог да бие Русе твојта мајка").
A video for one can look like a match for the other. This check moves such videos from "added" to "review".

Usage: python tools\\site\\video_audit.py [--debug]
Reads and rewrites data/bulk_progress.json and data/bulk2_progress.json. Review lists are rewritten too.
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bulk_videos as b1  # noqa: E402
import bulk_videos2 as b2  # noqa: E402
import config  # noqa: E402
import songs as songs_data  # noqa: E402
import videos_tool  # noqa: E402

log = logging.getLogger("site.video_audit")
FLOOR = 0.6


def _title_words(song):
    return [w for w in (b2.words(song["title_cyr"]), b2.words(song["title_latin"])) if w]


def _fit(song_words, video_words):
    """(recall, jaccard): how much of the song title is in the video title, and how tightly the words agree."""
    best = (0.0, 0.0)
    for wanted in song_words:
        inter = len(wanted & video_words)
        best = max(best, (inter / len(wanted), inter / len(wanted | video_words)))
    return best


def _best(songs, song_words, video_title):
    video_words = b2.words(video_title)
    scored = [(_fit(song_words[s["id"]], video_words), s) for s in songs]
    scored.sort(key=lambda t: (t[0], -t[1]["id"]), reverse=True)
    return scored[0] if scored else ((0.0, 0.0), None)


def best_song(songs, video_title, floor=FLOOR):
    """The song whose title fits the video title best, or None if none fits at least `floor`."""
    words = {s["id"]: _title_words(s) for s in songs}
    (recall, _jac), song = _best(songs, words, video_title)
    return song if song is not None and recall >= floor else None


def find_conflicts(entries, songs):
    """[(assigned_song_id, better_song_id)] for videos that fit another song strictly better."""
    words = {s["id"]: _title_words(s) for s in songs}
    by_id = {s["id"]: s for s in songs}
    conflicts = []
    for key, entry in entries.items():
        assigned = by_id.get(int(key))
        if assigned is None:
            continue
        video_words = b2.words(entry["title"])
        own = _fit(words[assigned["id"]], video_words)
        (best_fit, best) = _best(songs, words, entry["title"])
        if best is not None and best["id"] != assigned["id"] and best_fit[0] >= FLOOR and best_fit > own:
            conflicts.append((assigned["id"], best["id"]))
    return conflicts


def demote_conflicts(progress, songs):
    """Move conflicting videos from progress['added'] to progress['review'], with a note. Returns the conflicts."""
    conflicts = find_conflicts(progress["added"], songs)
    for sid, other in conflicts:
        video = progress["added"].pop(str(sid))
        video = dict(video, note=f"also fits song {other} better")
        progress["review"][str(sid)] = video
    return conflicts


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args(argv)
    handlers = [logging.FileHandler(config.DATA_DIR / "video_audit.log", mode="w", encoding="utf-8")]
    if args.debug:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.DEBUG, handlers=handlers, format="%(levelname)s %(name)s %(message)s", force=True
    )
    sys.stdout.reconfigure(encoding="utf-8")

    songs = songs_data.load_songs()
    by_id = {s["id"]: s for s in songs}
    applied = songs_data.load_videos()
    # Pass 1 results were already written to videos.json, so a demoted one must be removed from there too.
    for label, path, already_on_site in (("pass 1", b1.PROGRESS_FILE, True), ("pass 2", b2.PROGRESS2_FILE, False)):
        progress = b1.load_progress(path)
        before = len(progress["added"])
        moved = demote_conflicts(progress, songs)
        b1.save_progress(path, progress)
        if label == "pass 1":
            b1.REVIEW_FILE.write_text(b1.review_markdown(progress, by_id), encoding="utf-8")
        else:
            b2.REVIEW2_FILE.write_text(b2.review_markdown(progress, by_id), encoding="utf-8")
        print(f"{label}: checked {before} confident matches, moved {len(moved)} to review")
        for sid, other in moved:
            video = progress["review"][str(sid)]
            removed = False
            if already_on_site and sid in applied:
                removed = videos_tool.remove_video(sid, only_if_id=video["id"])
            print(f"   #{sid} {by_id[sid]['title_cyr']}  <- video: {video['title']}  "
                  f"(fits #{other} {by_id[other]['title_cyr']} better){'  [removed from the site]' if removed else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
