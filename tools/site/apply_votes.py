"""Count the votes that visitors send from the review page, and apply the clear ones.

Paste the emails you received into a text file, then:
  python tools\\site\\apply_votes.py votes.txt                 show what the votes say (changes nothing)
  python tools\\site\\apply_votes.py votes.txt --apply         add accepted videos and drop rejected ones
Options: --min-yes N (default 2) and --min-no N (default 2): votes needed for a decision.
A video is accepted when it has enough yes votes and more than twice as many yes as no. It is rejected the other way.
Debug log: data/apply_votes.log
"""
import argparse
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bulk_videos as b1  # noqa: E402
import bulk_videos2 as b2  # noqa: E402
import config  # noqa: E402
import review_queue as rq  # noqa: E402
import songs as songs_data  # noqa: E402
import videos_tool  # noqa: E402

log = logging.getLogger("site.apply_votes")

_LINE = re.compile(r"song=(\d+)\s+video=([A-Za-z0-9_-]{11})\s+vote=(yes|no)\b")


def parse_votes(text):
    """{(song_id, video_id): {'yes': n, 'no': n}} from the pasted message lines. Anything else is ignored."""
    tally = {}
    for song, video, vote in _LINE.findall(text or ""):
        counts = tally.setdefault((int(song), video), {"yes": 0, "no": 0})
        counts[vote] += 1
    return tally


def decide(counts, min_yes=2, min_no=2):
    yes, no = counts["yes"], counts["no"]
    if yes >= min_yes and yes > 2 * no:
        return "accept"
    if no >= min_no and no > 2 * yes:
        return "reject"
    return "wait"


def plan(tally, queue, min_yes=2, min_no=2):
    """(accept ids, reject ids, waiting ids). Only votes for the queued video of a song count."""
    accept, reject, waiting = [], [], []
    for row in queue:
        counts = tally.get((row["song_id"], row["video"]["id"]))
        if counts is None:
            continue
        verdict = decide(counts, min_yes, min_no)
        {"accept": accept, "reject": reject, "wait": waiting}[verdict].append(row["song_id"])
    return accept, reject, waiting


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="text file with the pasted vote emails")
    ap.add_argument("--min-yes", type=int, default=2)
    ap.add_argument("--min-no", type=int, default=2)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args(argv)

    handlers = [logging.FileHandler(config.DATA_DIR / "apply_votes.log", mode="a", encoding="utf-8")]
    if args.debug:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.DEBUG, handlers=handlers, format="%(asctime)s %(levelname)s %(name)s %(message)s", force=True
    )
    sys.stdout.reconfigure(encoding="utf-8")

    tally = parse_votes(Path(args.file).read_text(encoding="utf-8", errors="replace"))
    songs_by_id = {s["id"]: s for s in songs_data.load_songs()}
    pass1, pass2 = b1.load_progress(b1.PROGRESS_FILE), b1.load_progress(b2.PROGRESS2_FILE)
    decisions = rq.load_decisions()
    existing = songs_data.load_videos()
    queue = rq.build_queue(pass1, pass2, songs_by_id, existing, decisions)
    accept, reject, waiting = plan(tally, queue, args.min_yes, args.min_no)

    print(f"vote lines read: {sum(c['yes'] + c['no'] for c in tally.values())}  songs voted on: {len(tally)}")
    print(f"accept: {accept}\nreject: {reject}\nwaiting for more votes: {waiting}")
    if args.apply:
        result = rq.apply_decisions(queue, accept, reject, decisions, existing, videos_tool.add_video)
        rq.save_decisions(decisions)
        print(result)
    else:
        print("(nothing changed; add --apply to apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
