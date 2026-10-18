"""Read every video on a YouTube channel and match them to songs that have no video yet.

Only reads public pages. Never edits data/videos.json by itself; see add_from_channel() and the CLI.

Usage: python tools\\site\\channel_videos.py CHANNEL_ID [--add] [--debug]
Without --add it only prints what it would add. Debug log: data/channel_videos.log
"""
import argparse
import json
import logging
import re
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import songs as songs_data  # noqa: E402
import video_search as vs  # noqa: E402
import videos_tool  # noqa: E402

log = logging.getLogger("site.channel_videos")

ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
DURATION_RE = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")
VIEWS_RE = re.compile(r"^[\d.,]+\s*[KMB]?(\s*views?)?$", re.I)
SKIP_TITLE_RE = re.compile(
    r"instrumental|karaoke|dance|orchestra|ranked by|\?"
    r"|piano|guitar|accordion|violin|clarinet|saxophone|flute|kaval|tutorial|lesson|remix|ringtone",
    re.I,
)
_CTX = {"key": None, "version": "2.20240101.00.00"}


def parse_compact_views(text):
    """'26K' -> 26000, '1.2M views' -> 1200000, '850' -> 850, anything unreadable -> 0."""
    if not text:
        return 0
    m = re.match(r"\s*([\d][\d.,]*)\s*([KMB])?", text, re.I)
    if not m:
        return 0
    number = float(m.group(1).replace(",", ""))
    mult = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get((m.group(2) or "").upper(), 1)
    return int(round(number * mult))


def _walk(node, visit):
    if isinstance(node, dict):
        visit(node)
        for v in node.values():
            _walk(v, visit)
    elif isinstance(node, list):
        for v in node:
            _walk(v, visit)


def _durations(node, found):
    if isinstance(node, str):
        if DURATION_RE.match(node.strip()):
            found.append(node.strip())
    elif isinstance(node, dict):
        for v in node.values():
            _durations(v, found)
    elif isinstance(node, list):
        for v in node:
            _durations(v, found)


def extract_lockups(data):
    """Videos from YouTube's newer 'lockupViewModel' layout. Non-video items are skipped."""
    found = []

    def visit(node):
        if "lockupViewModel" in node:
            found.append(node["lockupViewModel"])

    _walk(data, visit)
    videos, seen = [], set()
    for lv in found:
        vid = lv.get("contentId", "")
        meta = lv.get("metadata", {}).get("lockupMetadataViewModel", {})
        title = meta.get("title", {}).get("content")
        if not ID_RE.match(vid) or not title or vid in seen:
            continue
        seen.add(vid)
        rows = meta.get("metadata", {}).get("contentMetadataViewModel", {}).get("metadataRows", [])
        parts = [p.get("text", {}).get("content", "") for r in rows for p in r.get("metadataParts", [])]
        views_text = next((p for p in parts if VIEWS_RE.match(p.strip())), None)
        durations = []
        _durations(lv.get("contentImage", {}), durations)
        videos.append(
            {
                "id": vid,
                "title": title,
                "views": parse_compact_views(views_text),
                "seconds": vs.parse_duration(durations[0]) if durations else None,
            }
        )
    return videos


def find_continuation(data):
    """The token for the next page of videos, or None. A token inside continuationItemRenderer wins."""
    preferred, any_token = [], []

    def visit(node):
        cmd = node.get("continuationCommand")
        if isinstance(cmd, dict) and isinstance(cmd.get("token"), str):
            any_token.append(cmd["token"])
        item = node.get("continuationItemRenderer")
        if isinstance(item, dict):
            inner = []
            _walk(item, lambda n: inner.append(n["continuationCommand"]["token"])
                  if isinstance(n.get("continuationCommand"), dict) and "token" in n["continuationCommand"] else None)
            preferred.extend(inner)

    _walk(data, visit)
    return (preferred or any_token or [None])[0]


def playlist_url(list_id):
    return f"https://www.youtube.com/playlist?list={list_id}"


_CHANNEL_PATH_RE = re.compile(r"^/(@[^/]+|channel/[^/]+|c/[^/]+|user/[^/]+)")


def resolve_source(ref):
    """Turn a handle (@Name), a channel ID, a playlist ID, or any YouTube link into ('channel' | 'playlist', url).
    Raises ValueError with a plain message when the text is none of those."""
    ref = (ref or "").strip()
    m = re.search(r"[?&]list=([A-Za-z0-9_-]+)", ref)
    if m:
        return "playlist", playlist_url(m.group(1))
    if re.fullmatch(r"PL[A-Za-z0-9_-]{10,}", ref):
        return "playlist", playlist_url(ref)
    if ref.startswith("@") and "/" not in ref:
        return "channel", f"https://www.youtube.com/{ref}/videos"
    if re.fullmatch(r"UC[A-Za-z0-9_-]{22}", ref):
        return "channel", f"https://www.youtube.com/channel/{ref}/videos"
    parsed = urlparse(ref)
    if parsed.hostname and parsed.hostname.endswith("youtube.com"):
        path = _CHANNEL_PATH_RE.match(parsed.path)
        if path:
            return "channel", f"https://www.youtube.com{path.group(0)}/videos"
    raise ValueError(f"I cannot tell what this is: {ref!r}. Give a channel link, an @handle, or a playlist link.")


def fetch_source_videos(ref, get_first=None, post_next=None, max_pages=80):
    """All videos of a channel or playlist, given a handle, ID or link."""
    kind, url = resolve_source(ref)
    get_first = get_first or _http_get_page
    return _fetch_all(lambda: get_first(url), post_next, max_pages, f"{kind} {url}")


def _http_get_first(channel_id):
    return _http_get_page(f"https://www.youtube.com/channel/{channel_id}/videos")


def _http_get_page(url):
    page = urlopen(Request(url, headers=vs.HEADERS), timeout=30).read().decode("utf-8", errors="replace")
    key = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', page)
    ver = re.search(r'"INNERTUBE_CONTEXT_CLIENT_VERSION":"([^"]+)"', page)
    _CTX["key"] = key.group(1) if key else None
    if ver:
        _CTX["version"] = ver.group(1)
    start = page.find("ytInitialData = ")
    data, _ = json.JSONDecoder().raw_decode(page[page.find("{", start):])
    return data


def _http_post_next(token):
    url = f"https://www.youtube.com/youtubei/v1/browse?key={_CTX['key']}"
    body = json.dumps(
        {"context": {"client": {"clientName": "WEB", "clientVersion": _CTX["version"], "hl": "en"}}, "continuation": token}
    ).encode("utf-8")
    headers = dict(vs.HEADERS, **{"Content-Type": "application/json"})
    return json.loads(urlopen(Request(url, data=body, headers=headers), timeout=30).read().decode("utf-8"))


def fetch_channel_videos(channel_id, get_first=None, post_next=None, max_pages=80):
    """All videos on the channel, newest first, without repeats."""
    get_first = get_first or _http_get_first
    return _fetch_all(lambda: get_first(channel_id), post_next, max_pages, f"channel {channel_id}")


def fetch_playlist_videos(list_id, get_first=None, post_next=None, max_pages=80):
    """All videos in a playlist, in playlist order, without repeats. `get_first` receives the playlist URL."""
    get_first = get_first or _http_get_page
    return _fetch_all(lambda: get_first(playlist_url(list_id)), post_next, max_pages, f"playlist {list_id}")


def _fetch_all(first_page, post_next, max_pages, label):
    post_next = post_next or _http_post_next
    data = first_page()
    videos, seen = [], set()

    def take(page):
        for v in extract_lockups(page):
            if v["id"] not in seen:
                seen.add(v["id"])
                videos.append(v)

    take(data)
    token = find_continuation(data)
    pages = 0
    while token and pages < max_pages:
        page = post_next(token)
        pages += 1
        take(page)
        token = find_continuation(page)
    log.debug("%s: %d videos in %d continuation pages", label, len(videos), pages)
    return videos


_NOTE_RE = re.compile(r"\([^)]*\)")
_SUFFIX_RE = re.compile(r"macedonian\s+(traditional\s+)?(wedding\s+|love\s+)?(song|music)", re.I)
_SPLIT_RE = re.compile(r"\s+[-|/]\s+")


def _word_set(text):
    return set(vs._normalize(text))


def title_score(song, video_title):
    """0 to 1: how closely some part of the video title (split at ' - ', '/', '|') has the same words as the
    song title, in Cyrillic or Latin. Notes in brackets and 'Macedonian Song' style labels are ignored.
    1 means identical word sets."""
    cleaned = _SUFFIX_RE.sub(" ", _NOTE_RE.sub(" ", video_title))
    targets = [w for w in (_word_set(song["title_cyr"]), _word_set(song["title_latin"])) if w]
    best = 0.0
    for piece in _SPLIT_RE.split(cleaned):
        words = _word_set(piece)
        if not words:
            continue
        for target in targets:
            best = max(best, len(words & target) / len(words | target))
    return best


def title_core_matches(song, video_title):
    """Strict match (score 0.8 or more). Short song titles cannot match longer, different songs."""
    return title_score(song, video_title) >= 0.8


def is_sung_song(title):
    """False for instrumentals, karaoke, dances and non-song videos."""
    return not SKIP_TITLE_RE.search(title)


def best_for_song(song, videos, used_ids=(), embeddable=None, max_seconds=vs.MAX_SECONDS):
    """Most viewed sung video on the channel whose title matches the song and that can be embedded."""
    for v in sorted(videos, key=lambda x: x["views"], reverse=True):
        if v["id"] in used_ids or not is_sung_song(v["title"]) or not title_core_matches(song, v["title"]):
            continue
        if v["seconds"] is not None and v["seconds"] > max_seconds:
            continue
        if embeddable is not None and not embeddable(v["id"]):
            log.debug("skip %s: not embeddable", v["id"])
            continue
        return v
    return None


def plan_additions(songs, videos, existing_video_ids, existing_song_ids, embeddable=None):
    """(song, video) pairs for songs with no video yet. A video is used for at most one song."""
    used = set(existing_video_ids)
    plan = []
    for song in songs:
        if song["id"] in existing_song_ids:
            continue
        best = best_for_song(song, videos, used_ids=used, embeddable=embeddable)
        if best:
            used.add(best["id"])
            plan.append((song, best))
    return plan


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("channel_id")
    ap.add_argument("--add", action="store_true", help="write the matches into data/videos.json")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args(argv)

    handlers = [logging.FileHandler(config.DATA_DIR / "channel_videos.log", mode="w", encoding="utf-8")]
    if args.debug:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.DEBUG, handlers=handlers, format="%(levelname)s %(name)s %(message)s", force=True
    )
    sys.stdout.reconfigure(encoding="utf-8")

    videos = fetch_channel_videos(args.channel_id)
    sung = [v for v in videos if is_sung_song(v["title"])]
    print(f"channel videos: {len(videos)}  sung songs (no instrumental, karaoke or dance): {len(sung)}")
    existing = songs_data.load_videos()
    used_ids = {v["id"] for v in existing.values()}
    plan = plan_additions(songs_data.load_songs(), videos, used_ids, set(existing), embeddable=vs.is_embeddable)
    for song, v in plan:
        print(f"{'ADD ' if args.add else 'WOULD ADD '} #{song['id']:<5} {song['title_cyr']}  <-  "
              f"{v['views']:,} views | {v['title']} | https://www.youtube.com/watch?v={v['id']}")
        if args.add:
            videos_tool.add_video(song["id"], f"https://www.youtube.com/watch?v={v['id']}")
    print(f"songs matched: {len(plan)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
