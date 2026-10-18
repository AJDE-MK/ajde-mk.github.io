"""Video list tools. data/videos.json maps song number to a YouTube video.

CLI:
  python tools\\site\\videos_tool.py add <song_id> <youtube_url> [--start SECONDS] [--debug]
  python tools\\site\\videos_tool.py validate [--debug]
"""
import argparse
import json
import logging
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

log = logging.getLogger("site.videos")

ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def parse_youtube_id(url):
    """Return the 11-character video ID from a YouTube URL, or None."""
    try:
        parsed = urlparse(url.strip())
    except (AttributeError, ValueError):
        return None
    host = (parsed.hostname or "").lower()
    candidate = None
    if host in ("youtu.be", "www.youtu.be"):
        candidate = parsed.path.lstrip("/").split("/")[0]
    elif host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        parts = [p for p in parsed.path.split("/") if p]
        if parsed.path.startswith("/watch"):
            candidate = (parse_qs(parsed.query).get("v") or [None])[0]
        elif len(parts) >= 2 and parts[0] in ("embed", "shorts", "v", "live"):
            candidate = parts[1]
    if candidate and ID_RE.match(candidate):
        return candidate
    return None


def validate_videos(videos, song_ids):
    """Return a list of plain-language problems. Empty list means the file is fine."""
    if not isinstance(videos, dict):
        return ["videos.json must be an object like {\"450\": {\"id\": \"VIDEOID\", \"start\": 0}}."]
    problems = []
    seen = {}
    for key, entry in videos.items():
        try:
            sid = int(key)
        except (TypeError, ValueError):
            problems.append(f"Song number {key!r} is not a number.")
            continue
        if sid not in song_ids:
            problems.append(f"Song {sid} does not exist in the songbook.")
        if not isinstance(entry, dict):
            problems.append(f"Song {sid}: the entry must be an object with an id, like {{\"id\": \"VIDEOID\"}}.")
            continue
        vid = entry.get("id", "")
        if not isinstance(vid, str) or not ID_RE.match(vid):
            problems.append(f"Song {sid}: video ID {vid!r} is not 11 letters, digits, dashes or underscores.")
        else:
            seen.setdefault(vid, []).append(sid)
        start = entry.get("start", 0)
        if not isinstance(start, int) or isinstance(start, bool) or start < 0:
            problems.append(f"Song {sid}: start time {start!r} must be a whole number of seconds, 0 or more.")
    for vid, sids in seen.items():
        if len(sids) > 1:
            problems.append(f"Video {vid} is used by more than one song: {sorted(sids)}.")
    log.debug("validated %d videos, %d problems", len(videos), len(problems))
    return problems


def _load():
    if config.VIDEOS_FILE.exists():
        return json.loads(config.VIDEOS_FILE.read_text(encoding="utf-8"))
    return {}


def add_video(song_id, url, start=0):
    """Add or replace the video for a song. Raises ValueError for a bad link and writes nothing."""
    vid = parse_youtube_id(url)
    if vid is None:
        raise ValueError(f"That is not a YouTube link I can read: {url!r}")
    if start < 0:
        raise ValueError("Start time must be 0 or more seconds.")
    data = _load()
    data[str(song_id)] = {"id": vid, "start": int(start)}
    ordered = {k: data[k] for k in sorted(data, key=int)}
    config.VIDEOS_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.VIDEOS_FILE.write_text(json.dumps(ordered, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log.debug("added video %s for song %s start=%s", vid, song_id, start)


def _song_ids():
    return {int(p.stem) for p in config.SONGS_DIR.glob("*.json")}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add")
    add.add_argument("song_id", type=int)
    add.add_argument("url")
    add.add_argument("--start", type=int, default=0)
    sub.add_parser("validate")
    args = ap.parse_args(argv)

    handlers = [logging.FileHandler(config.DATA_DIR / "videos_tool.log", mode="a", encoding="utf-8")]
    if args.debug:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.DEBUG, handlers=handlers, format="%(levelname)s %(name)s %(message)s", force=True
    )

    if args.cmd == "add":
        if args.song_id not in _song_ids():
            print(f"Song {args.song_id} does not exist.")
            return 1
        try:
            add_video(args.song_id, args.url, args.start)
        except ValueError as err:
            print(err)
            return 1
        print(f"Saved video for song {args.song_id}.")
        return 0

    problems = validate_videos(_load(), _song_ids())
    for p in problems:
        print(p)
    print("videos.json is fine." if not problems else f"{len(problems)} problem(s) found.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
